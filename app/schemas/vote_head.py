from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class VoteHeadCreate(BaseModel):
    name: str
    is_optional: bool = False


class VoteHeadOut(BaseModel):
    id: int
    name: str
    is_optional: bool

    class Config:
        from_attributes = True


class FeeStructureItemCreate(BaseModel):
    vote_head_id: int
    school_class_id: int
    term_id: int
    day_amount: Decimal
    boarder_amount: Decimal


class FeeStructureItemOut(BaseModel):
    id: int
    vote_head_id: int
    school_class_id: int
    term_id: int
    day_amount: Decimal
    boarder_amount: Decimal

    class Config:
        from_attributes = True


class InvoiceLineItemOut(BaseModel):
    id: int
    invoice_id: int
    vote_head_id: int
    vote_head_name: Optional[str] = None
    amount_due: Decimal

    class Config:
        from_attributes = True
