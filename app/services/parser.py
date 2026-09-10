from __future__ import annotations
import re
from app.models import FieldValue, InvoiceData, Item, Party

def fv(value='', confidence='not_detected'): return FieldValue(value=value, confidence=confidence if value else 'not_detected')
def parse_invoice(text: str) -> InvoiceData:
    """Conservative parser: empty values remain visible for user review rather than guessed."""
    def match(pattern):
        x=re.search(pattern, text, re.I); return x.group(1).strip() if x else ''
    gstins=re.findall(r'\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z0-9]\b', text.upper())
    inv=match(r'(?:invoice\s*(?:no|number|#)?|bill\s*(?:no|#)?)\s*[:.-]?\s*([A-Z0-9/-]+)')
    date=match(r'(?:invoice\s*)?date\s*[:.-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})')
    total=match(r'(?:grand\s*total|net\s*(?:amount|total))\s*[:₹]?\s*([\d,]+(?:\.\d{2})?)')
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    supplier=lines[0] if lines else ''
    return InvoiceData(invoice={'number':fv(inv,'medium'),'date':fv(date,'medium'),'currency':fv('INR','high')}, supplier=Party(name=fv(supplier,'low'),gstin=fv(gstins[0] if gstins else '', 'medium')), customer=Party(gstin=fv(gstins[1] if len(gstins)>1 else '', 'medium')), totals={'grand_total':fv(total.replace(',',''),'medium')},layout={'type':'gst_invoice','source_text_available':bool(text)})
