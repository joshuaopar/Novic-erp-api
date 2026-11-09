from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class VoteHead(Base):
    """A billing category: Tuition, Development Fund, Uniforms, Lab Fees, Transport, etc."""
    __tablename__ = "vote_heads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    is_optional = Column(Boolean, nullable=False, default=False)  # true for amenities like transport/music


class FeeStructureItem(Base):
    """How much a given vote-head costs for a class/term, split by day/boarder."""
    __tablename__ = "fee_structure_items"
    __table_args__ = (
        UniqueConstraint("vote_head_id", "school_class_id", "term_id", name="uq_votehead_class_term"),
    )

    id = Column(Integer, primary_key=True, index=True)
    vote_head_id = Column(Integer, ForeignKey("vote_heads.id"), nullable=False)
    school_class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    term_id = Column(Integer, ForeignKey("terms.id"), nullable=False)
    day_amount = Column(Numeric(12, 2), nullable=False)
    boarder_amount = Column(Numeric(12, 2), nullable=False)

    vote_head = relationship("VoteHead")
    school_class = relationship("SchoolClass")
    term = relationship("Term")


class InvoiceLineItem(Base):
    """One vote-head's charge within a student's invoice."""
    __tablename__ = "invoice_line_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    vote_head_id = Column(Integer, ForeignKey("vote_heads.id"), nullable=False)
    amount_due = Column(Numeric(12, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="line_items")
    vote_head = relationship("VoteHead")
