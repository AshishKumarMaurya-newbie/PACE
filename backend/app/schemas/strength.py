import uuid
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SetInput(BaseModel):
    repetitions: int = Field(gt=0, le=1000)
    weight_kg: Decimal | None = Field(default=None, ge=0, le=2000, max_digits=8, decimal_places=2)
    rest_seconds: int | None = Field(default=None, ge=0, le=7200)


class ExerciseInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)
    sets: list[SetInput] = Field(min_length=1, max_length=100)


class WorkoutCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    started_at: datetime
    duration_seconds: int | None = Field(default=None, gt=0, le=172800)
    notes: str | None = Field(default=None, max_length=4000)
    exercises: list[ExerciseInput] = Field(min_length=1, max_length=50)

    @field_validator("started_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("started_at must include a timezone")
        return value.astimezone(timezone.utc)


class WorkoutUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    started_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, gt=0, le=172800)
    notes: str | None = Field(default=None, max_length=4000)
    exercises: list[ExerciseInput] | None = Field(default=None, min_length=1, max_length=50)

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
        if any(field in self.model_fields_set and getattr(self, field) is None for field in {"title", "started_at"}):
            raise ValueError("Required workout fields cannot be null")
        return self


class SetResponse(BaseModel):
    id: uuid.UUID
    set_number: int
    repetitions: int
    weight_kg: Decimal | None
    rest_seconds: int | None
    model_config = ConfigDict(from_attributes=True)


class ExerciseResponse(BaseModel):
    id: uuid.UUID
    name: str
    position: int
    notes: str | None
    sets: list[SetResponse]
    model_config = ConfigDict(from_attributes=True)


class WorkoutResponse(BaseModel):
    id: uuid.UUID
    title: str
    started_at: datetime
    duration_seconds: int | None
    notes: str | None
    exercises: list[ExerciseResponse]
    model_config = ConfigDict(from_attributes=True)

    @field_validator("started_at", mode="before")
    @classmethod
    def normalize_database_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)