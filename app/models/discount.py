import enum
from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, Enum, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DiscountType(str, enum.Enum):
    SIBLING = "sibling"
    STAFF_CHILD = "staff_child"
    SCHOLARSHIP = "scholarship"
    MANUAL_WAIVER = "manual_waiver"


class StudentDiscount(Base):
    """A standing discount/waiver applied to a student's invoices going forward.
    Percentage discounts apply to the invoice total; fixed_amount discounts subtract a flat sum.
    Only one of percentage / fixed_amount should be set."""
    __tablename__ = "student_discounts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    discount_type = Column(Enum(DiscountType), nullable=False)
    percentage = Column(Numeric(5, 2), nullable=True)  # e.g. 25.00 = 25%
    fixed_amount = Column(Numeric(12, 2), nullable=True)
    reason = Column(Text, nullable=True)
    approved_by_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student")
    approved_by = relationship("Staff")
