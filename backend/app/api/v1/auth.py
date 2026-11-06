from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def set_session_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        "pace_access",
        create_access_token(str(user.id)),
        httponly=True,
        secure=settings.secure_cookie,
        samesite="lax",
        max_age=settings.access_token_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if not settings.allow_registration:
        raise HTTPException(status_code=403, detail="Registration is disabled")
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, user)
    return user


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    set_session_cookie(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie("pace_access", path="/")


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user