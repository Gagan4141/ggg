# BillConvert

BillConvert is a privacy-minded MVP for Indian distributors, wholesalers, and retailers: **bill photo/PDF → reviewed data → generic CSV or editable Excel invoice reconstruction**. It does not place a full-page bill screenshot in Excel; its renderer builds header, parties, line-item cells, totals, borders, print settings, and editable values.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # optional; set environment values in your shell
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`, then select **Try GST distributor demo** or **Try retail demo**. The demos work without any API key.

## Configuration and OCR

- `MAX_UPLOAD_MB` controls the server-side file limit (default `15`).
- `OCR_PROVIDER=auto` uses local Tesseract if it is installed. Install the operating-system `tesseract` binary to enable it; otherwise BillConvert deliberately returns editable, low-confidence fields rather than inventing values.
- `OCR_PROVIDER=none` disables OCR. `app/services/ocr.py` defines the provider boundary for Google Vision, Textract, or Azure implementations.

Uploaded content is processed in memory and is neither persisted nor publicly served. Production deployments should add authentication, TLS, rate limiting, malware scanning, and a short-lived private object store only if asynchronous processing becomes necessary.

## Project layout

- `app/main.py`: FastAPI endpoints and upload safeguards.
- `app/services/ocr.py`: swappable OCR interface.
- `app/services/parser.py`: conservative normalized-invoice extraction.
- `app/services/validation.py`: non-blocking GST and arithmetic warnings.
- `app/services/exporters.py`: RFC-compatible UTF-8 CSV and cell-based XLSX renderer.
- `app/services/demo.py`: two distinct Indian GST invoice demos.
- `app/static/`: responsive upload/review/export UI.

## Test

```bash
pytest -q
```

Tests exercise demo processing, CSV export, workbook generation/opening, invalid file types, and malformed PDF handling.

### OCR diagnostics and failure responses

`GET /health/ocr` reports the selected provider and whether an OpenAI key is configured. It never returns the key or attempts an API call. Server logs record provider selection, key presence only, safe OpenAI request error metadata, response validity, and extraction validation errors.

`POST /api/process` returns a structured error detail with a `code` and safe `message` when OCR cannot proceed. The codes are `ocr_api_key_missing`, `ocr_authentication_failed`, `ocr_request_failed`, `ocr_model_response_failed`, `structured_extraction_failed`, and `document_unreadable`. A successful response has `status: "success"`.

For OpenAI OCR, set `OCR_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `OPENAI_MODEL` (default: `gpt-4.1-mini`). The health endpoint verifies configuration only; an actual upload is still required to verify API access and model availability.
