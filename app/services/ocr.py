"""OCR provider boundary with an OpenAI vision backend for Vercel."""
from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from io import BytesIO


class OCRProvider(ABC):
    @abstractmethod
    def process_document(self, content: bytes, mime_type: str) -> str: ...


class NullOCRProvider(OCRProvider):
    def process_document(self, content: bytes, mime_type: str) -> str:
        return ""


class LocalTesseractProvider(OCRProvider):
    def process_document(self, content: bytes, mime_type: str) -> str:
        if mime_type == "application/pdf":
            return ""
        try:
            import pytesseract
            from PIL import Image

            return pytesseract.image_to_string(Image.open(BytesIO(content)))
        except Exception:
            return ""


class OpenAIOCRProvider(OCRProvider):
    """Use an OpenAI vision model to transcribe bills and invoices."""

    def process_document(self, content: bytes, mime_type: str) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return ""

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
            prompt = (
                "Read this bill or invoice carefully and transcribe all useful visible text. "
                "Preserve invoice numbers, dates, GSTINs, supplier/customer names, line items, "
                "quantities, prices, taxes, discounts, and totals. Keep table rows readable. "
                "Do not invent or correct values; if text is unclear, reproduce what is visible "
                "or omit it. Return only the transcription, with no commentary."
            )

            if mime_type == "application/pdf":
                data = base64.b64encode(content).decode("ascii")
                response = client.responses.create(
                    model=model,
                    input=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": prompt},
                                {
                                    "type": "input_file",
                                    "filename": "bill.pdf",
                                    "file_data": data,
                                },
                            ],
                        }
                    ],
                )
            else:
                data = base64.b64encode(content).decode("ascii")
                data_url = f"data:{mime_type};base64,{data}"
                response = client.responses.create(
                    model=model,
                    input=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": prompt},
                                {
                                    "type": "input_image",
                                    "image_url": data_url,
                                    "detail": "high",
                                },
                            ],
                        }
                    ],
                )

            return (response.output_text or "").strip()
        except Exception:
            return ""


# Backward-compatible alias for deployments that still refer to the old name.
OCRSpaceProvider = OpenAIOCRProvider


def get_ocr_provider() -> OCRProvider:
    provider = os.getenv("OCR_PROVIDER", "auto").lower().strip()

    if provider == "none":
        return NullOCRProvider()
    if provider in {"openai", "chatgpt", "gpt"}:
        return OpenAIOCRProvider()
    if provider in {"ocrspace", "ocr.space"}:
        return OpenAIOCRProvider()
    if provider == "tesseract":
        return LocalTesseractProvider()

    # Vercel/cloud default: OpenAI when an API key is configured.
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIOCRProvider()
    return LocalTesseractProvider()
