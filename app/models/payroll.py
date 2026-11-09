import enum
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class PayrollStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"


class SalaryStructure(Base):
    """Current salary setup per staff member. One active record per staff."""
    __tablename__ = "salary_structures"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), unique=True, nullable=False)
    basic_salary = Column(Numeric(12, 2), nullable=False)
    allowances = Column(Numeric(12, 2), nullable=False, default=0)  # transport, housing, etc. combined
    nssf_rate_percent = Column(Numeric(5, 2), nullable=False, default=5)  # employee NSSF contribution %

    staff = relationship("Staff")


class PayrollRecord(Base):
    __tablename__ = "payroll_records"
    __table_args__ = (
        UniqueConstraint("staff_id", "month", "year", name="uq_staff_month_year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)
    basic_salary = Column(Numeric(12, 2), nullable=False)
    allowances = Column(Numeric(12, 2), nullable=False, default=0)
    nssf_deduction = Column(Numeric(12, 2), nullable=False, default=0)
    net_pay = Column(Numeric(12, 2), nullable=False)
    status = Column(Enum(PayrollStatus), nullable=False, default=PayrollStatus.PENDING)

    staff = relationship("Staff")
