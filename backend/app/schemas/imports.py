import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ImportJobResponse(BaseModel):
    id: uuid.UUID
    provider: str
    upload_filename: str
    upload_size_bytes: int
    status: str
    total_discovered: int
    ready_count: int
    duplicate_count: int
    unsupported_count: int
    invalid_count: int
    imported_count: int
    failed_count: int
    error_details: list | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ImportItemResponse(BaseModel):
    id: uuid.UUID
    item_index: int
    external_activity_id: str | None
    status: str
    selected: bool
    title: str
    activity_type: str | None
    source_activity_type: str | None
    started_at: datetime | None
    duration_seconds: int | None
    moving_duration_seconds: int | None
    distance_m: Decimal | None
    elevation_gain_m: Decimal | None
    average_speed_mps: Decimal | None
    max_speed_mps: Decimal | None
    average_heart_rate: int | None
    max_heart_rate: int | None
    average_cadence: Decimal | None
    calories: int | None
    description: str | None
    sample_count: int
    source_metadata: dict
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class ImportPreviewResponse(BaseModel):
    job: ImportJobResponse
    items: list[ImportItemResponse]
    offset: int
    limit: int


class ImportItemSelection(BaseModel):
    id: uuid.UUID
    selected: bool


class ImportSelectionUpdate(BaseModel):
    items: list[ImportItemSelection] = Field(min_length=1, max_length=500)


class ImportConfirmationResponse(BaseModel):
    job: ImportJobResponse
    imported: int
    duplicates: int
    failed: int