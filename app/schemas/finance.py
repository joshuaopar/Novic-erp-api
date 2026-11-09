from decimal import Decimal
from typing import Optional, List
from datetime import date
from pydantic import BaseModel
from app.models.finance import InvoiceStatus, PaymentMethod


class FeeStructureCreate(BaseModel):
    school_class_id: int
    term_id: int
    day_amount: Decimal
    boarder_amount: Decimal


class FeeStructureOut(BaseModel):
    id: int
    school_class_id: int
    term_id: int
    day_amount: Decimal
    boarder_amount: Decimal

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    id: int
    student_id: int
    term_id: int
    amount_due: Decimal
    amount_paid: Decimal
    status: InvoiceStatus

    class Config:
        from_attributes = True


class GenerateInvoicesRequest(BaseModel):
    term_id: int
    school_class_id: Optional[int] = None  # if omitted, generate for all classes


class PaymentCreate(BaseModel):
    invoice_id: int
    amount: Decimal
    method: PaymentMethod
    reference: Optional[str] = None
    paid_at: Optional[date] = None


class PaymentOut(BaseModel):
    id: int
    invoice_id: int
    amount: Decimal
    method: PaymentMethod
    reference: Optional[str]
    paid_at: Optional[date]

    class Config:
        from_attributes = True
