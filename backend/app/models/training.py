import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class TrainingPlan(Base):
    __tablename__ = "training_plans"
    __table_args__ = (Index("ix_plans_user_active", "user_id", "is_active"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    goal: Mapped[str] = mapped_column(String(80))
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="training_plans")
    planned_workouts: Mapped[list["PlannedWorkout"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class PlannedWorkout(Base):
    __tablename__ = "planned_workouts"
    __table_args__ = (Index("ix_planned_user_date", "user_id", "scheduled_date"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("training_plans.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    activity_type: Mapped[str] = mapped_column(String(24))
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan: Mapped["TrainingPlan"] = relationship(back_populates="planned_workouts")