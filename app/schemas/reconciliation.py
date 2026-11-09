from decimal import Decimal
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel
from app.models.reconciliation import SettlementStatus


class SimulateDepositRequest(BaseModel):
    """Mimics what a real bank/MoMo webhook payload would send us."""
    utr_reference: str
    transaction_date: date
    deposit_amount: Decimal
    input_pay_code: str  # raw, possibly messy e.g. "sch - 2026 / 001"


class BankTransactionOut(BaseModel):
    id: int
    utr_reference: str
    transaction_date: date
    deposit_amount: Decimal
    input_pay_code_raw: str
    input_pay_code_sanitized: str
    matched_student_id: Optional[int]
    settlement_status: SettlementStatus
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class ManualMatchRequest(BaseModel):
    student_id: int


class StudentCreditOut(BaseModel):
    student_id: int
    balance: Decimal

    class Config:
        from_attributes = True


class ReversalRequest(BaseModel):
    penalty_fee: Optional[Decimal] = None
    reason: Optional[str] = None


class EndOfDayReportOut(BaseModel):
    report_date: date
    total_transactions_reconciled: int
    total_amount_reconciled: float
    official_bank_balance: float
    discrepancy: float
    has_discrepancy: bool
    unidentified_deposits_count: int
