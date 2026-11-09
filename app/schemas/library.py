from typing import Optional
from datetime import date
from pydantic import BaseModel
from app.models.library import BorrowStatus


class BookCreate(BaseModel):
    title: str
    author: Optional[str] = None
    isbn: Optional[str] = None
    total_copies: int = 1


class BookOut(BaseModel):
    id: int
    title: str
    author: Optional[str]
    isbn: Optional[str]
    total_copies: int
    copies_available: int

    class Config:
        from_attributes = True


class BorrowCreate(BaseModel):
    book_id: int
    student_id: int
    borrowed_date: date
    due_date: Optional[date] = None


class ReturnBook(BaseModel):
    returned_date: date


class BorrowRecordOut(BaseModel):
    id: int
    book_id: int
    student_id: int
    borrowed_date: date
    due_date: Optional[date]
    returned_date: Optional[date]
    status: BorrowStatus

    class Config:
        from_attributes = True
