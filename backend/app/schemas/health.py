import uuid
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthMetricCreate(BaseModel):
    metric_type: str = Field(min_length=1, max_length=40, pattern=r"^[a-z][a-z0-9_]*$")
    value: Decimal = Field(ge=0, le=1_000_000, max_digits=10, decimal_places=3)
    unit: str = Field(min_length=1, max_length=16)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must include a timezone")
        return value.astimezone(timezone.utc)


class HealthMetricResponse(HealthMetricCreate):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

    @field_validator("recorded_at", mode="before")
    @classmethod
    def normalize_database_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)