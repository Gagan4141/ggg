from __future__ import annotations
import logging
import os
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from app.models import InvoiceData
from app.services.demo import demo_invoice
from app.services.exporters import csv_export, excel_export
from app.services.ocr import OCRProcessingError, configured_provider_name, get_ocr_provider
from app.services.parser import parse_invoice
from app.services.validation import validate

logger = logging.getLogger(__name__)
ROOT = Path(__file__).parent
app = FastAPI(title="BillConvert", version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
MAX_UPLOAD = int(os.getenv("MAX_UPLOAD_MB", "15")) * 1024 * 1024
ALLOWED = {"application/pdf", "image/jpeg", "image/png"}


def ocr_error(error: OCRProcessingError) -> HTTPException:
    logger.error("OCR processing failed code=%s", error.code)
    return HTTPException(error.status_code, {"code": error.code, "message": error.public_message})


@app.get("/")
def home(): return FileResponse(ROOT / "templates" / "index.html")


@app.get("/api/demo/{sample}")
def demo(sample: int = 0):
    data = demo_invoice(sample)
    return {"invoice": data.model_dump(), "warnings": validate(data), "preview": f"Demo invoice {sample % 2 + 1}"}


@app.get("/health/ocr")
def ocr_health():
    """Configuration-only diagnostic; deliberately does not contact OpenAI or expose secrets."""
    selected_provider = configured_provider_name()
    key_configured = bool(os.getenv("OPENAI_API_KEY"))
    logger.info("OCR health provider=%s openai_api_key_configured=%s", selected_provider, key_configured)
    return {
        "status": "ok" if selected_provider != "openai" or key_configured else "misconfigured",
        "provider": selected_provider,
        "openai_api_key_configured": key_configured,
    }


@app.post("/api/process")
async def process(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED:
        raise HTTPException(415, "Please upload a PDF, JPG, JPEG, or PNG bill.")
    content = await file.read()
    if not content:
        raise HTTPException(422, "The uploaded file is empty.")
    if len(content) > MAX_UPLOAD:
        raise HTTPException(413, f"File exceeds the {MAX_UPLOAD // 1024 // 1024} MB upload limit.")
    if file.content_type == "application/pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(422, "This PDF appears corrupted. Please upload the original file.")

    provider = get_ocr_provider()
    logger.info("Processing upload provider=%s mime_type=%s bytes=%s", provider.provider_name, file.content_type, len(content))
    try:
        text = provider.process_document(content, file.content_type)
    except OCRProcessingError as error:
        raise ocr_error(error) from error

    if not text:
        logger.info("OCR completed but document was unreadable provider=%s", provider.provider_name)
        raise HTTPException(422, {"code": "document_unreadable", "message": "OCR completed, but no readable text was found. Please upload a clearer scan or original PDF."})
    try:
        data = parse_invoice(text)
        data = InvoiceData.model_validate(data)
    except (ValidationError, ValueError, TypeError) as error:
        logger.exception("Structured extraction validation failed type=%s", type(error).__name__)
        raise HTTPException(422, {"code": "structured_extraction_failed", "message": "Text was read, but invoice data could not be structured. Please review the document manually."}) from error

    logger.info("OCR extraction successful provider=%s structured_response_valid=true", provider.provider_name)
    return {"status": "success", "invoice": data.model_dump(), "warnings": validate(data), "preview": f"{file.filename} • {len(content) / 1024:.1f} KB", "ocr_notice": None}


def parse_payload(data: dict) -> InvoiceData: return InvoiceData.model_validate(data)


@app.post("/api/export/csv")
def export_csv(data: dict):
    result = csv_export(parse_payload(data))
    return Response(result, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=\"billconvert-invoice.csv\""})


@app.post("/api/export/excel")
def export_excel(data: dict):
    result = excel_export(parse_payload(data))
    return Response(result, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=\"billconvert-editable-invoice.xlsx\""})


@app.get("/health")
def health(): return {"status": "ok"}
