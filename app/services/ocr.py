"""OCR provider boundary and safe diagnostics for uploaded documents."""
from __future__ import annotations

import base64
import logging
import os
import re
from abc import ABC, abstractmethod
from io import BytesIO

logger = logging.getLogger(__name__)


class OCRProcessingError(Exception):
    """A classified OCR failure that is safe to return to the application layer."""

    code = "ocr_request_failed"
    public_message = "The OCR provider could not process this document. Please try again."

    def __init__(self, *, message: str | None = None, status_code: int = 502) -> None:
        super().__init__(message or self.public_message)
        self.status_code = status_code


class OCRConfigurationError(OCRProcessingError):
    code = "ocr_api_key_missing"
    public_message = "OCR is not configured: OPENAI_API_KEY is missing."

    def __init__(self) -> None:
        super().__init__(status_code=503)


class OCRAuthenticationError(OCRProcessingError):
    code = "ocr_authentication_failed"
    public_message = "The OCR provider rejected the server credentials. Contact the administrator."


class OCRModelResponseError(OCRProcessingError):
    code = "ocr_model_response_failed"
    public_message = "The OCR model returned no readable transcription. Please try another scan."


class OCRProviderDisabledError(OCRProcessingError):
    code = "ocr_provider_disabled"
    public_message = "OCR is disabled on this server."

    def __init__(self) -> None:
        super().__init__(status_code=503)


def _safe_error_message(error: Exception, api_key: str) -> str:
    """Keep useful provider diagnostics while ensuring credentials never reach logs."""
    message = str(error).replace(api_key, "[REDACTED]")
    return re.sub(r"\bsk-[A-Za-z0-9_-]+\b", "[REDACTED]", message)[:500]


class OCRProvider(ABC):
    provider_name = "unknown"

    @abstractmethod
    def process_document(self, content: bytes, mime_type: str) -> str: ...


class NullOCRProvider(OCRProvider):
    provider_name = "none"

    def process_document(self, content: bytes, mime_type: str) -> str:
        raise OCRProviderDisabledError()


class LocalTesseractProvider(OCRProvider):
    provider_name = "tesseract"

    def process_document(self, content: bytes, mime_type: str) -> str:
        if mime_type == "application/pdf":
            logger.info("OCR provider=tesseract cannot process PDF input")
            return ""
        try:
            import pytesseract
            from PIL import Image

            return pytesseract.image_to_string(Image.open(BytesIO(content))).strip()
        except Exception as error:
            logger.exception("OCR provider=tesseract failed type=%s", type(error).__name__)
            raise OCRProcessingError(message="Local OCR failed.") from error


class OpenAIOCRProvider(OCRProvider):
    """Use an OpenAI vision model to transcribe bills and invoices."""

    provider_name = "openai"

    def process_document(self, content: bytes, mime_type: str) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        logger.info("OCR provider=openai openai_api_key_configured=%s", bool(api_key))
        if not api_key:
            raise OCRConfigurationError()

        try:
            from openai import OpenAI
        except ImportError as error:
            logger.exception("OpenAI client initialization failed type=%s", type(error).__name__)
            raise OCRProcessingError(message="OpenAI client is not installed.") from error

        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        prompt = (
            "Read this bill or invoice carefully and transcribe all useful visible text. "
            "Preserve invoice numbers, dates, GSTINs, supplier/customer names, line items, "
            "quantities, prices, taxes, discounts, and totals. Keep table rows readable. "
            "Do not invent or correct values; if text is unclear, reproduce what is visible "
            "or omit it. Return only the transcription, with no commentary."
        )
        try:
            client = OpenAI(api_key=api_key)
            data = base64.b64encode(content).decode("ascii")
            attachment = (
                {"type": "input_file", "filename": "bill.pdf", "file_data": data}
                if mime_type == "application/pdf"
                else {"type": "input_image", "image_url": f"data:{mime_type};base64,{data}", "detail": "high"}
            )
            response = client.responses.create(
                model=model,
                input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, attachment]}],
            )
        except Exception as error:
            status_code = getattr(error, "status_code", None)
            error_name = type(error).__name__
            safe_message = _safe_error_message(error, api_key)
            logger.error(
                "OpenAI OCR request failed type=%s status=%s message=%s",
                error_name, status_code, safe_message,
            )
            if status_code == 401 or error_name == "AuthenticationError":
                raise OCRAuthenticationError(message=safe_message) from error
            raise OCRProcessingError(message=safe_message) from error

        text = getattr(response, "output_text", None)
        if not isinstance(text, str):
            logger.error("OpenAI OCR model response invalid: output_text type=%s", type(text).__name__)
            raise OCRModelResponseError(message="OpenAI response did not contain text.")
        text = text.strip()
        logger.info("OpenAI OCR structured transcription received=%s", bool(text))
        return text


# Backward-compatible alias for deployments that still refer to the old name.
OCRSpaceProvider = OpenAIOCRProvider


def configured_provider_name() -> str:
    return get_ocr_provider().provider_name


def get_ocr_provider() -> OCRProvider:
    provider = os.getenv("OCR_PROVIDER", "auto").lower().strip()
    if provider == "none":
        selected: OCRProvider = NullOCRProvider()
    elif provider in {"openai", "chatgpt", "gpt", "ocrspace", "ocr.space"}:
        selected = OpenAIOCRProvider()
    elif provider == "tesseract":
        selected = LocalTesseractProvider()
    elif os.getenv("OPENAI_API_KEY"):
        selected = OpenAIOCRProvider()
    else:
        selected = LocalTesseractProvider()
    logger.info("OCR provider selected=%s configured_provider=%s", selected.provider_name, provider)
    return selected
