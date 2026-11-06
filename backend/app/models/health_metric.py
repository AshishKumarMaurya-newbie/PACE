import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class HealthMetric(Base):
    __tablename__ = "health_metrics"
    __table_args__ = (Index("ix_health_user_type_recorded", "user_id", "metric_type", "recorded_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    metric_type: Mapped[str] = mapped_column(String(40))
    value: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    unit: Mapped[str] = mapped_column(String(16))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="health_metrics")