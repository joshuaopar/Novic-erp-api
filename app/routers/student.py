import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.people import UserRole, Student, Guardian
from app.models.academic import Stream
from app.schemas.student import (
    StudentCreate, StudentUpdate, StudentOut,
    GuardianCreate, GuardianOut,
)

router = APIRouter(prefix="/students", tags=["students"])

admin_or_class_teacher = require_roles(
    UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.CLASS_TEACHER
)


# ---- Guardians ----

@router.post("/guardians", response_model=GuardianOut, dependencies=[Depends(admin_or_class_teacher)])
def create_guardian(payload: GuardianCreate, db: Session = Depends(get_db)):
    guardian = Guardian(**payload.dict())
    db.add(guardian)
    db.commit()
    db.refresh(guardian)
    return guardian


@router.get("/guardians", response_model=List[GuardianOut])
def list_guardians(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(Guardian).all()


# ---- Students ----

@router.post("", response_model=StudentOut, dependencies=[Depends(admin_or_class_teacher)])
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    existing = db.query(Student).filter(Student.admission_number == payload.admission_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Admission number already in use")

    stream = db.query(Stream).get(payload.stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    data = payload.dict(exclude={"guardian_ids"})
    student = Student(**data)

    if payload.guardian_ids:
        guardians = db.query(Guardian).filter(Guardian.id.in_(payload.guardian_ids)).all()
        student.guardians = guardians

    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("", response_model=List[StudentOut])
def list_students(
    stream_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Student)
    if stream_id is not None:
        query = query.filter(Student.stream_id == stream_id)
    if is_active is not None:
        query = query.filter(Student.is_active == is_active)
    return query.all()


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.patch("/{student_id}", response_model=StudentOut, dependencies=[Depends(admin_or_class_teacher)])
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)
    return student


@router.post("/{student_id}/photo", response_model=StudentOut, dependencies=[Depends(admin_or_class_teacher)])
def upload_student_photo(student_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp files are allowed")

    filename = f"{student_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join("uploads", "student_photos", filename)

    with open(filepath, "wb") as f:
        f.write(file.file.read())

    student.photo_url = f"/uploads/student_photos/{filename}"
    db.commit()
    db.refresh(student)
    return student


@router.post("/{student_id}/assign-pay-code", response_model=StudentOut, dependencies=[Depends(admin_or_class_teacher)])
def assign_pay_code(student_id: int, db: Session = Depends(get_db)):
    from datetime import datetime
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.pay_code:
        raise HTTPException(status_code=400, detail="Student already has a pay code")

    year = datetime.now().year
    code = f"SCH-{year}-{student.id:03d}"
    student.pay_code = code
    db.commit()
    db.refresh(student)
    return student
