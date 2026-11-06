import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class ImportJob(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (Index("ix_import_jobs_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(24), default="strava")
    upload_filename: Mapped[str] = mapped_column(String(255))
    upload_size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="processing")
    total_discovered: Mapped[int] = mapped_column(Integer, default=0)
    ready_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    unsupported_count: Mapped[int] = mapped_column(Integer, default=0)
    invalid_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    error_details: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["ImportItem"]] = relationship(back_populates="job", cascade="all, delete-orphan", order_by="ImportItem.item_index")


class ImportItem(Base):
    __tablename__ = "import_items"
    __table_args__ = (
        UniqueConstraint("job_id", "source_key", name="uq_import_items_job_source_key"),
        Index("ix_import_items_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("import_jobs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_index: Mapped[int] = mapped_column(Integer)
    source_key: Mapped[str] = mapped_column(String(100))
    external_activity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fallback_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24), default="ready")
    selected: Mapped[bool] = mapped_column(default=True)
    title: Mapped[str] = mapped_column(String(160))
    activity_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_activity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    moving_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_m: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    elevation_gain_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    average_speed_mps: Mapped[Decimal | None] = mapped_column(Numeric(9, 3), nullable=True)
    max_speed_mps: Mapped[Decimal | None] = mapped_column(Numeric(9, 3), nullable=True)
    average_heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_cadence: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped["ImportJob"] = relationship(back_populates="items")
    samples: Mapped[list["ImportSample"]] = relationship(back_populates="item", cascade="all, delete-orphan", order_by="ImportSample.sample_index")


class ImportSample(Base):
    __tablename__ = "import_samples"
    __table_args__ = (
        UniqueConstraint("import_item_id", "sample_index", name="uq_import_samples_item_index"),
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_import_samples_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_import_samples_longitude"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("import_items.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    sample_index: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    elevation_m: Mapped[Decimal | None] = mapped_column(Numeric(9, 2), nullable=True)
    heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cadence: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    item: Mapped["ImportItem"] = relationship(back_populates="samples")


class ImportedActivitySource(Base):
    __tablename__ = "imported_activity_sources"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", "external_activity_id", name="uq_import_source_user_provider_external"),
        UniqueConstraint("user_id", "provider", "fallback_fingerprint", name="uq_import_source_user_provider_fingerprint"),
        CheckConstraint("external_activity_id IS NOT NULL OR fallback_fingerprint IS NOT NULL", name="ck_import_source_has_identity"),
        Index("ix_import_sources_user_activity", "user_id", "activity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True)
    provider: Mapped[str] = mapped_column(String(24))
    external_activity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fallback_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_activity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    activity: Mapped["Activity"] = relationship(back_populates="imported_sources")


class ActivitySample(Base):
    __tablename__ = "activity_samples"
    __table_args__ = (
        UniqueConstraint("activity_id", "sample_index", name="uq_activity_samples_activity_index"),
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_activity_samples_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_activity_samples_longitude"),
        Index("ix_activity_samples_user_recorded", "user_id", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    sample_index: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    elevation_m: Mapped[Decimal | None] = mapped_column(Numeric(9, 2), nullable=True)
    heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cadence: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    activity: Mapped["Activity"] = relationship(back_populates="samples")