from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.people import UserRole, Student
from app.models.discount import StudentDiscount, DiscountType
from app.schemas.discount import StudentDiscountCreate, StudentDiscountOut

router = APIRouter(prefix="/finance/discounts", tags=["finance-discounts"])

bursar_or_admin = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.BURSAR)
approver_only = require_roles(UserRole.ADMIN, UserRole.HEAD_TEACHER)


@router.post("", response_model=StudentDiscountOut)
def create_discount(
    payload: StudentDiscountCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    student = db.query(Student).get(payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Manual waivers require approval-level access (Head Teacher/Admin), per your spec's
    # "required approval log" — bursars can propose sibling/scholarship discounts freely,
    # but write-offs need a senior sign-off.
    if payload.discount_type == DiscountType.MANUAL_WAIVER:
        if current_user.role not in (UserRole.ADMIN, UserRole.HEAD_TEACHER):
            raise HTTPException(
                status_code=403,
                detail="Manual waivers require Head Teacher or Admin approval",
            )
    else:
        if current_user.role not in (UserRole.ADMIN, UserRole.HEAD_TEACHER, UserRole.BURSAR):
            raise HTTPException(status_code=403, detail="Not authorized to apply discounts")

    discount = StudentDiscount(
        **payload.dict(),
        approved_by_staff_id=None,  # linked staff profile, not the login user; left null unless explicitly set
    )
    db.add(discount)
    db.commit()
    db.refresh(discount)
    return discount


@router.get("", response_model=List[StudentDiscountOut])
def list_discounts(
    student_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(StudentDiscount)
    if student_id is not None:
        query = query.filter(StudentDiscount.student_id == student_id)
    if is_active is not None:
        query = query.filter(StudentDiscount.is_active == is_active)
    return query.all()


@router.post("/{discount_id}/deactivate", response_model=StudentDiscountOut, dependencies=[Depends(approver_only)])
def deactivate_discount(discount_id: int, db: Session = Depends(get_db)):
    discount = db.query(StudentDiscount).get(discount_id)
    if not discount:
        raise HTTPException(status_code=404, detail="Discount not found")
    discount.is_active = False
    db.commit()
    db.refresh(discount)
    return discount


@router.post("/detect-siblings", response_model=List[StudentDiscountOut], dependencies=[Depends(bursar_or_admin)])
def detect_and_apply_sibling_discounts(
    percentage: float = Query(10.0, description="Discount % to apply to each sibling beyond the first"),
    db: Session = Depends(get_db),
):
    """Scans all active students, groups by shared guardian, and applies a sibling discount
    to every student beyond the first in each guardian group (the eldest/first-listed pays full price)."""
    students = db.query(Student).filter(Student.is_active == True).all()  # noqa: E712

    guardian_groups = {}
    for student in students:
        for guardian in student.guardians:
            guardian_groups.setdefault(guardian.id, []).append(student)

    applied = []
    already_discounted_student_ids = set()

    for guardian_id, sibling_list in guardian_groups.items():
        if len(sibling_list) < 2:
            continue
        # Skip the first sibling (full price), discount the rest
        for student in sibling_list[1:]:
            if student.id in already_discounted_student_ids:
                continue  # avoid double-discounting a student who appears under multiple guardians

            existing = (
                db.query(StudentDiscount)
                .filter(
                    StudentDiscount.student_id == student.id,
                    StudentDiscount.discount_type == DiscountType.SIBLING,
                    StudentDiscount.is_active == True,  # noqa: E712
                )
                .first()
            )
            if existing:
                continue

            discount = StudentDiscount(
                student_id=student.id,
                discount_type=DiscountType.SIBLING,
                percentage=percentage,
                reason="Auto-detected sibling discount",
            )
            db.add(discount)
            applied.append(discount)
            already_discounted_student_ids.add(student.id)

    db.commit()
    for d in applied:
        db.refresh(d)
    return applied
