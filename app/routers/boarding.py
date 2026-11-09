from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.people import UserRole, Student, BoardingStatus
from app.models.boarding import Dormitory, BoardingAllocation
from app.schemas.boarding import (
    DormitoryCreate, DormitoryOut,
    BoardingAllocationCreate, BoardingAllocationOut,
)

router = APIRouter(prefix="/boarding", tags=["boarding"])

boarding_staff = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.MATRON)


# ---- Dormitories ----

@router.post("/dormitories", response_model=DormitoryOut, dependencies=[Depends(boarding_staff)])
def create_dormitory(payload: DormitoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Dormitory).filter(Dormitory.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Dormitory already exists")
    dorm = Dormitory(**payload.dict())
    db.add(dorm)
    db.commit()
    db.refresh(dorm)
    return dorm


@router.get("/dormitories", response_model=List[DormitoryOut])
def list_dormitories(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(Dormitory).all()


# ---- Allocations ----

@router.post("/allocations", response_model=BoardingAllocationOut, dependencies=[Depends(boarding_staff)])
def allocate_student(payload: BoardingAllocationCreate, db: Session = Depends(get_db)):
    student = db.query(Student).get(payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.boarding_status != BoardingStatus.BOARDER:
        raise HTTPException(status_code=400, detail="Student is not marked as a boarder")

    dorm = db.query(Dormitory).get(payload.dormitory_id)
    if not dorm:
        raise HTTPException(status_code=404, detail="Dormitory not found")

    current_count = (
        db.query(BoardingAllocation)
        .filter(
            BoardingAllocation.dormitory_id == payload.dormitory_id,
            BoardingAllocation.term_id == payload.term_id,
        )
        .count()
    )
    if current_count >= dorm.capacity:
        raise HTTPException(status_code=400, detail="Dormitory is at full capacity for this term")

    existing = (
        db.query(BoardingAllocation)
        .filter(
            BoardingAllocation.student_id == payload.student_id,
            BoardingAllocation.term_id == payload.term_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Student already allocated for this term")

    allocation = BoardingAllocation(**payload.dict())
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation


@router.get("/allocations", response_model=List[BoardingAllocationOut])
def list_allocations(
    dormitory_id: Optional[int] = Query(None),
    term_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(BoardingAllocation)
    if dormitory_id is not None:
        query = query.filter(BoardingAllocation.dormitory_id == dormitory_id)
    if term_id is not None:
        query = query.filter(BoardingAllocation.term_id == term_id)
    return query.all()
