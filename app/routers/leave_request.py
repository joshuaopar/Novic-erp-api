import os
import uuid
from typing import List, Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from datetime import date as date_cls
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.people import UserRole, Student
from app.models.academic import Stream, SchoolClass
from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.leave_request import LeaveRequest, LeaveRequestStatus
from app.schemas.leave_request import LeaveRequestOut, LeaveRequestReview, StudentLookupOut

router = APIRouter(prefix="/leave-requests", tags=["leave-requests"])

admin_roles = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.CLASS_TEACHER)


# ---- Public: look up a student by admission number (no login required) ----
# Used by the parent-facing leave request form so parents don't need staff accounts.

@router.get("/lookup-student", response_model=StudentLookupOut)
def lookup_student_by_admission_number(admission_number: str = Query(...), db: Session = Depends(get_db)):
    student = (
        db.query(Student)
        .filter(Student.admission_number == admission_number, Student.is_active == True)  # noqa: E712
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="No active student found with that admission number")

    stream = db.query(Stream).get(student.stream_id)
    school_class = db.query(SchoolClass).get(stream.school_class_id) if stream else None

    return StudentLookupOut(
        id=student.id,
        full_name=student.full_name,
        class_name=school_class.name if school_class else "",
        stream_name=stream.name if stream else "",
    )


# ---- Public: submit a leave request, optionally with a file attachment (e.g. doctor's note) ----

@router.post("", response_model=LeaveRequestOut)
def submit_leave_request(
    student_id: int = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    reason: Optional[str] = Form(None),
    guardian_id: Optional[int] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    try:
        start_date_parsed = date_cls.fromisoformat(start_date)
        end_date_parsed = date_cls.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Dates must be in YYYY-MM-DD format")

    if end_date_parsed < start_date_parsed:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    attachment_url = None
    if file is not None:
        allowed_extensions = {".jpg", ".jpeg", ".png", ".pdf"}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, pdf files are allowed")
        filename = f"{student_id}_{uuid.uuid4().hex[:8]}{ext}"
        filepath = os.path.join("uploads", "leave_attachments", filename)
        with open(filepath, "wb") as f:
            f.write(file.file.read())
        attachment_url = f"/uploads/leave_attachments/{filename}"

    leave = LeaveRequest(
        student_id=student_id,
        guardian_id=guardian_id,
        start_date=start_date_parsed,
        end_date=end_date_parsed,
        reason=reason,
        attachment_url=attachment_url,
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


# ---- Staff-only from here on ----

@router.get("", response_model=List[LeaveRequestOut], dependencies=[Depends(get_current_user)])
def list_leave_requests(
    status: Optional[LeaveRequestStatus] = Query(None),
    student_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(LeaveRequest)
    if status is not None:
        query = query.filter(LeaveRequest.status == status)
    if student_id is not None:
        query = query.filter(LeaveRequest.student_id == student_id)
    return query.order_by(LeaveRequest.submitted_at.desc()).all()


@router.post("/{leave_id}/review", response_model=LeaveRequestOut, dependencies=[Depends(admin_roles)])
def review_leave_request(leave_id: int, payload: LeaveRequestReview, db: Session = Depends(get_db)):
    leave = db.query(LeaveRequest).get(leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if leave.status != LeaveRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="This leave request has already been reviewed")

    if payload.approve:
        if not payload.term_id:
            raise HTTPException(status_code=400, detail="term_id is required when approving")

        leave.status = LeaveRequestStatus.APPROVED

        from datetime import date as date_cls
        start = date_cls.fromisoformat(str(leave.start_date))
        end = date_cls.fromisoformat(str(leave.end_date))
        current_date = start
        while current_date <= end:
            existing = (
                db.query(AttendanceRecord)
                .filter(
                    AttendanceRecord.student_id == leave.student_id,
                    AttendanceRecord.date == current_date,
                )
                .first()
            )
            if existing:
                existing.status = AttendanceStatus.EXCUSED
                existing.reason = "approved leave"
                existing.term_id = payload.term_id
            else:
                db.add(AttendanceRecord(
                    student_id=leave.student_id,
                    term_id=payload.term_id,
                    date=current_date,
                    status=AttendanceStatus.EXCUSED,
                    reason="approved leave",
                ))
            current_date += timedelta(days=1)
    else:
        leave.status = LeaveRequestStatus.REJECTED

    db.commit()
    db.refresh(leave)
    return leave
