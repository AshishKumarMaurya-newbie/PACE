import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Activity, PlannedWorkout, StrengthWorkout, TrainingPlan, User
from app.schemas.activity import ActivityResponse
from app.schemas.training import PlanCreate, PlanResponse, PlannedWorkoutCreate, PlannedWorkoutResponse

router = APIRouter(prefix="/training", tags=["training"])


@router.get("/plans", response_model=list[PlanResponse])
def list_plans(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(TrainingPlan).where(TrainingPlan.user_id == user.id).order_by(TrainingPlan.is_active.desc())).all()


@router.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plan = TrainingPlan(**payload.model_dump(), user_id=user.id)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/plans/{plan_id}/workouts", response_model=PlannedWorkoutResponse, status_code=status.HTTP_201_CREATED)
def create_planned_workout(plan_id: uuid.UUID, payload: PlannedWorkoutCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plan = db.scalar(select(TrainingPlan).where(TrainingPlan.id == plan_id, TrainingPlan.user_id == user.id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Training plan not found")
    workout = PlannedWorkout(**payload.model_dump(), plan_id=plan.id, user_id=user.id)
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout


@router.post("/workouts/{workout_id}/complete", response_model=PlannedWorkoutResponse)
def complete_planned_workout(workout_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    workout = db.scalar(select(PlannedWorkout).where(PlannedWorkout.id == workout_id, PlannedWorkout.user_id == user.id))
    if workout is None:
        raise HTTPException(status_code=404, detail="Planned workout not found")
    workout.is_completed = True
    db.commit()
    db.refresh(workout)
    return workout


@router.get("/calendar")
def calendar(
    start: date = Query(),
    end: date = Query(),
    timezone_name: str = Query(default="UTC", alias="timezone", max_length=80),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if end < start or (end - start).days > 370:
        raise HTTPException(status_code=422, detail="Choose a valid date range of at most 12 months")
    try:
        local_timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=422, detail="Choose a valid IANA timezone") from None
    start_utc = datetime.combine(start, time.min, local_timezone).astimezone(timezone.utc)
    end_utc = datetime.combine(end + timedelta(days=1), time.min, local_timezone).astimezone(timezone.utc)
    activities = db.scalars(select(Activity).where(
        Activity.user_id == user.id,
        Activity.started_at >= start_utc,
        Activity.started_at < end_utc,
    ).order_by(Activity.started_at)).all()
    planned = db.scalars(select(PlannedWorkout).where(
        PlannedWorkout.user_id == user.id,
        PlannedWorkout.scheduled_date >= start,
        PlannedWorkout.scheduled_date <= end,
    ).order_by(PlannedWorkout.scheduled_date)).all()
    strength = db.scalars(select(StrengthWorkout).where(
        StrengthWorkout.user_id == user.id,
        StrengthWorkout.started_at >= start_utc,
        StrengthWorkout.started_at < end_utc,
    ).order_by(StrengthWorkout.started_at)).all()
    return {
        "activities": [ActivityResponse.model_validate(item) for item in activities],
        "planned_workouts": [PlannedWorkoutResponse.model_validate(item) for item in planned],
        "strength_workouts": [
            {"id": str(item.id), "title": item.title, "started_at": item.started_at, "duration_seconds": item.duration_seconds}
            for item in strength
        ],
    }