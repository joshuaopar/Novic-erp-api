from datetime import date
from typing import Optional, List
from pydantic import BaseModel
from app.models.people import BoardingStatus


class GuardianCreate(BaseModel):
    full_name: str
    relationship_to_student: Optional[str] = None
    phone_number: str
    alt_phone_number: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class GuardianOut(BaseModel):
    id: int
    full_name: str
    relationship_to_student: Optional[str]
    phone_number: str
    alt_phone_number: Optional[str]
    email: Optional[str]
    address: Optional[str]

    class Config:
        from_attributes = True


class StudentCreate(BaseModel):
    admission_number: str
    full_name: str
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    stream_id: int
    boarding_status: BoardingStatus = BoardingStatus.DAY
    guardian_ids: List[int] = []


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    stream_id: Optional[int] = None
    boarding_status: Optional[BoardingStatus] = None
    is_active: Optional[bool] = None
    photo_url: Optional[str] = None


class StudentOut(BaseModel):
    id: int
    admission_number: str
    full_name: str
    date_of_birth: Optional[date]
    sex: Optional[str]
    stream_id: int
    boarding_status: BoardingStatus
    is_active: bool
    photo_url: Optional[str] = None
    pay_code: Optional[str] = None
    guardians: List[GuardianOut] = []

    class Config:
        from_attributes = True
