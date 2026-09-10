from __future__ import annotations
import re
from app.models import InvoiceData
def num(x):
 try:return float(x or 0)
 except (TypeError,ValueError):return 0
def validate(data: InvoiceData) -> list[str]:
 warnings=[]
 for label, party in [('Supplier',data.supplier),('Customer',data.customer)]:
  value=str(party.gstin.value or '')
  if value and not re.fullmatch(r'\d{2}[A-Z]{5}\d{4}[A-Z]\dZ[A-Z0-9]',value): warnings.append(f'{label} GSTIN format appears invalid.')
 for i,item in enumerate(data.items,1):
  q,r,total=map(lambda x:num(x.value),(item.quantity,item.rate,item.line_total))
  if q and r and total and abs(q*r-total)>.05: warnings.append(f'Item {i}: quantity × rate does not match line total.')
 return warnings
