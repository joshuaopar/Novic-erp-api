import re
from typing import List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.sms import send_sms
from app.models.people import UserRole, Student
from app.models.finance import Invoice, InvoiceStatus, Payment, PaymentMethod
from app.models.reconciliation import BankTransaction, StudentCredit, SettlementStatus
from app.models.communication import Notification, NotificationStatus
from app.schemas.reconciliation import (
    SimulateDepositRequest, BankTransactionOut, ManualMatchRequest, StudentCreditOut,
    ReversalRequest, EndOfDayReportOut,
)
from datetime import date as date_cls

router = APIRouter(prefix="/finance/reconciliation", tags=["finance-reconciliation"])

bursar_or_admin = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.BURSAR)
senior_bursar = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER)  # checker role for maker-checker


def sanitize_pay_code(raw: str) -> str:
    """Step 1: Sanitation. Strips whitespace and special characters, uppercases.
    e.g. 'sch - 2026 / 041' -> 'SCH2026041'"""
    return re.sub(r"[^A-Za-z0-9]", "", raw).upper()


def allocate_fifo(db: Session, student: Student, amount: Decimal) -> Decimal:
    """Step 3: Split Allocation (FIFO). Applies the deposit to the student's oldest
    unpaid/partially-paid invoices first (earlier term_id = older = arrears cleared first).
    Returns any leftover amount (overpayment) not consumed by outstanding invoices."""
    outstanding_invoices = (
        db.query(Invoice)
        .filter(
            Invoice.student_id == student.id,
            Invoice.status != InvoiceStatus.PAID,
        )
        .order_by(Invoice.term_id.asc())
        .all()
    )

    remaining = amount
    for invoice in outstanding_invoices:
        if remaining <= 0:
            break
        owed = invoice.amount_due - invoice.amount_paid
        if owed <= 0:
            continue
        applied = min(remaining, owed)

        payment = Payment(
            invoice_id=invoice.id,
            amount=applied,
            method=PaymentMethod.MTN_MOMO,  # reconciliation source; refine later if we track bank vs momo separately
            reference=None,  # linked via the BankTransaction record instead
        )
        db.add(payment)

        invoice.amount_paid = invoice.amount_paid + applied
        if invoice.amount_paid >= invoice.amount_due:
            invoice.status = InvoiceStatus.PAID
        elif invoice.amount_paid > 0:
            invoice.status = InvoiceStatus.PARTIALLY_PAID

        remaining -= applied

    return remaining  # leftover = overpayment, if any


def apply_overpayment_credit(db: Session, student: Student, leftover: Decimal):
    if leftover <= 0:
        return
    credit = db.query(StudentCredit).filter(StudentCredit.student_id == student.id).first()
    if not credit:
        credit = StudentCredit(student_id=student.id, balance=0)
        db.add(credit)
    credit.balance = credit.balance + leftover


def send_receipt_sms(student: Student, amount: Decimal, remaining_balance: Decimal):
    """Step 4: SMS Trigger."""
    message = (
        f"Thank you, UGX {amount:,.0f} received for {student.full_name} ({student.pay_code}). "
        f"Your remaining balance is UGX {remaining_balance:,.0f}."
    )
    for guardian in student.guardians:
        send_sms(guardian.phone_number, message)


@router.post("/simulate-deposit", response_model=BankTransactionOut, dependencies=[Depends(bursar_or_admin)])
def simulate_deposit(payload: SimulateDepositRequest, db: Session = Depends(get_db)):
    """Simulates an incoming bank/MoMo webhook. Once deployed with real API access,
    this same logic runs automatically when a real deposit notification arrives."""

    existing = db.query(BankTransaction).filter(BankTransaction.utr_reference == payload.utr_reference).first()
    if existing:
        raise HTTPException(status_code=400, detail="This transaction reference has already been processed")

    # Step 1: Sanitation
    sanitized_code = sanitize_pay_code(payload.input_pay_code)

    # Step 2: Pay-Code Lookup (compare sanitized-to-sanitized, since stored codes
    # may contain dashes like SCH-2026-001 while incoming references vary in formatting)
    student = None
    for candidate in db.query(Student).filter(Student.pay_code.isnot(None)).all():
        if sanitize_pay_code(candidate.pay_code) == sanitized_code:
            student = candidate
            break

    transaction = BankTransaction(
        utr_reference=payload.utr_reference,
        transaction_date=payload.transaction_date,
        deposit_amount=payload.deposit_amount,
        input_pay_code_raw=payload.input_pay_code,
        input_pay_code_sanitized=sanitized_code,
        matched_student_id=student.id if student else None,
        settlement_status=SettlementStatus.UNIDENTIFIED,
    )
    db.add(transaction)

    if student:
        # Step 3: Split Allocation (FIFO)
        leftover = allocate_fifo(db, student, payload.deposit_amount)
        apply_overpayment_credit(db, student, leftover)

        # Step 4: Ledger already updated inside allocate_fifo; mark transaction reconciled
        transaction.settlement_status = SettlementStatus.RECONCILED

        remaining_balance = (
            db.query(Invoice)
            .filter(Invoice.student_id == student.id, Invoice.status != InvoiceStatus.PAID)
            .with_entities(Invoice.amount_due, Invoice.amount_paid)
            .all()
        )
        total_remaining = sum((due - paid) for due, paid in remaining_balance)

        send_receipt_sms(student, payload.deposit_amount, total_remaining)

    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/unidentified", response_model=List[BankTransactionOut])
def list_unidentified_deposits(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return (
        db.query(BankTransaction)
        .filter(BankTransaction.settlement_status == SettlementStatus.UNIDENTIFIED)
        .order_by(BankTransaction.created_at.desc())
        .all()
    )


@router.post("/{transaction_id}/manual-match", response_model=BankTransactionOut, dependencies=[Depends(senior_bursar)])
def manual_match_deposit(transaction_id: int, payload: ManualMatchRequest, db: Session = Depends(get_db)):
    """Maker-Checker: a bursar identifies the likely student for an unmatched deposit,
    but only a senior role (Head Teacher/Admin here) can approve posting it to the ledger."""
    transaction = db.query(BankTransaction).get(transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if transaction.settlement_status != SettlementStatus.UNIDENTIFIED:
        raise HTTPException(status_code=400, detail="This transaction has already been resolved")

    student = db.query(Student).get(payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    leftover = allocate_fifo(db, student, transaction.deposit_amount)
    apply_overpayment_credit(db, student, leftover)

    transaction.matched_student_id = student.id
    transaction.settlement_status = SettlementStatus.RECONCILED

    remaining_balance = (
        db.query(Invoice)
        .filter(Invoice.student_id == student.id, Invoice.status != InvoiceStatus.PAID)
        .with_entities(Invoice.amount_due, Invoice.amount_paid)
        .all()
    )
    total_remaining = sum((due - paid) for due, paid in remaining_balance)
    send_receipt_sms(student, transaction.deposit_amount, total_remaining)

    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/credits/{student_id}", response_model=StudentCreditOut)
def get_student_credit(student_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    credit = db.query(StudentCredit).filter(StudentCredit.student_id == student_id).first()
    if not credit:
        return StudentCreditOut(student_id=student_id, balance=Decimal("0"))
    return credit


@router.post("/{transaction_id}/reverse", response_model=BankTransactionOut, dependencies=[Depends(senior_bursar)])
def reverse_transaction(transaction_id: int, payload: ReversalRequest, db: Session = Depends(get_db)):
    """Handles bounced checks / reversed Mobile Money. The original transaction record is
    NEVER edited or deleted — its settlement_status changes to 'reversed', the affected
    invoice(s) are re-opened, and a penalty fee line item is optionally applied.
    This preserves the immutable audit trail while correcting the ledger."""
    transaction = db.query(BankTransaction).get(transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if transaction.settlement_status != SettlementStatus.RECONCILED:
        raise HTTPException(status_code=400, detail="Only reconciled transactions can be reversed")

    student = db.query(Student).get(transaction.matched_student_id) if transaction.matched_student_id else None
    if not student:
        raise HTTPException(status_code=400, detail="No matched student on this transaction to reverse against")

    # Re-open invoices this deposit had contributed to, oldest-affected-first, undoing up to the deposit amount
    remaining_to_reverse = transaction.deposit_amount
    invoices = (
        db.query(Invoice)
        .filter(Invoice.student_id == student.id)
        .order_by(Invoice.term_id.desc())
        .all()
    )
    for invoice in invoices:
        if remaining_to_reverse <= 0:
            break
        if invoice.amount_paid <= 0:
            continue
        undo_amount = min(remaining_to_reverse, invoice.amount_paid)
        invoice.amount_paid = invoice.amount_paid - undo_amount
        invoice.status = (
            InvoiceStatus.UNPAID if invoice.amount_paid == 0 else InvoiceStatus.PARTIALLY_PAID
        )
        remaining_to_reverse -= undo_amount

    # Any leftover comes out of credit balance rather than going negative on an invoice
    if remaining_to_reverse > 0:
        credit = db.query(StudentCredit).filter(StudentCredit.student_id == student.id).first()
        if credit:
            credit.balance = max(credit.balance - remaining_to_reverse, 0)

    # Optional penalty fee as its own line item on the student's most recent open invoice
    if payload.penalty_fee and payload.penalty_fee > 0:
        target_invoice = (
            db.query(Invoice)
            .filter(Invoice.student_id == student.id, Invoice.status != InvoiceStatus.PAID)
            .order_by(Invoice.term_id.desc())
            .first()
        )
        if target_invoice:
            from app.models.vote_head import InvoiceLineItem, VoteHead
            penalty_vote_head = db.query(VoteHead).filter(VoteHead.name == "Bounced Transaction Penalty").first()
            if not penalty_vote_head:
                penalty_vote_head = VoteHead(name="Bounced Transaction Penalty", is_optional=False)
                db.add(penalty_vote_head)
                db.flush()
            db.add(InvoiceLineItem(
                invoice_id=target_invoice.id, vote_head_id=penalty_vote_head.id, amount_due=payload.penalty_fee
            ))
            target_invoice.amount_due = target_invoice.amount_due + payload.penalty_fee
            if target_invoice.amount_paid < target_invoice.amount_due:
                target_invoice.status = (
                    InvoiceStatus.PARTIALLY_PAID if target_invoice.amount_paid > 0 else InvoiceStatus.UNPAID
                )

    transaction.settlement_status = SettlementStatus.REVERSED

    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/end-of-day-report", response_model=EndOfDayReportOut)
def end_of_day_report(
    report_date: date_cls = Query(...),
    official_bank_balance: float = Query(
        ..., description="The bank's reported total for the day, entered manually until a real bank API is connected"
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Compares total reconciled deposits for the day against the official bank figure.
    Any discrepancy, even a fraction of a shilling, is flagged for board-level attention."""
    transactions = (
        db.query(BankTransaction)
        .filter(
            BankTransaction.transaction_date == report_date,
            BankTransaction.settlement_status == SettlementStatus.RECONCILED,
        )
        .all()
    )
    total_reconciled = sum(float(t.deposit_amount) for t in transactions)
    discrepancy = round(official_bank_balance - total_reconciled, 2)

    unidentified_count = (
        db.query(BankTransaction)
        .filter(
            BankTransaction.transaction_date == report_date,
            BankTransaction.settlement_status == SettlementStatus.UNIDENTIFIED,
        )
        .count()
    )

    return EndOfDayReportOut(
        report_date=report_date,
        total_transactions_reconciled=len(transactions),
        total_amount_reconciled=total_reconciled,
        official_bank_balance=official_bank_balance,
        discrepancy=discrepancy,
        has_discrepancy=abs(discrepancy) > 0.01,
        unidentified_deposits_count=unidentified_count,
    )
