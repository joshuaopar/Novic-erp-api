from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.people import UserRole, Student
from app.models.academics_extra import Subject, ExamResult
from app.schemas.academics_extra import (
    SubjectCreate, SubjectOut,
    ExamResultBulkCreate, ExamResultOut,
    ReportCardOut, ReportCardSubject,
)

router = APIRouter(prefix="/academics", tags=["exams"])

teacher_roles = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.CLASS_TEACHER, UserRole.TEACHER)

EXAM_SETS = ("beginning", "mid", "end")


def check_exam_set(value: Optional[str]) -> str:
    v = (value or "").strip().lower()
    if v not in EXAM_SETS:
        raise HTTPException(status_code=400, detail="exam_set must be beginning, mid or end")
    return v


def calculate_grade(marks: Decimal) -> str:
    """Simple primary-school grading scale. Adjust boundaries to match your school's real scale."""
    m = float(marks)
    if m >= 80:
        return "A"
    elif m >= 70:
        return "B"
    elif m >= 60:
        return "C"
    elif m >= 50:
        return "D"
    else:
        return "F"


# ---- Subjects ----

@router.post("/subjects", response_model=SubjectOut, dependencies=[Depends(teacher_roles)])
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)):
    subject = Subject(**payload.dict())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.get("/subjects", response_model=List[SubjectOut])
def list_subjects(
    school_class_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Subject)
    if school_class_id is not None:
        query = query.filter(Subject.school_class_id == school_class_id)
    return query.all()


# ---- Exam Results ----

@router.post("/exam-results", response_model=List[ExamResultOut], dependencies=[Depends(teacher_roles)])
def record_exam_results(payload: ExamResultBulkCreate, db: Session = Depends(get_db)):
    exam_set = check_exam_set(payload.exam_set)
    for entry in payload.entries:
        if entry.marks < 0 or entry.marks > 100:
            raise HTTPException(status_code=400, detail="Marks must be between 0 and 100")

    results = []
    for entry in payload.entries:
        grade = calculate_grade(entry.marks)
        existing = (
            db.query(ExamResult)
            .filter(
                ExamResult.student_id == entry.student_id,
                ExamResult.subject_id == entry.subject_id,
                ExamResult.term_id == payload.term_id,
                ExamResult.exam_set == exam_set,
            )
            .first()
        )
        if existing:
            existing.marks = entry.marks
            existing.grade = grade
            record = existing
        else:
            record = ExamResult(
                student_id=entry.student_id,
                subject_id=entry.subject_id,
                term_id=payload.term_id,
                exam_set=exam_set,
                marks=entry.marks,
                grade=grade,
            )
            db.add(record)
        results.append(record)

    db.commit()
    for r in results:
        db.refresh(r)
    return results


@router.get("/exam-results", response_model=List[ExamResultOut])
def list_exam_results(
    student_id: Optional[int] = Query(None),
    term_id: Optional[int] = Query(None),
    subject_id: Optional[int] = Query(None),
    exam_set: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(ExamResult)
    if student_id is not None:
        query = query.filter(ExamResult.student_id == student_id)
    if term_id is not None:
        query = query.filter(ExamResult.term_id == term_id)
    if subject_id is not None:
        query = query.filter(ExamResult.subject_id == subject_id)
    if exam_set is not None:
        query = query.filter(ExamResult.exam_set == check_exam_set(exam_set))
    return query.all()


# ---- Report Card ----

@router.get("/report-card/{student_id}/{term_id}", response_model=ReportCardOut)
def get_report_card(
    student_id: int,
    term_id: int,
    exam_set: str = Query("end"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    exam_set = check_exam_set(exam_set)
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    results = (
        db.query(ExamResult)
        .filter(
            ExamResult.student_id == student_id,
            ExamResult.term_id == term_id,
            ExamResult.exam_set == exam_set,
        )
        .all()
    )
    if not results:
        raise HTTPException(status_code=404, detail="No exam results found for this student/term/exam set")

    subjects = []
    total = Decimal("0")
    for r in results:
        subject = db.query(Subject).get(r.subject_id)
        subjects.append(ReportCardSubject(subject_name=subject.name, marks=r.marks, grade=r.grade))
        total += r.marks

    average = total / len(results)

    return ReportCardOut(
        student_id=student.id,
        student_name=student.full_name,
        term_id=term_id,
        exam_set=exam_set,
        subjects=subjects,
        total_marks=total,
        average_marks=average,
    )
    
