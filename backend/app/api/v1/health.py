from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import HealthMetric, User
from app.schemas.health import HealthMetricCreate, HealthMetricResponse

router = APIRouter(prefix="/health/metrics", tags=["health"])


@router.get("", response_model=list[HealthMetricResponse])
def list_metrics(
    metric_type: str | None = Query(default=None, max_length=40),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(HealthMetric).where(HealthMetric.user_id == user.id)
    if metric_type:
        query = query.where(HealthMetric.metric_type == metric_type)
    return db.scalars(query.order_by(HealthMetric.recorded_at.desc()).limit(500)).all()


@router.post("", response_model=HealthMetricResponse, status_code=status.HTTP_201_CREATED)
def create_metric(payload: HealthMetricCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    metric = HealthMetric(**payload.model_dump(), user_id=user.id)
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric