from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Dormitory(Base):
    __tablename__ = "dormitories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # "Rose Dorm", "Lily Dorm"
    capacity = Column(Integer, nullable=False)
    matron_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)

    matron = relationship("Staff")
    allocations = relationship("BoardingAllocation", back_populates="dormitory", cascade="all, delete-orphan")


class BoardingAllocation(Base):
    __tablename__ = "boarding_allocations"
    __table_args__ = (
        UniqueConstraint("student_id", "term_id", name="uq_student_term_allocation"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    dormitory_id = Column(Integer, ForeignKey("dormitories.id"), nullable=False)
    term_id = Column(Integer, ForeignKey("terms.id"), nullable=False)
    bed_number = Column(String, nullable=True)

    student = relationship("Student")
    dormitory = relationship("Dormitory", back_populates="allocations")
    term = relationship("Term")
