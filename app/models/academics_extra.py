from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # "Mathematics", "English", "Science", "Social Studies"
    school_class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)

    school_class = relationship("SchoolClass")


class ExamResult(Base):
    __tablename__ = "exam_results"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "subject_id", "term_id", "exam_set", name="uq_student_subject_term_set"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    term_id = Column(Integer, ForeignKey("terms.id"), nullable=False)
    exam_set = Column(String, nullable=False, default="end")  # "beginning", "mid" or "end"
    marks = Column(Numeric(5, 2), nullable=False)  # e.g. out of 100
    grade = Column(String, nullable=True)  # computed, e.g. "A", "D1", or a division

    student = relationship("Student")
    subject = relationship("Subject")
    term = relationship("Term")
