from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.core.database import Base


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, unique=True, nullable=False)
    is_current = Column(Boolean, default=False)

    terms = relationship("Term", back_populates="academic_year", cascade="all, delete-orphan")


class Term(Base):
    __tablename__ = "terms"

    id = Column(Integer, primary_key=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_current = Column(Boolean, default=False)

    academic_year = relationship("AcademicYear", back_populates="terms")


class SchoolClass(Base):
    __tablename__ = "school_classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    level_order = Column(Integer, nullable=False)

    streams = relationship("Stream", back_populates="school_class", cascade="all, delete-orphan")


class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    school_class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    name = Column(String, nullable=False)
    class_teacher_id = Column(Integer, ForeignKey("staff.id"), nullable=True)

    school_class = relationship("SchoolClass", back_populates="streams")
    class_teacher = relationship("Staff", foreign_keys=[class_teacher_id])
    students = relationship("Student", back_populates="stream")
