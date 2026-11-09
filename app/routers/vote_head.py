from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.people import UserRole
from app.models.vote_head import VoteHead, FeeStructureItem
from app.schemas.vote_head import (
    VoteHeadCreate, VoteHeadOut,
    FeeStructureItemCreate, FeeStructureItemOut,
)

router = APIRouter(prefix="/finance/vote-heads", tags=["finance-vote-heads"])

bursar_or_admin = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.BURSAR)


@router.post("", response_model=VoteHeadOut, dependencies=[Depends(bursar_or_admin)])
def create_vote_head(payload: VoteHeadCreate, db: Session = Depends(get_db)):
    existing = db.query(VoteHead).filter(VoteHead.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vote-head already exists")
    vh = VoteHead(**payload.dict())
    db.add(vh)
    db.commit()
    db.refresh(vh)
    return vh


@router.get("", response_model=List[VoteHeadOut])
def list_vote_heads(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(VoteHead).all()


@router.post("/fee-structure-items", response_model=FeeStructureItemOut, dependencies=[Depends(bursar_or_admin)])
def create_fee_structure_item(payload: FeeStructureItemCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(FeeStructureItem)
        .filter(
            FeeStructureItem.vote_head_id == payload.vote_head_id,
            FeeStructureItem.school_class_id == payload.school_class_id,
            FeeStructureItem.term_id == payload.term_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="This vote-head is already configured for this class/term")

    item = FeeStructureItem(**payload.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/fee-structure-items", response_model=List[FeeStructureItemOut])
def list_fee_structure_items(
    school_class_id: Optional[int] = Query(None),
    term_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(FeeStructureItem)
    if school_class_id is not None:
        query = query.filter(FeeStructureItem.school_class_id == school_class_id)
    if term_id is not None:
        query = query.filter(FeeStructureItem.term_id == term_id)
    return query.all()
