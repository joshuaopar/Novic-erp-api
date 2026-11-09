from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.people import User, UserRole
from app import models

Base.metadata.create_all(bind=engine)

db = SessionLocal()
existing = db.query(User).filter(User.username == "admin").first()
if existing:
    print("Admin user already exists.")
else:
    admin = User(
        username="admin",
        hashed_password=hash_password("admin123"),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()
    print("Seeded admin user -> username: admin / password: admin123")
db.close()
