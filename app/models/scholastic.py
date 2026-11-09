from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class RequirementItem(Base):
    """A required item for a class in a given term, e.g. '4 exercise books', 'PE uniform'."""
    __tablename__ = "requirement_items"

    id = Column(Integer, primary_key=True, index=True)
    school_class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    term_id = Column(Integer, ForeignKey("terms.id"), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    school_class = relationship("SchoolClass")
    term = relationship("Term")
    statuses = relationship("StudentRequirementStatus", back_populates="requirement_item", cascade="all, delete-orphan")


class StudentRequirementStatus(Base):
    __tablename__ = "student_requirement_statuses"
    __table_args__ = (
        UniqueConstraint("student_id", "requirement_item_id", name="uq_student_requirement"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    requirement_item_id = Column(Integer, ForeignKey("requirement_items.id"), nullable=False)
    is_fulfilled = Column(Boolean, nullable=False, default=False)

    student = relationship("Student")
    requirement_item = relationship("RequirementItem", back_populates="statuses")
