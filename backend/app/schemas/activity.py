import uuid
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.activity import ActivityType


class ActivityCreate(BaseModel):
    activity_type: ActivityType
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    started_at: datetime
    duration_seconds: int = Field(gt=0, le=172800)
    distance_m: Decimal | None = Field(default=None, gt=0, le=2_000_000, max_digits=12, decimal_places=2)
    elevation_gain_m: Decimal | None = Field(default=None, ge=0, le=100_000, max_digits=10, decimal_places=2)
    moving_duration_seconds: int | None = Field(default=None, gt=0, le=172800)
    average_speed_mps: Decimal | None = Field(default=None, ge=0, le=200, max_digits=9, decimal_places=3)
    max_speed_mps: Decimal | None = Field(default=None, ge=0, le=300, max_digits=9, decimal_places=3)
    calories: int | None = Field(default=None, ge=0, le=100_000)
    average_heart_rate: int | None = Field(default=None, ge=30, le=250)
    max_heart_rate: int | None = Field(default=None, ge=30, le=250)
    average_cadence: Decimal | None = Field(default=None, ge=0, le=1000, max_digits=8, decimal_places=2)
    perceived_effort: int | None = Field(default=None, ge=1, le=10)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("started_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("started_at must include a timezone")
        return value.astimezone(timezone.utc)


class ActivityUpdate(BaseModel):
    activity_type: ActivityType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    started_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, gt=0, le=172800)
    distance_m: Decimal | None = Field(default=None, gt=0, le=2_000_000, max_digits=12, decimal_places=2)
    elevation_gain_m: Decimal | None = Field(default=None, ge=0, le=100_000, max_digits=10, decimal_places=2)
    moving_duration_seconds: int | None = Field(default=None, gt=0, le=172800)
    average_speed_mps: Decimal | None = Field(default=None, ge=0, le=200, max_digits=9, decimal_places=3)
    max_speed_mps: Decimal | None = Field(default=None, ge=0, le=300, max_digits=9, decimal_places=3)
    calories: int | None = Field(default=None, ge=0, le=100_000)
    average_heart_rate: int | None = Field(default=None, ge=30, le=250)
    max_heart_rate: int | None = Field(default=None, ge=30, le=250)
    average_cadence: Decimal | None = Field(default=None, ge=0, le=1000, max_digits=8, decimal_places=2)
    perceived_effort: int | None = Field(default=None, ge=1, le=10)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("started_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("started_at must include a timezone")
            return value.astimezone(timezone.utc)
        return value

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        required_fields = {"activity_type", "title", "started_at", "duration_seconds"}
        if any(field in self.model_fields_set and getattr(self, field) is None for field in required_fields):
            raise ValueError("Required activity fields cannot be null")
        return self


class ActivityResponse(BaseModel):
    id: uuid.UUID
    activity_type: ActivityType
    title: str
    description: str | None
    started_at: datetime
    duration_seconds: int
    distance_m: Decimal | None
    elevation_gain_m: Decimal | None
    moving_duration_seconds: int | None
    average_speed_mps: Decimal | None
    max_speed_mps: Decimal | None
    calories: int | None
    average_heart_rate: int | None
    max_heart_rate: int | None
    average_cadence: Decimal | None
    perceived_effort: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("started_at", "created_at", "updated_at", mode="before")
    @classmethod
    def normalize_database_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)