import enum
from sqlalchemy import Column, Integer, String, Date, Enum, ForeignKey, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class LeaveRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    guardian_id = Column(Integer, ForeignKey("guardians.id"), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    attachment_url = Column(String, nullable=True)  # doctor's note, etc.
    status = Column(Enum(LeaveRequestStatus), nullable=False, default=LeaveRequestStatus.PENDING)
    reviewed_by_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student")
    guardian = relationship("Guardian")
    reviewed_by = relationship("Staff")
