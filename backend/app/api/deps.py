import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("pace_access")
    subject = decode_access_token(token) if token else None
    try:
        user_id = uuid.UUID(subject) if subject else None
    except ValueError:
        user_id = None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user