from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Activity, ActivityType, User
from app.models.strength import ExerciseSet, StrengthExercise, StrengthWorkout

router = APIRouter(prefix="/records", tags=["records"])


@router.get("")
def personal_records(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    records = []
    now = datetime.now(timezone.utc)
    runs = db.scalars(select(Activity).where(
        Activity.user_id == user.id, Activity.activity_type == ActivityType.run,
        Activity.distance_m.is_not(None), Activity.started_at < now,
    )).all()
    if runs:
        longest = max(runs, key=lambda activity: activity.distance_m or 0)
        records.append({"category": "Longest run", "value": round(longest.distance_m / 1000, 2), "unit": "km", "achieved_at": longest.started_at, "source": longest.title})

    strength_rows = db.execute(select(
        StrengthWorkout.started_at, StrengthExercise.name, ExerciseSet.weight_kg,
        ExerciseSet.repetitions, StrengthWorkout.title,
    ).join(StrengthExercise, StrengthExercise.workout_id == StrengthWorkout.id)
      .join(ExerciseSet, ExerciseSet.exercise_id == StrengthExercise.id)
    .where(StrengthWorkout.user_id == user.id, StrengthWorkout.started_at < now)).all()
    if strength_rows:
        weighted = [row for row in strength_rows if row.weight_kg is not None]
        if weighted:
            heaviest = max(weighted, key=lambda row: row.weight_kg)
            records.append({"category": f"Heaviest lift · {heaviest.name}", "value": float(heaviest.weight_kg), "unit": "kg", "achieved_at": heaviest.started_at, "source": heaviest.title})
        weighted_sets = [row for row in strength_rows if row.weight_kg is not None and row.weight_kg > 0]
        if weighted_sets:
            highest_volume = max(weighted_sets, key=lambda row: float(row.weight_kg) * row.repetitions)
            records.append({"category": f"Highest set volume · {highest_volume.name}", "value": round(float(highest_volume.weight_kg) * highest_volume.repetitions, 2), "unit": "kg", "achieved_at": highest_volume.started_at, "source": highest_volume.title})
    return {"records": records}