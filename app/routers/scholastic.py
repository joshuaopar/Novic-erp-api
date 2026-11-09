from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.people import UserRole, Student
from app.models.academic import Stream
from app.models.scholastic import RequirementItem, StudentRequirementStatus
from app.schemas.scholastic import (
    RequirementItemCreate, RequirementItemOut,
    SyncRequirementsRequest, SetFulfilledRequest, StudentRequirementStatusOut,
)

router = APIRouter(prefix="/scholastic", tags=["scholastic"])

teacher_roles = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.CLASS_TEACHER)


# ---- Requirement Items ----

@router.post("/items", response_model=RequirementItemOut, dependencies=[Depends(teacher_roles)])
def create_requirement_item(payload: RequirementItemCreate, db: Session = Depends(get_db)):
    item = RequirementItem(**payload.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/items", response_model=List[RequirementItemOut])
def list_requirement_items(
    school_class_id: Optional[int] = Query(None),
    term_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(RequirementItem)
    if school_class_id is not None:
        query = query.filter(RequirementItem.school_class_id == school_class_id)
    if term_id is not None:
        query = query.filter(RequirementItem.term_id == term_id)
    return query.all()


# ---- Sync statuses for all students in the item's class ----

@router.post("/sync", response_model=List[StudentRequirementStatusOut], dependencies=[Depends(teacher_roles)])
def sync_requirement_statuses(payload: SyncRequirementsRequest, db: Session = Depends(get_db)):
    item = db.query(RequirementItem).get(payload.requirement_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Requirement item not found")

    students = (
        db.query(Student)
        .join(Stream)
        .filter(Stream.school_class_id == item.school_class_id, Student.is_active == True)  # noqa: E712
        .all()
    )

    created = []
    for student in students:
        existing = (
            db.query(StudentRequirementStatus)
            .filter(
                StudentRequirementStatus.student_id == student.id,
                StudentRequirementStatus.requirement_item_id == item.id,
            )
            .first()
        )
        if existing:
            continue
        status_row = StudentRequirementStatus(student_id=student.id, requirement_item_id=item.id)
        db.add(status_row)
        created.append(status_row)

    db.commit()
    for s in created:
        db.refresh(s)
    return created


# ---- Toggle fulfilled status ----

@router.patch("/statuses/{status_id}", response_model=StudentRequirementStatusOut, dependencies=[Depends(teacher_roles)])
def set_fulfilled(status_id: int, payload: SetFulfilledRequest, db: Session = Depends(get_db)):
    status_row = db.query(StudentRequirementStatus).get(status_id)
    if not status_row:
        raise HTTPException(status_code=404, detail="Status record not found")
    status_row.is_fulfilled = payload.is_fulfilled
    db.commit()
    db.refresh(status_row)
    return status_row


@router.get("/statuses", response_model=List[StudentRequirementStatusOut])
def list_statuses(
    student_id: Optional[int] = Query(None),
    requirement_item_id: Optional[int] = Query(None),
    is_fulfilled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(StudentRequirementStatus)
    if student_id is not None:
        query = query.filter(StudentRequirementStatus.student_id == student_id)
    if requirement_item_id is not None:
        query = query.filter(StudentRequirementStatus.requirement_item_id == requirement_item_id)
    if is_fulfilled is not None:
        query = query.filter(StudentRequirementStatus.is_fulfilled == is_fulfilled)
    return query.all()
