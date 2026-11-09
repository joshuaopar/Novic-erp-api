from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel
from app.models.leave_request import LeaveRequestStatus


class LeaveRequestCreate(BaseModel):
    student_id: int
    guardian_id: Optional[int] = None
    start_date: date
    end_date: date
    reason: Optional[str] = None


class StudentLookupOut(BaseModel):
    id: int
    full_name: str
    class_name: str
    stream_name: str


class LeaveRequestOut(BaseModel):
    id: int
    student_id: int
    guardian_id: Optional[int]
    start_date: date
    end_date: date
    reason: Optional[str]
    attachment_url: Optional[str] = None
    status: LeaveRequestStatus
    reviewed_by_staff_id: Optional[int]
    submitted_at: Optional[datetime]

    class Config:
        from_attributes = True


class LeaveRequestReview(BaseModel):
    approve: bool
    term_id: Optional[int] = None  # required if approving, so attendance can be marked excused
