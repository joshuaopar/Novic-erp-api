from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.people import UserRole
from app.models.library import Book, BorrowRecord, BorrowStatus
from app.schemas.library import (
    BookCreate, BookOut, BorrowCreate, ReturnBook, BorrowRecordOut,
)

router = APIRouter(prefix="/library", tags=["library"])

librarian_roles = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.LIBRARIAN)


def book_to_out(db: Session, book: Book) -> BookOut:
    borrowed_count = (
        db.query(BorrowRecord)
        .filter(BorrowRecord.book_id == book.id, BorrowRecord.status == BorrowStatus.BORROWED)
        .count()
    )
    return BookOut(
        id=book.id,
        title=book.title,
        author=book.author,
        isbn=book.isbn,
        total_copies=book.total_copies,
        copies_available=book.total_copies - borrowed_count,
    )


# ---- Books ----

@router.post("/books", response_model=BookOut, dependencies=[Depends(librarian_roles)])
def create_book(payload: BookCreate, db: Session = Depends(get_db)):
    book = Book(**payload.dict())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book_to_out(db, book)


@router.get("/books", response_model=List[BookOut])
def list_books(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    books = db.query(Book).all()
    return [book_to_out(db, b) for b in books]


# ---- Borrowing ----

@router.post("/borrow", response_model=BorrowRecordOut, dependencies=[Depends(librarian_roles)])
def borrow_book(payload: BorrowCreate, db: Session = Depends(get_db)):
    book = db.query(Book).get(payload.book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    borrowed_count = (
        db.query(BorrowRecord)
        .filter(BorrowRecord.book_id == book.id, BorrowRecord.status == BorrowStatus.BORROWED)
        .count()
    )
    if borrowed_count >= book.total_copies:
        raise HTTPException(status_code=400, detail="No copies available")

    record = BorrowRecord(**payload.dict())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/return/{borrow_id}", response_model=BorrowRecordOut, dependencies=[Depends(librarian_roles)])
def return_book(borrow_id: int, payload: ReturnBook, db: Session = Depends(get_db)):
    record = db.query(BorrowRecord).get(borrow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Borrow record not found")
    if record.status != BorrowStatus.BORROWED:
        raise HTTPException(status_code=400, detail="This book was already returned or marked lost")

    record.status = BorrowStatus.RETURNED
    record.returned_date = payload.returned_date
    db.commit()
    db.refresh(record)
    return record


@router.get("/borrow-records", response_model=List[BorrowRecordOut])
def list_borrow_records(
    student_id: Optional[int] = Query(None),
    status: Optional[BorrowStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(BorrowRecord)
    if student_id is not None:
        query = query.filter(BorrowRecord.student_id == student_id)
    if status is not None:
        query = query.filter(BorrowRecord.status == status)
    return query.all()
