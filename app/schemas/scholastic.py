from typing import Optional, List
from pydantic import BaseModel


class RequirementItemCreate(BaseModel):
    school_class_id: int
    term_id: int
    name: str
    quantity: int = 1


class RequirementItemOut(BaseModel):
    id: int
    school_class_id: int
    term_id: int
    name: str
    quantity: int

    class Config:
        from_attributes = True


class SyncRequirementsRequest(BaseModel):
    """Creates a StudentRequirementStatus row (unfulfilled) for every student in the class for a given requirement."""
    requirement_item_id: int


class SetFulfilledRequest(BaseModel):
    is_fulfilled: bool


class StudentRequirementStatusOut(BaseModel):
    id: int
    student_id: int
    requirement_item_id: int
    is_fulfilled: bool

    class Config:
        from_attributes = True
