from typing import List, Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.sms import send_sms
from app.models.people import UserRole, Student
from app.models.finance import Invoice, InvoiceStatus
from app.models.communication import Notification, NotificationStatus
from app.models.academic import Term

router = APIRouter(prefix="/finance/dunning", tags=["finance-dunning"])

bursar_or_admin = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.BURSAR)


@router.get("/overdue")
def list_overdue_invoices(
    term_id: int = Query(...),
    days_overdue: int = Query(7, description="Only include invoices whose term ended at least this many days ago"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    term = db.query(Term).get(term_id)
    if not term or not term.end_date:
        return {"detail": "Term not found or has no end_date set — cannot calculate overdue status", "results": []}

    cutoff = term.end_date + timedelta(days=days_overdue)
    if date.today() < cutoff:
        return {"detail": f"Not yet overdue — becomes overdue on {cutoff}", "results": []}

    invoices = (
        db.query(Invoice)
        .filter(Invoice.term_id == term_id, Invoice.status != InvoiceStatus.PAID)
        .all()
    )

    results = []
    for invoice in invoices:
        student = db.query(Student).get(invoice.student_id)
        results.append({
            "invoice_id": invoice.id,
            "student_id": student.id,
            "student_name": student.full_name,
            "amount_owed": float(invoice.amount_due - invoice.amount_paid),
            "days_overdue": (date.today() - cutoff).days + days_overdue,
        })

    return {"detail": None, "results": results}


@router.post("/send-reminders", dependencies=[Depends(bursar_or_admin)])
def send_overdue_reminders(
    term_id: int = Query(...),
    days_overdue: int = Query(7),
    db: Session = Depends(get_db),
):
    term = db.query(Term).get(term_id)
    if not term or not term.end_date:
        return {"sent": 0, "detail": "Term has no end_date set"}

    cutoff = term.end_date + timedelta(days=days_overdue)
    if date.today() < cutoff:
        return {"sent": 0, "detail": f"Not yet overdue — becomes overdue on {cutoff}"}

    invoices = (
        db.query(Invoice)
        .filter(Invoice.term_id == term_id, Invoice.status != InvoiceStatus.PAID)
        .all()
    )

    sent_count = 0
    for invoice in invoices:
        student = db.query(Student).get(invoice.student_id)
        owed = invoice.amount_due - invoice.amount_paid
        message = (
            f"Dear Parent, {student.full_name}'s school fees balance of UGX {owed:,.0f} "
            f"is now overdue. Kindly settle using pay code {student.pay_code or 'N/A'}. Thank you."
        )
        for guardian in student.guardians:
            success = send_sms(guardian.phone_number, message)
            notification = Notification(
                guardian_id=guardian.id,
                message=message,
                status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
            )
            db.add(notification)
            sent_count += 1

    db.commit()
    return {"sent": sent_count, "detail": None}


@router.get("/exam-clearance")
def exam_clearance_check(
    term_id: int = Query(...),
    school_class_id: Optional[int] = Query(None),
    clearance_threshold_percent: float = Query(
        100.0, description="Minimum % of fees that must be paid to be cleared (100 = fully paid)"
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models.academic import Stream

    query = db.query(Invoice).filter(Invoice.term_id == term_id)
    invoices = query.all()

    cleared = []
    not_cleared = []

    for invoice in invoices:
        student = db.query(Student).get(invoice.student_id)
        if school_class_id is not None:
            stream = db.query(Stream).get(student.stream_id)
            if not stream or stream.school_class_id != school_class_id:
                continue

        paid_percent = (
            float(invoice.amount_paid / invoice.amount_due * 100) if invoice.amount_due > 0 else 100
        )
        entry = {
            "student_id": student.id,
            "student_name": student.full_name,
            "amount_due": float(invoice.amount_due),
            "amount_paid": float(invoice.amount_paid),
            "paid_percent": round(paid_percent, 1),
        }
        if paid_percent >= clearance_threshold_percent:
            cleared.append(entry)
        else:
            not_cleared.append(entry)

    return {"cleared": cleared, "not_cleared": not_cleared}
