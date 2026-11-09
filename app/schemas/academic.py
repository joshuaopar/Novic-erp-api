from datetime import date
from typing import Optional
from pydantic import BaseModel


class AcademicYearCreate(BaseModel):
    year: int
    is_current: bool = False


class AcademicYearOut(BaseModel):
    id: int
    year: int
    is_current: bool

    class Config:
        from_attributes = True


class TermCreate(BaseModel):
    academic_year_id: int
    name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False


class TermOut(BaseModel):
    id: int
    academic_year_id: int
    name: str
    start_date: Optional[date]
    end_date: Optional[date]
    is_current: bool

    class Config:
        from_attributes = True


class SchoolClassCreate(BaseModel):
    name: str
    level_order: int


class SchoolClassUpdate(BaseModel):
    name: Optional[str] = None
    level_order: Optional[int] = None


class SchoolClassOut(BaseModel):
    id: int
    name: str
    level_order: int

    class Config:
        from_attributes = True


class StreamCreate(BaseModel):
    school_class_id: int
    name: str
    class_teacher_id: Optional[int] = None


class StreamUpdate(BaseModel):
    name: Optional[str] = None
    class_teacher_id: Optional[int] = None


class StreamOut(BaseModel):
    id: int
    school_class_id: int
    name: str
    class_teacher_id: Optional[int]

    class Config:
        from_attributes = True
