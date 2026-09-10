from io import BytesIO
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from app.main import app
client=TestClient(app)
def test_demo_and_exports():
 r=client.get('/api/demo/0');assert r.status_code==200; data=r.json()['invoice'];assert data['items']
 csv=client.post('/api/export/csv',json=data);assert csv.status_code==200 and b'Invoice Number' in csv.content
 xlsx=client.post('/api/export/excel',json=data);assert xlsx.status_code==200
 wb=load_workbook(BytesIO(xlsx.content));assert wb.active['A1'].value=='SRI LAKSHMI DISTRIBUTORS';assert wb.active['B8'].value

def test_rejects_invalid_upload():
 r=client.post('/api/process',files={'file':('bad.txt',b'x','text/plain')});assert r.status_code==415

def test_rejects_bad_pdf():
 r=client.post('/api/process',files={'file':('bad.pdf',b'not a pdf','application/pdf')});assert r.status_code==422
