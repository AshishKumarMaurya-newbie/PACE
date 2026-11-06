import uuid
from datetime import datetime, timezone
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Activity, ActivitySample, ActivityType, ImportItem, ImportJob, ImportSample, ImportedActivitySource, User
from app.schemas.imports import (
    ImportConfirmationResponse,
    ImportItemResponse,
    ImportJobResponse,
    ImportPreviewResponse,
    ImportSelectionUpdate,
)
from app.services.strava_import import MAX_ARCHIVE_BYTES, ParsedActivity, StravaArchiveError, activity_fingerprint, parse_strava_archive

router = APIRouter(prefix="/imports", tags=["imports"])


def _upload_name(filename: str | None) -> str:
    basename = PurePosixPath((filename or "strava-export.zip").replace("\\", "/")).name
    return basename[:255] or "strava-export.zip"


async def _read_limited(upload: UploadFile) -> bytes:
    content = bytearray()
    while chunk := await upload.read(1024 * 1024):
        content.extend(chunk)
        if len(content) > MAX_ARCHIVE_BYTES:
            raise HTTPException(status_code=413, detail="Strava export exceeds the 250 MiB upload limit")
    return bytes(content)


def _find_existing_duplicates(items: list[ParsedActivity], user_id: uuid.UUID, db: Session) -> set[str]:
    external_ids = {item.external_activity_id for item in items if item.external_activity_id}
    fingerprints = {item.fallback_fingerprint for item in items}
    existing_keys: set[str] = set()
    if external_ids:
        existing_keys.update(db.scalars(select(ImportedActivitySource.external_activity_id).where(
            ImportedActivitySource.user_id == user_id,
            ImportedActivitySource.provider == "strava",
            ImportedActivitySource.external_activity_id.in_(external_ids),
        )).all())
    if fingerprints:
        existing_keys.update(db.scalars(select(ImportedActivitySource.fallback_fingerprint).where(
            ImportedActivitySource.user_id == user_id,
            ImportedActivitySource.provider == "strava",
            ImportedActivitySource.fallback_fingerprint.in_(fingerprints),
        )).all())

    start_dates = {item.started_at for item in items if item.started_at is not None}
    activity_types = {ActivityType(item.activity_type) for item in items if item.activity_type}
    if start_dates and activity_types:
        for chunk_start in range(0, len(start_dates), 400):
            dates = list(start_dates)[chunk_start : chunk_start + 400]
            existing_activities = db.scalars(select(Activity).where(
                Activity.user_id == user_id,
                Activity.started_at.in_(dates),
                Activity.activity_type.in_(activity_types),
            )).all()
            for activity in existing_activities:
                existing_keys.add(activity_fingerprint(
                    activity.activity_type.value,
                    activity.started_at,
                    activity.duration_seconds,
                    activity.distance_m,
                ))
    return {str(key) for key in existing_keys if key}


def _item_response(item: ImportItem) -> ImportItemResponse:
    return ImportItemResponse.model_validate({
        **{field: getattr(item, field) for field in ImportItemResponse.model_fields if field != "sample_count"},
        "sample_count": len(item.samples),
    })


def _owned_job(job_id: uuid.UUID, user: User, db: Session) -> ImportJob:
    job = db.scalar(select(ImportJob).where(ImportJob.id == job_id, ImportJob.user_id == user.id))
    if job is None:
        raise HTTPException(status_code=404, detail="Import not found")
    return job


