from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.sms import send_sms
from app.models.people import UserRole, Guardian, Student
from app.models.academic import Stream
from app.models.communication import Notification, NotificationStatus
from app.schemas.communication import SendToGuardianRequest, SendToClassRequest, NotificationOut

router = APIRouter(prefix="/communication", tags=["communication"])

staff_roles = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.BURSAR, UserRole.CLASS_TEACHER)


def log_and_send(db: Session, guardian: Guardian, message: str) -> Notification:
    success = send_sms(guardian.phone_number, message)
    notification = Notification(
        guardian_id=guardian.id,
        message=message,
        status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
    )
    db.add(notification)
    return notification


@router.post("/send", response_model=NotificationOut, dependencies=[Depends(staff_roles)])
def send_to_guardian(payload: SendToGuardianRequest, db: Session = Depends(get_db)):
    guardian = db.query(Guardian).get(payload.guardian_id)
    if not guardian:
        raise HTTPException(status_code=404, detail="Guardian not found")

    notification = log_and_send(db, guardian, payload.message)
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/send-to-class", response_model=List[NotificationOut], dependencies=[Depends(staff_roles)])
def send_to_class(payload: SendToClassRequest, db: Session = Depends(get_db)):
    students = (
        db.query(Student)
        .join(Stream)
        .filter(Stream.school_class_id == payload.school_class_id, Student.is_active == True)  # noqa: E712
        .all()
    )

    sent = []
    seen_guardian_ids = set()
    for student in students:
        for guardian in student.guardians:
            if guardian.id in seen_guardian_ids:
                continue  # avoid double-messaging a guardian with multiple kids in the same class
            seen_guardian_ids.add(guardian.id)
            notification = log_and_send(db, guardian, payload.message)
            sent.append(notification)

    db.commit()
    for n in sent:
        db.refresh(n)
    return sent


@router.get("", response_model=List[NotificationOut])
def list_notifications(
    guardian_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Notification)
    if guardian_id is not None:
        query = query.filter(Notification.guardian_id == guardian_id)
    return query.order_by(Notification.sent_at.desc()).all()
