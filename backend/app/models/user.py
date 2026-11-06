import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    activities: Mapped[list["Activity"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    strength_workouts: Mapped[list["StrengthWorkout"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    health_metrics: Mapped[list["HealthMetric"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    training_plans: Mapped[list["TrainingPlan"]] = relationship(back_populates="user", cascade="all, delete-orphan")