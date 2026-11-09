from typing import Optional
from pydantic import BaseModel
from app.models.people import UserRole


class StaffCreate(BaseModel):
    full_name: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    role: UserRole


class StaffOut(BaseModel):
    id: int
    full_name: str
    phone_number: Optional[str]
    email: Optional[str]
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True
