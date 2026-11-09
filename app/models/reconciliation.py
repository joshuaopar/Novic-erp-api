import enum
from sqlalchemy import Column, Integer, String, Numeric, Date, Enum, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class SettlementStatus(str, enum.Enum):
    RECONCILED = "reconciled"
    UNIDENTIFIED = "unidentified"
    REVERSED = "reversed"


class BankTransaction(Base):
    """Immutable log of every incoming deposit. Never edited or deleted after creation —
    only its settlement_status changes, and reversals happen via a separate reversal record."""
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    utr_reference = Column(String, unique=True, nullable=False, index=True)
    transaction_date = Column(Date, nullable=False)
    deposit_amount = Column(Numeric(12, 2), nullable=False)
    input_pay_code_raw = Column(String, nullable=False)
    input_pay_code_sanitized = Column(String, nullable=False, index=True)
    matched_student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    settlement_status = Column(Enum(SettlementStatus), nullable=False, default=SettlementStatus.UNIDENTIFIED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    matched_student = relationship("Student")


class StudentCredit(Base):
    """Running credit balance per student, created from overpayments. Deducted from future invoices."""
    __tablename__ = "student_credits"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=False)
    balance = Column(Numeric(12, 2), nullable=False, default=0)

    student = relationship("Student")
