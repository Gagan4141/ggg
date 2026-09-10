from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

Confidence = Literal['high', 'medium', 'low', 'not_detected']
class FieldValue(BaseModel):
    value: str | float | int | None = ''
    confidence: Confidence = 'not_detected'
class Item(BaseModel):
    serial_number: FieldValue = Field(default_factory=FieldValue)
    product_name: FieldValue = Field(default_factory=FieldValue)
    sku: FieldValue = Field(default_factory=FieldValue)
    hsn: FieldValue = Field(default_factory=FieldValue)
    quantity: FieldValue = Field(default_factory=FieldValue)
    unit: FieldValue = Field(default_factory=FieldValue)
    rate: FieldValue = Field(default_factory=FieldValue)
    discount: FieldValue = Field(default_factory=FieldValue)
    taxable_value: FieldValue = Field(default_factory=FieldValue)
    gst: FieldValue = Field(default_factory=FieldValue)
    cgst: FieldValue = Field(default_factory=FieldValue)
    sgst: FieldValue = Field(default_factory=FieldValue)
    igst: FieldValue = Field(default_factory=FieldValue)
    line_total: FieldValue = Field(default_factory=FieldValue)
class Party(BaseModel):
    name: FieldValue = Field(default_factory=FieldValue)
    address: FieldValue = Field(default_factory=FieldValue)
    gstin: FieldValue = Field(default_factory=FieldValue)
    pan: FieldValue = Field(default_factory=FieldValue)
    phone: FieldValue = Field(default_factory=FieldValue)
    email: FieldValue = Field(default_factory=FieldValue)
class InvoiceData(BaseModel):
    invoice: dict[str, FieldValue] = Field(default_factory=dict)
    supplier: Party = Field(default_factory=Party)
    customer: Party = Field(default_factory=Party)
    items: list[Item] = Field(default_factory=list)
    totals: dict[str, FieldValue] = Field(default_factory=dict)
    layout: dict[str, Any] = Field(default_factory=dict)
