import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User


def create_user() -> None:
    email = input("Email: ").strip().lower()
    full_name = input("Name: ").strip()
    password = getpass.getpass("Password (10+ characters): ")
    if len(password) < 10:
        raise SystemExit("Password must contain at least 10 characters.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("An account with this email already exists.")
        user = User(email=email, full_name=full_name, password_hash=hash_password(password))
        db.add(user)
        db.commit()
    print(f"Created account for {email}.")


if __name__ == "__main__":
    create_user()