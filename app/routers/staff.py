from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.people import UserRole, Staff
from app.schemas.staff import StaffCreate, StaffOut

router = APIRouter(prefix="/staff", tags=["staff"])

admin_only = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER)


@router.post("", response_model=StaffOut, dependencies=[Depends(admin_only)])
def create_staff(payload: StaffCreate, db: Session = Depends(get_db)):
    staff = Staff(**payload.dict())
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.get("", response_model=List[StaffOut])
def list_staff(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(Staff).all()
