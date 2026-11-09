from typing import List, Optional
from datetime import date as date_type, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.sms import send_sms
from app.models.people import UserRole, Student
from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.attendance import AttendanceRecord
from app.models.communication import Notification, NotificationStatus
from app.schemas.attendance import AttendanceBulkCreate, AttendanceOut

router = APIRouter(prefix="/attendance", tags=["attendance"])

teacher_roles = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.CLASS_TEACHER, UserRole.TEACHER)


@router.post("/mark", response_model=List[AttendanceOut], dependencies=[Depends(teacher_roles)])
def mark_attendance(payload: AttendanceBulkCreate, db: Session = Depends(get_db)):
    results = []
    for entry in payload.entries:
        existing = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.student_id == entry.student_id,
                AttendanceRecord.date == payload.date,
            )
            .first()
        )
        if existing:
            existing.status = entry.status
            existing.term_id = payload.term_id
            existing.reason = entry.reason
            record = existing
        else:
            record = AttendanceRecord(
                student_id=entry.student_id,
                term_id=payload.term_id,
                date=payload.date,
                status=entry.status,
                reason=entry.reason,
            )
            db.add(record)
        results.append(record)

    db.commit()
    for r in results:
        db.refresh(r)

    # Alert guardians of any student marked absent in this batch
    for entry in payload.entries:
        if entry.status == "absent":
            student = db.query(Student).get(entry.student_id)
            if student:
                reason_suffix = f" Reason: {entry.reason.value}." if entry.reason else ""
                for guardian in student.guardians:
                    message = f"{student.full_name} was marked ABSENT today ({payload.date}).{reason_suffix}"
                    success = send_sms(guardian.phone_number, message)
                    notification = Notification(
                        guardian_id=guardian.id,
                        message=message,
                        status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
                    )
                    db.add(notification)
    db.commit()

    return results


@router.get("", response_model=List[AttendanceOut])
def list_attendance(
    student_id: Optional[int] = Query(None),
    date: Optional[date_type] = Query(None),
    term_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(AttendanceRecord)
    if student_id is not None:
        query = query.filter(AttendanceRecord.student_id == student_id)
    if date is not None:
        query = query.filter(AttendanceRecord.date == date)
    if term_id is not None:
        query = query.filter(AttendanceRecord.term_id == term_id)
    return query.all()


# ---- Reports ----

@router.get("/report/{student_id}")
def monthly_attendance_report(
    student_id: int,
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    records = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.date >= date_type(year, month, 1),
            AttendanceRecord.date < date_type(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1),
        )
        .all()
    )

    counts = defaultdict(int)
    for r in records:
        counts[r.status.value] += 1

    total = len(records)
    present_like = counts.get("present", 0) + counts.get("late", 0)
    rate = round((present_like / total) * 100, 1) if total > 0 else None

    return {
        "student_id": student_id,
        "student_name": student.full_name,
        "year": year,
        "month": month,
        "total_days_recorded": total,
        "present": counts.get("present", 0),
        "absent": counts.get("absent", 0),
        "late": counts.get("late", 0),
        "excused": counts.get("excused", 0),
        "attendance_rate": rate,
    }


@router.get("/flags")
def attendance_flags(
    term_id: int = Query(...),
    rate_threshold: float = Query(80.0, description="Flag if attendance rate falls below this percent"),
    consecutive_threshold: int = Query(3, description="Flag if student has this many consecutive absent days"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    students = db.query(Student).filter(Student.is_active == True).all()  # noqa: E712
    flagged = []

    for student in students:
        records = (
            db.query(AttendanceRecord)
            .filter(AttendanceRecord.student_id == student.id, AttendanceRecord.term_id == term_id)
            .order_by(AttendanceRecord.date)
            .all()
        )
        if not records:
            continue

        present_like = sum(1 for r in records if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE))
        rate = round((present_like / len(records)) * 100, 1)

        max_consecutive_absent = 0
        current_streak = 0
        prev_date = None
        for r in records:
            if r.status == AttendanceStatus.ABSENT:
                if prev_date is not None and (r.date - prev_date).days == 1:
                    current_streak += 1
                else:
                    current_streak = 1
                max_consecutive_absent = max(max_consecutive_absent, current_streak)
            else:
                current_streak = 0
            prev_date = r.date

        reasons = []
        if rate < rate_threshold:
            reasons.append(f"attendance rate {rate}% below {rate_threshold}%")
        if max_consecutive_absent >= consecutive_threshold:
            reasons.append(f"{max_consecutive_absent} consecutive days absent")

        if reasons:
            flagged.append({
                "student_id": student.id,
                "student_name": student.full_name,
                "attendance_rate": rate,
                "max_consecutive_absent": max_consecutive_absent,
                "reasons": reasons,
            })

    return flagged
