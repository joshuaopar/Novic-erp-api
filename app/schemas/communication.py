from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.communication import NotificationChannel, NotificationStatus


class SendToGuardianRequest(BaseModel):
    guardian_id: int
    message: str


class SendToClassRequest(BaseModel):
    school_class_id: int
    message: str


class NotificationOut(BaseModel):
    id: int
    guardian_id: int
    channel: NotificationChannel
    message: str
    status: NotificationStatus
    sent_at: Optional[datetime]

    class Config:
        from_attributes = True
