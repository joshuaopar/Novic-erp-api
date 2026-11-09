from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.people import UserRole, Staff
from app.models.payroll import SalaryStructure, PayrollRecord, PayrollStatus
from app.schemas.payroll import (
    SalaryStructureCreate, SalaryStructureOut,
    GeneratePayrollRequest, PayrollRecordOut,
)

router = APIRouter(prefix="/payroll", tags=["payroll"])

admin_or_bursar = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.BURSAR)


# ---- Salary Structures ----

@router.post("/salary-structures", response_model=SalaryStructureOut, dependencies=[Depends(admin_or_bursar)])
def create_salary_structure(payload: SalaryStructureCreate, db: Session = Depends(get_db)):
    staff = db.query(Staff).get(payload.staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    existing = db.query(SalaryStructure).filter(SalaryStructure.staff_id == payload.staff_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Salary structure already exists for this staff member")

    structure = SalaryStructure(**payload.dict())
    db.add(structure)
    db.commit()
    db.refresh(structure)
    return structure


@router.get("/salary-structures", response_model=List[SalaryStructureOut])
def list_salary_structures(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(SalaryStructure).all()


# ---- Payroll Generation ----

@router.post("/generate", response_model=List[PayrollRecordOut], dependencies=[Depends(admin_or_bursar)])
def generate_payroll(payload: GeneratePayrollRequest, db: Session = Depends(get_db)):
    structures = db.query(SalaryStructure).all()
    created = []

    for structure in structures:
        existing = (
            db.query(PayrollRecord)
            .filter(
                PayrollRecord.staff_id == structure.staff_id,
                PayrollRecord.month == payload.month,
                PayrollRecord.year == payload.year,
            )
            .first()
        )
        if existing:
            continue  # already generated for this staff/month/year

        nssf_deduction = (structure.basic_salary * structure.nssf_rate_percent) / Decimal("100")
        net_pay = structure.basic_salary + structure.allowances - nssf_deduction

        record = PayrollRecord(
            staff_id=structure.staff_id,
            month=payload.month,
            year=payload.year,
            basic_salary=structure.basic_salary,
            allowances=structure.allowances,
            nssf_deduction=nssf_deduction,
            net_pay=net_pay,
        )
        db.add(record)
        created.append(record)

    db.commit()
    for r in created:
        db.refresh(r)
    return created


@router.get("", response_model=List[PayrollRecordOut])
def list_payroll(
    staff_id: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(PayrollRecord)
    if staff_id is not None:
        query = query.filter(PayrollRecord.staff_id == staff_id)
    if month is not None:
        query = query.filter(PayrollRecord.month == month)
    if year is not None:
        query = query.filter(PayrollRecord.year == year)
    return query.all()


@router.post("/{payroll_id}/mark-paid", response_model=PayrollRecordOut, dependencies=[Depends(admin_or_bursar)])
def mark_paid(payroll_id: int, db: Session = Depends(get_db)):
    record = db.query(PayrollRecord).get(payroll_id)
    if not record:
        raise HTTPException(status_code=404, detail="Payroll record not found")
    record.status = PayrollStatus.PAID
    db.commit()
    db.refresh(record)
    return record
