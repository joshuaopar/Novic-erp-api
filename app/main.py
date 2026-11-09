from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.core.deps import get_current_user
from app.models.people import User
from app.routers import auth, academic, student, attendance, finance, academics_extra, boarding, library, payroll, staff, scholastic, communication, leave_request, vote_head, reconciliation, discount, dunning, finance_reports
from app import models

app = FastAPI(title="School ERP API")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.include_router(auth.router)
app.include_router(academic.router)
app.include_router(student.router)
app.include_router(attendance.router)
app.include_router(finance.router)
app.include_router(academics_extra.router)
app.include_router(boarding.router)
app.include_router(library.router)
app.include_router(payroll.router)
app.include_router(staff.router)
app.include_router(scholastic.router)
app.include_router(communication.router)
app.include_router(leave_request.router)
app.include_router(vote_head.router)
app.include_router(reconciliation.router)
app.include_router(discount.router)
app.include_router(dunning.router)
app.include_router(finance_reports.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/me")
def read_current_user(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role.value}
