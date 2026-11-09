from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.people import Student
from app.models.academic import Stream, SchoolClass, Term
from app.models.finance import Invoice, InvoiceStatus, Payment

router = APIRouter(prefix="/finance/reports", tags=["finance-reports"])


@router.get("/debtors-age-analysis")
def debtors_age_analysis(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Buckets every student's outstanding balance by how many days overdue their
    oldest unpaid invoice's term end date is. Standard 0-30 / 31-60 / 61-90 / 90+ buckets."""
    if as_of_date is None:
        as_of_date = date.today()

    invoices = db.query(Invoice).filter(Invoice.status != InvoiceStatus.PAID).all()

    buckets = {"current": [], "0-30": [], "31-60": [], "61-90": [], "90+": []}
    total_outstanding = 0.0

    for invoice in invoices:
        owed = float(invoice.amount_due - invoice.amount_paid)
        if owed <= 0:
            continue
        term = db.query(Term).get(invoice.term_id)
        student = db.query(Student).get(invoice.student_id)

        if not term or not term.end_date:
            bucket_key = "current"
            days_overdue = 0
        else:
            days_overdue = (as_of_date - term.end_date).days
            if days_overdue <= 0:
                bucket_key = "current"
            elif days_overdue <= 30:
                bucket_key = "0-30"
            elif days_overdue <= 60:
                bucket_key = "31-60"
            elif days_overdue <= 90:
                bucket_key = "61-90"
            else:
                bucket_key = "90+"

        buckets[bucket_key].append({
            "student_id": student.id,
            "student_name": student.full_name,
            "invoice_id": invoice.id,
            "amount_owed": owed,
            "days_overdue": max(days_overdue, 0),
        })
        total_outstanding += owed

    summary = {k: round(sum(e["amount_owed"] for e in v), 2) for k, v in buckets.items()}

    return {
        "as_of_date": as_of_date,
        "total_outstanding": round(total_outstanding, 2),
        "bucket_totals": summary,
        "buckets": buckets,
    }


@router.get("/collection-summary")
def collection_summary(
    term_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Expected revenue (total invoiced) vs actual cash collected for a term."""
    invoices = db.query(Invoice).filter(Invoice.term_id == term_id).all()

    total_expected = sum(float(inv.amount_due) for inv in invoices)
    total_collected = sum(float(inv.amount_paid) for inv in invoices)
    total_outstanding = total_expected - total_collected
    collection_rate = round((total_collected / total_expected) * 100, 1) if total_expected > 0 else 0

    status_breakdown = {}
    for status in InvoiceStatus:
        count = len([i for i in invoices if i.status == status])
        status_breakdown[status.value] = count

    return {
        "term_id": term_id,
        "total_students_invoiced": len(invoices),
        "total_expected_revenue": round(total_expected, 2),
        "total_collected": round(total_collected, 2),
        "total_outstanding": round(total_outstanding, 2),
        "collection_rate_percent": collection_rate,
        "status_breakdown": status_breakdown,
    }


@router.get("/collection-by-class")
def collection_by_class(
    term_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Same as collection-summary but broken down per class — useful for spotting
    which classes/streams are lagging in fee payment."""
    invoices = db.query(Invoice).filter(Invoice.term_id == term_id).all()

    by_class = {}
    for invoice in invoices:
        student = db.query(Student).get(invoice.student_id)
        stream = db.query(Stream).get(student.stream_id)
        school_class = db.query(SchoolClass).get(stream.school_class_id) if stream else None
        class_name = school_class.name if school_class else "Unknown"

        if class_name not in by_class:
            by_class[class_name] = {"expected": 0.0, "collected": 0.0, "student_count": 0}

        by_class[class_name]["expected"] += float(invoice.amount_due)
        by_class[class_name]["collected"] += float(invoice.amount_paid)
        by_class[class_name]["student_count"] += 1

    results = []
    for class_name, data in by_class.items():
        rate = round((data["collected"] / data["expected"]) * 100, 1) if data["expected"] > 0 else 0
        results.append({
            "class_name": class_name,
            "student_count": data["student_count"],
            "expected": round(data["expected"], 2),
            "collected": round(data["collected"], 2),
            "collection_rate_percent": rate,
        })

    results.sort(key=lambda r: r["collection_rate_percent"])
    return results
