from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.people import UserRole
from app.models.academic import AcademicYear, Term, SchoolClass, Stream
from app.schemas.academic import (
    AcademicYearCreate, AcademicYearOut,
    TermCreate, TermOut,
    SchoolClassCreate, SchoolClassOut, SchoolClassUpdate,
    StreamCreate, StreamOut, StreamUpdate,
)

router = APIRouter(prefix="/academic", tags=["academic"])

admin_only = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER)


# ---- Academic Years ----

@router.post("/years", response_model=AcademicYearOut, dependencies=[Depends(admin_only)])
def create_academic_year(payload: AcademicYearCreate, db: Session = Depends(get_db)):
    existing = db.query(AcademicYear).filter(AcademicYear.year == payload.year).first()
    if existing:
        raise HTTPException(status_code=400, detail="Academic year already exists")
    year = AcademicYear(**payload.dict())
    db.add(year)
    db.commit()
    db.refresh(year)
    return year


@router.get("/years", response_model=List[AcademicYearOut])
def list_academic_years(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(AcademicYear).order_by(AcademicYear.year.desc()).all()


# ---- Terms ----

@router.post("/terms", response_model=TermOut, dependencies=[Depends(admin_only)])
def create_term(payload: TermCreate, db: Session = Depends(get_db)):
    year = db.query(AcademicYear).get(payload.academic_year_id)
    if not year:
        raise HTTPException(status_code=404, detail="Academic year not found")
    term = Term(**payload.dict())
    db.add(term)
    db.commit()
    db.refresh(term)
    return term


@router.get("/terms", response_model=List[TermOut])
def list_terms(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(Term).all()


# ---- School Classes ----

@router.post("/classes", response_model=SchoolClassOut, dependencies=[Depends(admin_only)])
def create_class(payload: SchoolClassCreate, db: Session = Depends(get_db)):
    existing = db.query(SchoolClass).filter(SchoolClass.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Class already exists")
    school_class = SchoolClass(**payload.dict())
    db.add(school_class)
    db.commit()
    db.refresh(school_class)
    return school_class


@router.get("/classes", response_model=List[SchoolClassOut])
def list_classes(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(SchoolClass).order_by(SchoolClass.level_order).all()


@router.patch("/classes/{class_id}", response_model=SchoolClassOut, dependencies=[Depends(admin_only)])
def update_class(class_id: int, payload: SchoolClassUpdate, db: Session = Depends(get_db)):
    school_class = db.query(SchoolClass).get(class_id)
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(school_class, field, value)
    db.commit()
    db.refresh(school_class)
    return school_class


# ---- Streams ----

@router.post("/streams", response_model=StreamOut, dependencies=[Depends(admin_only)])
def create_stream(payload: StreamCreate, db: Session = Depends(get_db)):
    school_class = db.query(SchoolClass).get(payload.school_class_id)
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")

    existing = (
        db.query(Stream)
        .filter(Stream.school_class_id == payload.school_class_id, Stream.name == payload.name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="This stream already exists for this class")
    stream = Stream(**payload.dict())
    db.add(stream)
    db.commit()
    db.refresh(stream)
    return stream


@router.get("/streams", response_model=List[StreamOut])
def list_streams(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(Stream).all()


@router.patch("/streams/{stream_id}", response_model=StreamOut, dependencies=[Depends(admin_only)])
def update_stream(stream_id: int, payload: StreamUpdate, db: Session = Depends(get_db)):
    stream = db.query(Stream).get(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(stream, field, value)
    db.commit()
    db.refresh(stream)
    return stream
