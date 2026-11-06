import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Activity, ActivityType, User
from app.schemas.activity import ActivityCreate, ActivityResponse, ActivityUpdate

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=list[ActivityResponse])
def list_activities(
    activity_type: ActivityType | None = None,
    search: str | None = Query(default=None, max_length=120),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Activity).where(Activity.user_id == user.id)
    if activity_type:
        query = query.where(Activity.activity_type == activity_type)
    if search:
        query = query.where(Activity.title.ilike(f"%{search}%"))
    return db.scalars(query.order_by(Activity.started_at.desc()).offset(offset).limit(limit)).all()


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    activity = Activity(**payload.model_dump(), user_id=user.id)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def owned_activity(activity_id: uuid.UUID, user: User, db: Session) -> Activity:
    activity = db.scalar(select(Activity).where(Activity.id == activity_id, Activity.user_id == user.id))
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(activity_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return owned_activity(activity_id, user, db)


@router.patch("/{activity_id}", response_model=ActivityResponse)
def update_activity(activity_id: uuid.UUID, payload: ActivityUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    activity = owned_activity(activity_id, user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(activity, field, value)
    db.commit()
    db.refresh(activity)
    return activity


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    activity = owned_activity(activity_id, user, db)
    db.delete(activity)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)