from __future__ import annotations
import os
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from app.models import InvoiceData
from app.services.demo import demo_invoice
from app.services.exporters import csv_export, excel_export
from app.services.ocr import get_ocr_provider
from app.services.parser import parse_invoice
from app.services.validation import validate
ROOT=Path(__file__).parent
app=FastAPI(title='BillConvert',version='0.1.0')
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
MAX_UPLOAD=int(os.getenv('MAX_UPLOAD_MB','15'))*1024*1024
ALLOWED={'application/pdf','image/jpeg','image/png'}
@app.get('/')
def home(): return FileResponse(ROOT/'templates'/'index.html')
@app.get('/api/demo/{sample}')
def demo(sample:int=0):
 data=demo_invoice(sample);return {'invoice':data.model_dump(),'warnings':validate(data),'preview':f'Demo invoice {sample%2+1}'}
@app.post('/api/process')
async def process(file:UploadFile=File(...)):
 if file.content_type not in ALLOWED: raise HTTPException(415,'Please upload a PDF, JPG, JPEG, or PNG bill.')
 content=await file.read()
 if not content: raise HTTPException(422,'The uploaded file is empty.')
 if len(content)>MAX_UPLOAD: raise HTTPException(413,f'File exceeds the {MAX_UPLOAD//1024//1024} MB upload limit.')
 if file.content_type=='application/pdf' and not content.startswith(b'%PDF'): raise HTTPException(422,'This PDF appears corrupted. Please upload the original file.')
 text=get_ocr_provider().process_document(content,file.content_type)
 data=parse_invoice(text)
 return {'invoice':data.model_dump(),'warnings':validate(data),'preview':f'{file.filename} • {len(content)/1024:.1f} KB','ocr_notice':None if text else 'OCR could not reliably read this document. Review and complete the highlighted fields.'}
def parse_payload(data:dict)->InvoiceData: return InvoiceData.model_validate(data)
@app.post('/api/export/csv')
def export_csv(data:dict):
 result=csv_export(parse_payload(data));return Response(result,media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="billconvert-invoice.csv"'})
@app.post('/api/export/excel')
def export_excel(data:dict):
 result=excel_export(parse_payload(data));return Response(result,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename="billconvert-editable-invoice.xlsx"'})
@app.get('/health')
def health():return {'status':'ok'}
