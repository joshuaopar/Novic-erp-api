import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Enum, Table
from sqlalchemy.orm import relationship
from app.core.database import Base


class BoardingStatus(str, enum.Enum):
    DAY = "day"
    BOARDER = "boarder"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    HEAD_TEACHER = "head_teacher"
    BURSAR = "bursar"
    CLASS_TEACHER = "class_teacher"
    TEACHER = "teacher"
    MATRON = "matron"
    LIBRARIAN = "librarian"


student_guardian_association = Table(
    "student_guardian_association",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id"), primary_key=True),
    Column("guardian_id", Integer, ForeignKey("guardians.id"), primary_key=True),
)


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    email = Column(String, nullable=True)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="staff", uselist=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), unique=True, nullable=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)

    staff = relationship("Staff", back_populates="user")


class Guardian(Base):
    __tablename__ = "guardians"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    relationship_to_student = Column(String, nullable=True)
    phone_number = Column(String, nullable=False)
    alt_phone_number = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)

    students = relationship(
        "Student", secondary=student_guardian_association, back_populates="guardians"
    )


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    admission_number = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    sex = Column(String, nullable=True)
    stream_id = Column(Integer, ForeignKey("streams.id"), nullable=False)
    boarding_status = Column(Enum(BoardingStatus), default=BoardingStatus.DAY, nullable=False)
    photo_url = Column(String, nullable=True)
    pay_code = Column(String, unique=True, nullable=True, index=True)
    enrollment_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)

    stream = relationship("Stream", back_populates="students")
    guardians = relationship(
        "Guardian", secondary=student_guardian_association, back_populates="students"
    )
