import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class StrengthWorkout(Base):
    __tablename__ = "strength_workouts"
    __table_args__ = (Index("ix_strength_user_started", "user_id", "started_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="strength_workouts")
    exercises: Mapped[list["StrengthExercise"]] = relationship(back_populates="workout", cascade="all, delete-orphan", order_by="StrengthExercise.position")


class StrengthExercise(Base):
    __tablename__ = "strength_exercises"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("strength_workouts.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    position: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    workout: Mapped["StrengthWorkout"] = relationship(back_populates="exercises")
    sets: Mapped[list["ExerciseSet"]] = relationship(back_populates="exercise", cascade="all, delete-orphan", order_by="ExerciseSet.set_number")


class ExerciseSet(Base):
    __tablename__ = "exercise_sets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("strength_exercises.id", ondelete="CASCADE"), index=True)
    set_number: Mapped[int] = mapped_column(Integer)
    repetitions: Mapped[int] = mapped_column(Integer)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    exercise: Mapped["StrengthExercise"] = relationship(back_populates="sets")