from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.people import UserRole, Student, BoardingStatus
from app.models.academic import Stream, SchoolClass
from app.models.finance import FeeStructure, Invoice, Payment, InvoiceStatus
from app.models.vote_head import FeeStructureItem, InvoiceLineItem
from app.models.discount import StudentDiscount
from app.models.vote_head import VoteHead
from app.models.academic import Term
from app.schemas.finance import (
    FeeStructureCreate, FeeStructureOut,
    InvoiceOut, GenerateInvoicesRequest,
    PaymentCreate, PaymentOut,
)

router = APIRouter(prefix="/finance", tags=["finance"])

bursar_or_admin = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.BURSAR)


# ---- Fee Structures ----

@router.post("/fee-structures", response_model=FeeStructureOut, dependencies=[Depends(bursar_or_admin)])
def create_fee_structure(payload: FeeStructureCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(FeeStructure)
        .filter(
            FeeStructure.school_class_id == payload.school_class_id,
            FeeStructure.term_id == payload.term_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Fee structure already exists for this class/term")

    fee = FeeStructure(**payload.dict())
    db.add(fee)
    db.commit()
    db.refresh(fee)
    return fee


@router.get("/fee-structures", response_model=List[FeeStructureOut])
def list_fee_structures(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(FeeStructure).all()


# ---- Invoices ----

@router.post("/invoices/generate", response_model=List[InvoiceOut], dependencies=[Depends(bursar_or_admin)])
def generate_invoices(payload: GenerateInvoicesRequest, db: Session = Depends(get_db)):
    query = db.query(Student).filter(Student.is_active == True)  # noqa: E712
    if payload.school_class_id:
        query = query.join(Stream).filter(Stream.school_class_id == payload.school_class_id)

    students = query.all()
    created = []

    for student in students:
        stream = db.query(Stream).get(student.stream_id)

        existing_invoice = (
            db.query(Invoice)
            .filter(Invoice.student_id == student.id, Invoice.term_id == payload.term_id)
            .first()
        )
        if existing_invoice:
            continue  # already invoiced

        # Itemized billing: pull every mandatory (non-optional) vote-head configured for this class/term
        fee_items = (
            db.query(FeeStructureItem)
            .join(FeeStructureItem.vote_head)
            .filter(
                FeeStructureItem.school_class_id == stream.school_class_id,
                FeeStructureItem.term_id == payload.term_id,
            )
            .all()
        )
        mandatory_items = [fi for fi in fee_items if not fi.vote_head.is_optional]

        if not mandatory_items:
            continue  # no fee structure items configured for this class/term yet

        # Mid-term pro-ration: if the student enrolled after this term started, scale
        # the fee by the fraction of the term remaining. Requires term start/end dates
        # and student.enrollment_date to be set; otherwise bills in full (safe default).
        proration_factor = 1
        term = db.query(Term).get(payload.term_id)
        if term and term.start_date and term.end_date and student.enrollment_date:
            if student.enrollment_date > term.start_date:
                term_total_days = (term.end_date - term.start_date).days or 1
                remaining_days = (term.end_date - student.enrollment_date).days
                if remaining_days < 0:
                    remaining_days = 0
                proration_factor = min(remaining_days / term_total_days, 1)

        total_due = 0
        invoice = Invoice(student_id=student.id, term_id=payload.term_id, amount_due=0)
        db.add(invoice)
        db.flush()  # get invoice.id before creating line items

        for fi in mandatory_items:
            amount = fi.boarder_amount if student.boarding_status == BoardingStatus.BOARDER else fi.day_amount
            if proration_factor < 1:
                amount = round(amount * proration_factor, 2)
            db.add(InvoiceLineItem(invoice_id=invoice.id, vote_head_id=fi.vote_head_id, amount_due=amount))
            total_due += amount

        # Apply discounts to the current term's new charges ONLY, before arrears are added —
        # arrears are historical debt already invoiced (and already discounted correctly at
        # that time), so they must not be discounted a second time here.
        discounts = (
            db.query(StudentDiscount)
            .filter(StudentDiscount.student_id == student.id, StudentDiscount.is_active == True)  # noqa: E712
            .all()
        )
        for d in discounts:
            if d.percentage:
                total_due -= total_due * (d.percentage / 100)
            elif d.fixed_amount:
                total_due -= d.fixed_amount
        total_due = max(total_due, 0)

        # Arrears forwarding: pull any unpaid balance from the student's most recent
        # prior invoice and add it as its own "Previous Term Arrears" line item.
        # Added AFTER discounting, so past debt is carried forward at full value.
        prior_invoice = (
            db.query(Invoice)
            .filter(Invoice.student_id == student.id, Invoice.term_id != payload.term_id)
            .filter(Invoice.status != InvoiceStatus.PAID)
            .order_by(Invoice.term_id.desc())
            .first()
        )
        if prior_invoice:
            outstanding = prior_invoice.amount_due - prior_invoice.amount_paid
            if outstanding > 0:
                arrears_vote_head = db.query(VoteHead).filter(VoteHead.name == "Previous Term Arrears").first()
                if not arrears_vote_head:
                    arrears_vote_head = VoteHead(name="Previous Term Arrears", is_optional=False)
                    db.add(arrears_vote_head)
                    db.flush()
                db.add(InvoiceLineItem(invoice_id=invoice.id, vote_head_id=arrears_vote_head.id, amount_due=outstanding))
                total_due += outstanding

        invoice.amount_due = total_due
        created.append(invoice)

    db.commit()
    for inv in created:
        db.refresh(inv)
    return created


@router.get("/invoices", response_model=List[InvoiceOut])
def list_invoices(
    student_id: Optional[int] = Query(None),
    term_id: Optional[int] = Query(None),
    status: Optional[InvoiceStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Invoice)
    if student_id is not None:
        query = query.filter(Invoice.student_id == student_id)
    if term_id is not None:
        query = query.filter(Invoice.term_id == term_id)
    if status is not None:
        query = query.filter(Invoice.status == status)
    return query.all()


# ---- Payments ----

@router.post("/payments", response_model=PaymentOut, dependencies=[Depends(bursar_or_admin)])
def record_payment(payload: PaymentCreate, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).get(payload.invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    payment = Payment(**payload.dict())
    db.add(payment)

    invoice.amount_paid = invoice.amount_paid + payload.amount
    if invoice.amount_paid >= invoice.amount_due:
        invoice.status = InvoiceStatus.PAID
    elif invoice.amount_paid > 0:
        invoice.status = InvoiceStatus.PARTIALLY_PAID

    db.commit()
    db.refresh(payment)
    return payment
