"""Swappable OCR provider boundary; local OCR is deliberately optional."""
from __future__ import annotations
from abc import ABC, abstractmethod
from io import BytesIO
class OCRProvider(ABC):
    @abstractmethod
    def process_document(self, content: bytes, mime_type: str) -> str: ...
class NullOCRProvider(OCRProvider):
    def process_document(self, content: bytes, mime_type: str) -> str: return ''
class LocalTesseractProvider(OCRProvider):
    def process_document(self, content: bytes, mime_type: str) -> str:
        if mime_type == 'application/pdf': return ''
        try:
            import pytesseract
            from PIL import Image
            return pytesseract.image_to_string(Image.open(BytesIO(content)))
        except Exception: return ''
def get_ocr_provider() -> OCRProvider:
    import os
    return NullOCRProvider() if os.getenv('OCR_PROVIDER') == 'none' else LocalTesseractProvider()
