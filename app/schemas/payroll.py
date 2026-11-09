from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel
from app.models.payroll import PayrollStatus


class SalaryStructureCreate(BaseModel):
    staff_id: int
    basic_salary: Decimal
    allowances: Decimal = Decimal("0")
    nssf_rate_percent: Decimal = Decimal("5")


class SalaryStructureOut(BaseModel):
    id: int
    staff_id: int
    basic_salary: Decimal
    allowances: Decimal
    nssf_rate_percent: Decimal

    class Config:
        from_attributes = True


class GeneratePayrollRequest(BaseModel):
    month: int
    year: int


class PayrollRecordOut(BaseModel):
    id: int
    staff_id: int
    month: int
    year: int
    basic_salary: Decimal
    allowances: Decimal
    nssf_deduction: Decimal
    net_pay: Decimal
    status: PayrollStatus

    class Config:
        from_attributes = True


class MarkPaidRequest(BaseModel):
    pass
