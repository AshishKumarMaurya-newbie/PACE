import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import ExerciseSet, StrengthExercise, StrengthWorkout, User
from app.schemas.strength import WorkoutCreate, WorkoutResponse, WorkoutUpdate

router = APIRouter(prefix="/strength/workouts", tags=["strength"])


def get_workout(workout_id: uuid.UUID, user: User, db: Session) -> StrengthWorkout:
    query = select(StrengthWorkout).where(StrengthWorkout.id == workout_id, StrengthWorkout.user_id == user.id).options(
        selectinload(StrengthWorkout.exercises).selectinload(StrengthExercise.sets)
    )
    workout = db.scalar(query)
    if workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout


def add_exercises(workout: StrengthWorkout, exercises) -> None:
    for position, exercise_data in enumerate(exercises):
        exercise = StrengthExercise(name=exercise_data.name.strip(), notes=exercise_data.notes, position=position)
        exercise.sets = [ExerciseSet(set_number=index, **set_data.model_dump()) for index, set_data in enumerate(exercise_data.sets, start=1)]
        workout.exercises.append(exercise)


@router.get("", response_model=list[WorkoutResponse])
def list_workouts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(StrengthWorkout).where(StrengthWorkout.user_id == user.id).options(
        selectinload(StrengthWorkout.exercises).selectinload(StrengthExercise.sets)
    ).order_by(StrengthWorkout.started_at.desc())
    return db.scalars(query).all()


@router.post("", response_model=WorkoutResponse, status_code=status.HTTP_201_CREATED)
def create_workout(payload: WorkoutCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    workout = StrengthWorkout(
        user_id=user.id,
        title=payload.title.strip(),
        started_at=payload.started_at,
        duration_seconds=payload.duration_seconds,
        notes=payload.notes,
    )
    add_exercises(workout, payload.exercises)
    db.add(workout)
    db.commit()
    return get_workout(workout.id, user, db)


@router.get("/{workout_id}", response_model=WorkoutResponse)
def read_workout(workout_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_workout(workout_id, user, db)


@router.patch("/{workout_id}", response_model=WorkoutResponse)
def update_workout(workout_id: uuid.UUID, payload: WorkoutUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    workout = get_workout(workout_id, user, db)
    values = payload.model_dump(exclude_unset=True, exclude={"exercises"})
    for field, value in values.items():
        setattr(workout, field, value)
    if payload.exercises is not None:
        workout.exercises.clear()
        add_exercises(workout, payload.exercises)
    db.commit()
    return get_workout(workout_id, user, db)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    workout = get_workout(workout_id, user, db)
    db.delete(workout)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)