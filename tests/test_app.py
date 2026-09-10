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


def test_ocr_health_does_not_expose_key(monkeypatch):
 monkeypatch.setenv('OCR_PROVIDER','openai');monkeypatch.setenv('OPENAI_API_KEY','super-secret-value')
 r=client.get('/health/ocr');assert r.status_code==200
 assert r.json()=={'status':'ok','provider':'openai','openai_api_key_configured':True}
 assert 'super-secret-value' not in r.text


def test_process_reports_missing_openai_key(monkeypatch):
 monkeypatch.setenv('OCR_PROVIDER','openai');monkeypatch.delenv('OPENAI_API_KEY',raising=False)
 r=client.post('/api/process',files={'file':('bill.png',b'png','image/png')})
 assert r.status_code==503
 assert r.json()['detail']['code']=='ocr_api_key_missing'


def test_process_complete_flow_with_mocked_openai(monkeypatch):
 import sys
 class Response: output_text='ACME STORES\nInvoice No: INV-42\nDate: 01/02/2026\nGrand Total: 1,250.00'
 class Responses:
  def create(self,**kwargs):
   assert kwargs['model']=='test-model'
   assert kwargs['input'][0]['content'][1]['type']=='input_image'
   return Response()
 class OpenAI:
  def __init__(self,api_key): assert api_key=='test-key';self.responses=Responses()
 monkeypatch.setitem(sys.modules,'openai',type('FakeOpenAI',(),{'OpenAI':OpenAI}))
 monkeypatch.setenv('OCR_PROVIDER','openai');monkeypatch.setenv('OPENAI_API_KEY','test-key');monkeypatch.setenv('OPENAI_MODEL','test-model')
 r=client.post('/api/process',files={'file':('bill.png',b'png','image/png')})
 assert r.status_code==200
 body=r.json();assert body['status']=='success';assert body['invoice']['invoice']['number']['value']=='INV-42';assert body['invoice']['totals']['grand_total']['value']=='1250.00'


def test_process_reports_mocked_openai_auth_failure(monkeypatch):
 import sys
 class AuthenticationError(Exception): status_code=401
 class Responses:
  def create(self,**kwargs): raise AuthenticationError('invalid credentials')
 class OpenAI:
  def __init__(self,api_key): self.responses=Responses()
 monkeypatch.setitem(sys.modules,'openai',type('FakeOpenAI',(),{'OpenAI':OpenAI}))
 monkeypatch.setenv('OCR_PROVIDER','openai');monkeypatch.setenv('OPENAI_API_KEY','test-key')
 r=client.post('/api/process',files={'file':('bill.png',b'png','image/png')})
 assert r.status_code==502 and r.json()['detail']['code']=='ocr_authentication_failed'


def test_process_reports_model_response_and_unreadable_documents(monkeypatch):
 import sys
 class EmptyResponse: output_text=''
 class InvalidResponse: output_text=None
 class Responses:
  def __init__(self,response): self.response=response
  def create(self,**kwargs): return self.response
 class OpenAI:
  response=EmptyResponse()
  def __init__(self,api_key): self.responses=Responses(self.response)
 monkeypatch.setitem(sys.modules,'openai',type('FakeOpenAI',(),{'OpenAI':OpenAI}))
 monkeypatch.setenv('OCR_PROVIDER','openai');monkeypatch.setenv('OPENAI_API_KEY','test-key')
 unreadable=client.post('/api/process',files={'file':('bill.png',b'png','image/png')})
 assert unreadable.status_code==422 and unreadable.json()['detail']['code']=='document_unreadable'
 OpenAI.response=InvalidResponse()
 malformed=client.post('/api/process',files={'file':('bill.png',b'png','image/png')})
 assert malformed.status_code==502 and malformed.json()['detail']['code']=='ocr_model_response_failed'


def test_process_reports_structured_extraction_failure(monkeypatch):
 from app import main
 class Provider:
  provider_name='mock'
  def process_document(self,*args): return 'valid text'
 monkeypatch.setattr(main,'get_ocr_provider',lambda:Provider())
 monkeypatch.setattr(main,'parse_invoice',lambda text:(_ for _ in ()).throw(ValueError('bad structure')))
 r=client.post('/api/process',files={'file':('bill.png',b'png','image/png')})
 assert r.status_code==422 and r.json()['detail']['code']=='structured_extraction_failed'
