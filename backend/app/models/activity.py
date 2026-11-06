import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class ActivityType(str, Enum):
    run = "run"
    walk = "walk"
    ride = "ride"
    hike = "hike"
    swim = "swim"
    strength = "strength"
    yoga = "yoga"
    sport = "sport"
    other = "other"


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (Index("ix_activities_user_started", "user_id", "started_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    activity_type: Mapped[ActivityType] = mapped_column(SqlEnum(ActivityType, native_enum=False, length=16))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    distance_m: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    elevation_gain_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    moving_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_speed_mps: Mapped[Decimal | None] = mapped_column(Numeric(9, 3), nullable=True)
    max_speed_mps: Mapped[Decimal | None] = mapped_column(Numeric(9, 3), nullable=True)
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_cadence: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    perceived_effort: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="activities")
    samples: Mapped[list["ActivitySample"]] = relationship(back_populates="activity", cascade="all, delete-orphan", order_by="ActivitySample.sample_index")
    imported_sources: Mapped[list["ImportedActivitySource"]] = relationship(back_populates="activity", cascade="all, delete-orphan")