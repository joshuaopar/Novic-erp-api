from typing import Optional
from pydantic import BaseModel


class DormitoryCreate(BaseModel):
    name: str
    capacity: int
    matron_staff_id: Optional[int] = None


class DormitoryOut(BaseModel):
    id: int
    name: str
    capacity: int
    matron_staff_id: Optional[int]

    class Config:
        from_attributes = True


class BoardingAllocationCreate(BaseModel):
    student_id: int
    dormitory_id: int
    term_id: int
    bed_number: Optional[str] = None


class BoardingAllocationOut(BaseModel):
    id: int
    student_id: int
    dormitory_id: int
    term_id: int
    bed_number: Optional[str]

    class Config:
        from_attributes = True
