from app.models import InvoiceData
SAMPLE_TEXTS = [
'''SRI LAKSHMI DISTRIBUTORS\nGSTIN: 29ABCDE1234F1Z5\nInvoice No: SLD/2026/1042\nInvoice Date: 10/09/2026\nBill To: Green Basket Retail\nGSTIN: 29AACCG6789K1Z2\nGrand Total: 7,552.00''',
'''NARMADA MEDICAL SUPPLIES\nGSTIN: 27AABCN9932M1ZQ\nBill No: NMS-8841\nDate: 08/09/2026\nTax Invoice\nGrand Total: 3,186.00'''
]

def demo_invoice(index: int=0) -> InvoiceData:
 from app.services.parser import parse_invoice
 from app.models import Item, FieldValue
 d=parse_invoice(SAMPLE_TEXTS[index % 2])
 d.customer.name=FieldValue(value='Green Basket Retail' if index%2==0 else 'Aarogya Pharmacy',confidence='high')
 d.items=[Item(serial_number=FieldValue(value=1,confidence='high'),product_name=FieldValue(value='Premium Basmati Rice, 5 kg' if index%2==0 else 'Paracetamol 500mg',confidence='high'),hsn=FieldValue(value='1006' if index%2==0 else '3004',confidence='high'),quantity=FieldValue(value=2,confidence='high'),unit=FieldValue(value='PCS',confidence='high'),rate=FieldValue(value=3200 if index%2==0 else 1350,confidence='high'),taxable_value=FieldValue(value=6400 if index%2==0 else 2700,confidence='high'),gst=FieldValue(value=18,confidence='high'),cgst=FieldValue(value=576 if index%2==0 else 243,confidence='high'),sgst=FieldValue(value=576 if index%2==0 else 243,confidence='high'),line_total=FieldValue(value=7552 if index%2==0 else 3186,confidence='high'))]
 d.layout.update({'variant':'split_header' if index%2==0 else 'receipt','title':'TAX INVOICE'})
 return d
