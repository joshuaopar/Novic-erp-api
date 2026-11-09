import enum
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Enum, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class InvoiceStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"


class PaymentMethod(str, enum.Enum):
    MTN_MOMO = "mtn_momo"
    AIRTEL_MOMO = "airtel_momo"
    CASH = "cash"
    BANK = "bank"


class FeeStructure(Base):
    """Defines how much a class should pay per term, split by day/boarder."""
    __tablename__ = "fee_structures"
    __table_args__ = (
        UniqueConstraint("school_class_id", "term_id", name="uq_class_term_fee"),
    )

    id = Column(Integer, primary_key=True, index=True)
    school_class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    term_id = Column(Integer, ForeignKey("terms.id"), nullable=False)
    day_amount = Column(Numeric(12, 2), nullable=False)
    boarder_amount = Column(Numeric(12, 2), nullable=False)

    school_class = relationship("SchoolClass")
    term = relationship("Term")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    term_id = Column(Integer, ForeignKey("terms.id"), nullable=False)
    amount_due = Column(Numeric(12, 2), nullable=False)
    amount_paid = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.UNPAID)

    student = relationship("Student")
    term = relationship("Term")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    reference = Column(String, nullable=True)  # MoMo transaction ref, or cash receipt no.
    paid_at = Column(Date, nullable=True)

    invoice = relationship("Invoice", back_populates="payments")
