import csv
import io
import re
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Activity, User
from app.schemas.activity import ActivityResponse

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/activities")
def export_activities(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    activities = db.scalars(select(Activity).where(Activity.user_id == user.id).order_by(Activity.started_at)).all()
    if format == "json":
        return [ActivityResponse.model_validate(item).model_dump(mode="json") for item in activities]

    output = io.StringIO(newline="")
    fields = ["id", "activity_type", "title", "started_at", "duration_seconds", "distance_m", "elevation_gain_m", "calories", "average_heart_rate", "perceived_effort", "notes"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for activity in activities:
        row = {field: getattr(activity, field) for field in fields}
        for field, value in row.items():
            if isinstance(value, Enum):
                value = value.value
            elif isinstance(value, datetime):
                value = value.isoformat()
            if isinstance(value, str) and re.match(r"^[\s]*[=+@-]", value):
                value = "'" + value
            row[field] = value
        writer.writerow(row)
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=pace-activities.csv"})