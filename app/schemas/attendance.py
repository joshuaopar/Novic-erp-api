import enum
from datetime import date
from typing import List, Optional
from pydantic import BaseModel
from app.models.attendance import AttendanceStatus


class AbsenceReason(str, enum.Enum):
    SICK = "sick"
    UNEXCUSED = "unexcused"
    FAMILY = "family"
    OTHER = "other"


class AttendanceEntry(BaseModel):
    student_id: int
    status: AttendanceStatus = AttendanceStatus.PRESENT
    reason: Optional[AbsenceReason] = None


class AttendanceBulkCreate(BaseModel):
    term_id: int
    date: date
    entries: List[AttendanceEntry]


class AttendanceOut(BaseModel):
    id: int
    student_id: int
    term_id: int
    date: date
    status: AttendanceStatus
    reason: Optional[str]
    marked_by_staff_id: Optional[int]

    class Config:
        from_attributes = True
