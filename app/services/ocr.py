"""OCR provider boundary with a Vercel-compatible hosted OCR backend."""
from __future__ import annotations

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


class OCRSpaceProvider(OCRProvider):
    """Hosted OCR.Space backend; suitable for Vercel serverless functions."""

    endpoint = "https://api.ocr.space/parse/image"

    def process_document(self, content: bytes, mime_type: str) -> str:
        api_key = os.getenv("OCR_SPACE_API_KEY")
        if not api_key:
            return ""

        try:
            import requests

            filename = "document.pdf" if mime_type == "application/pdf" else "document.png"
            response = requests.post(
                self.endpoint,
                headers={"apikey": api_key},
                files={"file": (filename, content, mime_type)},
                data={
                    "language": "eng",
                    "isOverlayRequired": "false",
                    "isTable": "true",
                    "detectOrientation": "true",
                    "scale": "true",
                    "OCREngine": "2",
                },
                timeout=45,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("IsErroredOnProcessing"):
                return ""
            return "\n".join(
                item.get("ParsedText", "")
                for item in payload.get("ParsedResults", [])
                if item.get("ParsedText")
            ).strip()
        except Exception:
            return ""


def get_ocr_provider() -> OCRProvider:
    provider = os.getenv("OCR_PROVIDER", "auto").lower().strip()

    if provider == "none":
        return NullOCRProvider()
    if provider in {"ocrspace", "ocr.space"}:
        return OCRSpaceProvider()
    if provider == "tesseract":
        return LocalTesseractProvider()

    # Vercel/cloud default: hosted OCR when an API key is configured.
    if os.getenv("OCR_SPACE_API_KEY"):
        return OCRSpaceProvider()
    return LocalTesseractProvider()
