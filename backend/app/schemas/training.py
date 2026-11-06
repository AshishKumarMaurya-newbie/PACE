import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class PlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    goal: str = Field(min_length=1, max_length=80)
    target_date: date | None = None
    notes: str | None = Field(default=None, max_length=4000)


class PlanResponse(PlanCreate):
    id: uuid.UUID
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class PlannedWorkoutCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    activity_type: str = Field(min_length=1, max_length=24)
    scheduled_date: date
    notes: str | None = Field(default=None, max_length=2000)


class PlannedWorkoutResponse(PlannedWorkoutCreate):
    id: uuid.UUID
    plan_id: uuid.UUID
    is_completed: bool
    model_config = ConfigDict(from_attributes=True)