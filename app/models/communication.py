import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class NotificationChannel(str, enum.Enum):
    SMS = "sms"
    EMAIL = "email"


class NotificationStatus(str, enum.Enum):
    SENT = "sent"
    FAILED = "failed"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    guardian_id = Column(Integer, ForeignKey("guardians.id"), nullable=False)
    channel = Column(Enum(NotificationChannel), nullable=False, default=NotificationChannel.SMS)
    message = Column(Text, nullable=False)
    status = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.SENT)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())

    guardian = relationship("Guardian")
