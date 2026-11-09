import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Date
from sqlalchemy.orm import relationship
from app.core.database import Base


class BorrowStatus(str, enum.Enum):
    BORROWED = "borrowed"
    RETURNED = "returned"
    LOST = "lost"


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=True)
    isbn = Column(String, nullable=True)
    total_copies = Column(Integer, nullable=False, default=1)

    borrow_records = relationship("BorrowRecord", back_populates="book")


class BorrowRecord(Base):
    __tablename__ = "borrow_records"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    borrowed_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    returned_date = Column(Date, nullable=True)
    status = Column(Enum(BorrowStatus), nullable=False, default=BorrowStatus.BORROWED)

    book = relationship("Book", back_populates="borrow_records")
    student = relationship("Student")
