from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class SubjectCreate(BaseModel):
    name: str
    school_class_id: int


class SubjectOut(BaseModel):
    id: int
    name: str
    school_class_id: int

    class Config:
        from_attributes = True


class ExamResultEntry(BaseModel):
    student_id: int
    subject_id: int
    marks: Decimal


class ExamResultBulkCreate(BaseModel):
    term_id: int
    exam_set: str = "end"
    entries: List[ExamResultEntry]


class ExamResultOut(BaseModel):
    id: int
    student_id: int
    subject_id: int
    term_id: int
    exam_set: str = "end"
    marks: Decimal
    grade: Optional[str]

    class Config:
        from_attributes = True


class ReportCardSubject(BaseModel):
    subject_name: str
    marks: Decimal
    grade: Optional[str]


class ReportCardOut(BaseModel):
    student_id: int
    student_name: str
    term_id: int
    exam_set: str = "end"
    subjects: List[ReportCardSubject]
    total_marks: Decimal
    average_marks: Decimal
    
