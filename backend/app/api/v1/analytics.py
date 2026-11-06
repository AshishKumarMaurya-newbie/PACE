from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Activity, ActivityType, User
from app.models.strength import ExerciseSet, StrengthExercise, StrengthWorkout

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    totals = db.execute(select(
        func.count(Activity.id),
        func.coalesce(func.sum(Activity.distance_m), 0),
        func.coalesce(func.sum(Activity.duration_seconds), 0),
    ).where(Activity.user_id == user.id, Activity.started_at < now)).one()
    distribution = db.execute(select(Activity.activity_type, func.count(Activity.id)).where(
        Activity.user_id == user.id, Activity.started_at < datetime.now(timezone.utc)
    ).group_by(Activity.activity_type)).all()
    strength_workouts, strength_duration = db.execute(select(
        func.count(StrengthWorkout.id), func.coalesce(func.sum(StrengthWorkout.duration_seconds), 0)
    ).where(StrengthWorkout.user_id == user.id, StrengthWorkout.started_at < datetime.now(timezone.utc))).one()
    run_distance, run_duration = db.execute(select(
        func.coalesce(func.sum(Activity.distance_m), 0),
        func.coalesce(func.sum(Activity.duration_seconds), 0),
    ).where(
        Activity.user_id == user.id,
        Activity.activity_type == ActivityType.run,
        Activity.distance_m.is_not(None),
        Activity.started_at < now,
    )).one()
    run_distance_m = float(run_distance)
    return {
        "activity_count": totals[0] + strength_workouts,
        "distance_m": float(totals[1]),
        "duration_seconds": int(totals[2] + strength_duration),
        "activity_distribution": [{"type": kind.value, "count": count} for kind, count in distribution],
        "strength_workouts": strength_workouts,
        "running": {
            "distance_m": run_distance_m,
            "duration_seconds": int(run_duration),
            "average_elapsed_pace_seconds_per_km": round(run_duration / (run_distance_m / 1000), 1) if run_distance_m > 0 else None,
        },
    }


@router.get("/trends")
def trends(
    period: str = Query(default="week", pattern="^(week|month|year)$"),
    activity_type: ActivityType | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    count = {"week": 12, "month": 12, "year": 5}[period]
    if period == "week":
        start = (now - timedelta(weeks=count - 1)).date()
        start -= timedelta(days=start.weekday())
    elif period == "month":
        start = date(now.year, now.month, 1)
        for _ in range(count - 1):
            start = date(start.year - (start.month == 1), start.month - 1 if start.month > 1 else 12, 1)
    else:
        start = date(now.year - count + 1, 1, 1)
    query = select(Activity).where(
        Activity.user_id == user.id,
        Activity.started_at >= datetime.combine(start, datetime.min.time(), timezone.utc),
        Activity.started_at < now,
    )
    if activity_type:
        query = query.where(Activity.activity_type == activity_type)
    items = db.scalars(query.order_by(Activity.started_at)).all()
    buckets = defaultdict(lambda: {
        "distance_m": 0.0,
        "duration_seconds": 0,
        "activities": 0,
        "elevation_gain_m": 0.0,
        "running_distance_m": 0.0,
        "running_duration_seconds": 0,
    })
    for item in items:
        day = item.started_at.date()
        key = (day - timedelta(days=day.weekday())).isoformat() if period == "week" else day.strftime("%Y-%m" if period == "month" else "%Y")
        buckets[key]["distance_m"] += float(item.distance_m or 0)
        buckets[key]["duration_seconds"] += item.duration_seconds
        buckets[key]["activities"] += 1
        buckets[key]["elevation_gain_m"] += float(item.elevation_gain_m or 0)
        if item.activity_type == ActivityType.run and item.distance_m:
            buckets[key]["running_distance_m"] += float(item.distance_m)
            buckets[key]["running_duration_seconds"] += item.duration_seconds
    if period == "week":
        keys = [((start + timedelta(weeks=index))).isoformat() for index in range(count)]
    elif period == "month":
        keys = []
        cursor = start
        for _ in range(count):
            keys.append(cursor.strftime("%Y-%m"))
            cursor = date(cursor.year + (cursor.month == 12), cursor.month + 1 if cursor.month < 12 else 1, 1)
    else:
        keys = [str(year) for year in range(start.year, now.year + 1)]
    return {
        "period": period,
        "data": [
            {
                "period": key,
                **buckets[key],
                "average_elapsed_pace_seconds_per_km": (
                    round(buckets[key]["running_duration_seconds"] / (buckets[key]["running_distance_m"] / 1000), 1)
                    if buckets[key]["running_distance_m"] > 0 else None
                ),
            }
            for key in keys
        ],
    }


@router.get("/strength")
def strength_trends(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(select(
        StrengthWorkout.started_at,
        ExerciseSet.repetitions,
        ExerciseSet.weight_kg,
    ).join(StrengthExercise, StrengthExercise.workout_id == StrengthWorkout.id)
      .join(ExerciseSet, ExerciseSet.exercise_id == StrengthExercise.id)
    .where(StrengthWorkout.user_id == user.id, StrengthWorkout.started_at < datetime.now(timezone.utc))
      .order_by(StrengthWorkout.started_at)).all()
    totals = defaultdict(lambda: {"volume_kg": 0.0, "sets": 0})
    for started_at, repetitions, weight in rows:
        key = started_at.strftime("%Y-%m")
        totals[key]["volume_kg"] += float(weight or 0) * repetitions
        totals[key]["sets"] += 1
    return {"data": [{"period": key, **value} for key, value in sorted(totals.items())]}