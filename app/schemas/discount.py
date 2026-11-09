from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, model_validator
from app.models.discount import DiscountType


class StudentDiscountCreate(BaseModel):
    student_id: int
    discount_type: DiscountType
    percentage: Optional[Decimal] = None
    fixed_amount: Optional[Decimal] = None
    reason: Optional[str] = None

    @model_validator(mode="after")
    def check_exactly_one_value(self):
        has_pct = self.percentage is not None
        has_fixed = self.fixed_amount is not None
        if has_pct == has_fixed:
            raise ValueError("Provide exactly one of percentage or fixed_amount, not both or neither")
        if has_pct and (self.percentage <= 0 or self.percentage > 100):
            raise ValueError("percentage must be between 0 and 100")
        return self


class StudentDiscountOut(BaseModel):
    id: int
    student_id: int
    discount_type: DiscountType
    percentage: Optional[Decimal]
    fixed_amount: Optional[Decimal]
    reason: Optional[str]
    approved_by_staff_id: Optional[int]
    is_active: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True
