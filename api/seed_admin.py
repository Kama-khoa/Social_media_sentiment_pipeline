"""Chạy 1 lần để tạo admin user mặc định: python -m api.seed_admin"""
import uuid
from datetime import datetime, timezone

from api.auth import hash_password
from api.database import SessionLocal, init_db
from api.models import AppUser


def seed():
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(AppUser).filter(AppUser.email == "admin@example.com").first()
        if existing:
            print("Admin user already exists.")
            return

        admin = AppUser(
            id=str(uuid.uuid4()),
            email="admin@example.com",
            display_name="Admin",
            hashed_password=hash_password("admin1234"),
            role="admin",
            created_at=datetime.now(timezone.utc),
        )
        user = AppUser(
            id=str(uuid.uuid4()),
            email="user@example.com",
            display_name="Demo User",
            hashed_password=hash_password("user1234"),
            role="user",
            created_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.add(user)
        db.commit()
        print("Seeded accounts:")
        print("  Admin: admin@example.com / admin1234")
        print("  User:  user@example.com  / user1234")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