@router.post("/strava/upload", response_model=ImportJobResponse, status_code=status.HTTP_201_CREATED)
async def upload_strava_export(
    file: UploadFile = File(...),
    timezone_name: str = Form(..., alias="timezone"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    filename = _upload_name(file.filename)
    archive_bytes = await _read_limited(file)
    if not filename.casefold().endswith(".zip"):
        raise HTTPException(status_code=415, detail="Upload a Strava ZIP export")
    try:
        parsed = parse_strava_archive(archive_bytes, timezone_name)
    except StravaArchiveError as error:
        job = ImportJob(
            user_id=user.id,
            provider="strava",
            upload_filename=filename,
            upload_size_bytes=len(archive_bytes),
            status="failed",
            error_details=[str(error)[:500]],
            completed_at=datetime.now(timezone.utc),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        raise HTTPException(status_code=422, detail=str(error)) from None

    existing = _find_existing_duplicates(parsed.activities, user.id, db)
    job = ImportJob(
        user_id=user.id,
        provider="strava",
        upload_filename=filename,
        upload_size_bytes=len(archive_bytes),
        status="preview_ready",
        total_discovered=parsed.total_rows,
        duplicate_count=parsed.duplicates_in_archive,
        error_details=parsed.errors or None,
    )
    for parsed_item in parsed.activities:
        duplicate_key = parsed_item.external_activity_id or parsed_item.fallback_fingerprint
        if duplicate_key in existing or parsed_item.fallback_fingerprint in existing:
            parsed_item.status = "duplicate"
            parsed_item.selected = False
            parsed_item.source_metadata["duplicate_match"] = "strava_id" if parsed_item.external_activity_id in existing else "fingerprint"
        item = ImportItem(
            user_id=user.id,
            item_index=parsed_item.item_index,
            source_key=parsed_item.source_key,
            external_activity_id=parsed_item.external_activity_id,
            fallback_fingerprint=parsed_item.fallback_fingerprint,
            status=parsed_item.status,
            selected=parsed_item.selected,
            title=parsed_item.title,
            activity_type=parsed_item.activity_type,
            source_activity_type=parsed_item.source_activity_type,
            started_at=parsed_item.started_at,
            duration_seconds=parsed_item.duration_seconds,
            moving_duration_seconds=parsed_item.moving_duration_seconds,
            distance_m=parsed_item.distance_m,
            elevation_gain_m=parsed_item.elevation_gain_m,
            average_speed_mps=parsed_item.average_speed_mps,
            max_speed_mps=parsed_item.max_speed_mps,
            average_heart_rate=parsed_item.average_heart_rate,
            max_heart_rate=parsed_item.max_heart_rate,
            average_cadence=parsed_item.average_cadence,
            calories=parsed_item.calories,
            description=parsed_item.description,
            source_metadata=parsed_item.source_metadata,
            error_message=parsed_item.error_message,
        )
        item.samples = [ImportSample(
            user_id=user.id,
            sample_index=sample.sample_index,
            recorded_at=sample.recorded_at,
            latitude=sample.latitude,
            longitude=sample.longitude,
            elevation_m=sample.elevation_m,
            heart_rate=sample.heart_rate,
            cadence=sample.cadence,
        ) for sample in parsed_item.samples]
        job.items.append(item)

    job.ready_count = sum(item.status == "ready" for item in job.items)
    job.duplicate_count += sum(item.status == "duplicate" for item in job.items)
    job.unsupported_count = sum(item.status == "unsupported" for item in job.items)
    job.invalid_count = sum(item.status == "invalid" for item in job.items)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[ImportJobResponse])
def list_imports(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.scalars(select(ImportJob).where(ImportJob.user_id == user.id).order_by(ImportJob.created_at.desc()).offset(offset).limit(limit)).all()


@router.get("/{job_id}", response_model=ImportJobResponse)
def read_import(job_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _owned_job(job_id, user, db)


@router.get("/{job_id}/preview", response_model=ImportPreviewResponse)
def preview_import(
    job_id: uuid.UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = _owned_job(job_id, user, db)
    query = select(ImportItem).where(ImportItem.job_id == job.id, ImportItem.user_id == user.id).options(
        selectinload(ImportItem.samples)
    ).order_by(ImportItem.item_index).offset(offset).limit(limit)
    items = db.scalars(query).all()
    return ImportPreviewResponse(job=job, items=[_item_response(item) for item in items], offset=offset, limit=limit)


@router.patch("/{job_id}/preview", response_model=ImportJobResponse)
def update_preview_selection(
    job_id: uuid.UUID,
    payload: ImportSelectionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = _owned_job(job_id, user, db)
    if job.status != "preview_ready":
        raise HTTPException(status_code=409, detail="This import is no longer editable")
    selections = {entry.id: entry.selected for entry in payload.items}
    rows = db.scalars(select(ImportItem).where(
        ImportItem.job_id == job.id,
        ImportItem.user_id == user.id,
        ImportItem.id.in_(selections),
    )).all()
    if len(rows) != len(selections):
        raise HTTPException(status_code=404, detail="One or more preview activities were not found")
    for item in rows:
        selected = selections[item.id]
        if selected and item.status not in {"ready", "unsupported"}:
            raise HTTPException(status_code=422, detail="Duplicates and invalid activities cannot be selected")
        item.selected = selected
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/confirm", response_model=ImportConfirmationResponse)
def confirm_import(job_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = _owned_job(job_id, user, db)
    if job.status not in {"preview_ready", "partial"}:
        raise HTTPException(status_code=409, detail="This import cannot be confirmed in its current state")
    job.status = "processing"
    db.flush()
    items = db.scalars(select(ImportItem).where(
        ImportItem.job_id == job.id,
        ImportItem.user_id == user.id,
        ImportItem.selected.is_(True),
        ImportItem.status.in_(["ready", "unsupported", "failed"]),
    ).options(selectinload(ImportItem.samples)).order_by(ImportItem.item_index)).all()
    for item in items:
        if not item.activity_type or not item.started_at or not item.duration_seconds:
            item.status = "failed"
            item.error_message = "Required activity fields are missing"
            continue
        try:
            with db.begin_nested():
                activity = Activity(
                    user_id=user.id,
                    activity_type=ActivityType(item.activity_type),
                    title=item.title,
                    description=item.description,
                    started_at=item.started_at,
                    duration_seconds=item.duration_seconds,
                    moving_duration_seconds=item.moving_duration_seconds,
                    distance_m=item.distance_m,
                    elevation_gain_m=item.elevation_gain_m,
                    average_speed_mps=item.average_speed_mps,
                    max_speed_mps=item.max_speed_mps,
                    calories=item.calories,
                    average_heart_rate=item.average_heart_rate,
                    max_heart_rate=item.max_heart_rate,
                    average_cadence=item.average_cadence,
                )
                db.add(activity)
                db.flush()
                db.add(ImportedActivitySource(
                    user_id=user.id,
                    activity_id=activity.id,
                    import_job_id=job.id,
                    provider="strava",
                    external_activity_id=item.external_activity_id,
                    fallback_fingerprint=item.fallback_fingerprint if not item.external_activity_id else None,
                    source_activity_type=item.source_activity_type,
                    source_metadata=item.source_metadata,
                ))
                db.add_all([ActivitySample(
                    user_id=user.id,
                    activity_id=activity.id,
                    sample_index=sample.sample_index,
                    recorded_at=sample.recorded_at,
                    latitude=sample.latitude,
                    longitude=sample.longitude,
                    elevation_m=sample.elevation_m,
                    heart_rate=sample.heart_rate,
                    cadence=sample.cadence,
                ) for sample in item.samples])
                db.flush()
                item.status = "imported"
                item.error_message = None
        except IntegrityError:
            item.status = "duplicate"
            item.selected = False
        except (SQLAlchemyError, ValueError) as error:
            item.status = "failed"
            item.error_message = str(error)[:500]

    db.flush()
    statuses = db.execute(select(ImportItem.status, __import__("sqlalchemy").func.count(ImportItem.id)).where(
        ImportItem.job_id == job.id,
        ImportItem.user_id == user.id,
    ).group_by(ImportItem.status)).all()
    counts = dict(statuses)
    job.imported_count = counts.get("imported", 0)
    job.failed_count = counts.get("failed", 0)
    job.duplicate_count = max(job.duplicate_count, counts.get("duplicate", 0))
    job.status = "partial" if job.failed_count and job.imported_count else "failed" if job.failed_count else "completed"
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return ImportConfirmationResponse(job=job, imported=job.imported_count, duplicates=job.duplicate_count, failed=job.failed_count)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_import(job_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = _owned_job(job_id, user, db)
    if job.imported_count:
        raise HTTPException(status_code=409, detail="Imports with committed activities are retained as history")
    db.delete(job)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)