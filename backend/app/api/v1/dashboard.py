from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Activity, StrengthWorkout, User
from app.schemas.activity import ActivityResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    week_start = datetime.combine(now.date() - timedelta(days=now.weekday()), time.min, timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    rows = db.execute(
        select(
            func.count(Activity.id),
            func.coalesce(func.sum(Activity.distance_m), 0),
            func.coalesce(func.sum(Activity.duration_seconds), 0),
        ).where(Activity.user_id == user.id, Activity.started_at < now)
    ).one()
    strength_totals = db.execute(select(
        func.count(StrengthWorkout.id), func.coalesce(func.sum(StrengthWorkout.duration_seconds), 0)
    ).where(StrengthWorkout.user_id == user.id, StrengthWorkout.started_at < now)).one()
    weekly = db.execute(
        select(func.count(Activity.id), func.coalesce(func.sum(Activity.distance_m), 0)).where(
            Activity.user_id == user.id, Activity.started_at >= week_start, Activity.started_at < now
        )
    ).one()
    weekly_strength = db.execute(select(
        func.count(StrengthWorkout.id), func.coalesce(func.sum(StrengthWorkout.duration_seconds), 0)
    ).where(StrengthWorkout.user_id == user.id, StrengthWorkout.started_at >= week_start, StrengthWorkout.started_at < now)).one()
    monthly_count = db.scalar(
        select(func.count(Activity.id)).where(Activity.user_id == user.id, Activity.started_at >= month_start, Activity.started_at < now)
    )
    monthly_strength = db.scalar(select(func.count(StrengthWorkout.id)).where(
        StrengthWorkout.user_id == user.id, StrengthWorkout.started_at >= month_start, StrengthWorkout.started_at < now
    ))
    recent = db.scalars(
        select(Activity).where(Activity.user_id == user.id, Activity.started_at < now).order_by(Activity.started_at.desc()).limit(5)
    ).all()
    recent_strength = db.scalars(select(StrengthWorkout).where(
        StrengthWorkout.user_id == user.id, StrengthWorkout.started_at < now
    ).order_by(StrengthWorkout.started_at.desc()).limit(3)).all()
    return {
        "total_activities": rows[0] + strength_totals[0],
        "total_distance_m": float(rows[1]),
        "total_duration_seconds": int(rows[2] + strength_totals[1]),
        "week_activities": weekly[0] + weekly_strength[0],
        "week_distance_m": float(weekly[1]),
        "month_activities": (monthly_count or 0) + (monthly_strength or 0),
        "recent_activities": [ActivityResponse.model_validate(activity) for activity in recent],
        "recent_strength_workouts": [
            {"id": str(item.id), "title": item.title, "started_at": item.started_at, "duration_seconds": item.duration_seconds}
            for item in recent_strength
        ],
    }