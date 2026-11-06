import csv
import gzip
import io
import zipfile
from collections import Counter
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.session import get_db
from app.models import ActivitySample, ImportJob, ImportedActivitySource
from app.services.strava_import import (
    MAX_ARCHIVE_BYTES,
    StravaArchiveError,
    _parse_gpx,
    _parse_tcx,
    parse_strava_archive,
)


HEADERS = [
    "Activity ID", "Activity Date", "Activity Name", "Activity Type", "Activity Description",
    "Elapsed Time", "Distance", "Filename", "Elapsed Time", "Moving Time", "Distance",
    "Max Speed", "Average Speed", "Elevation Gain", "Average Heart Rate", "Max Heart Rate",
    "Average Cadence", "Calories", "Start Time",
]


def activity_row(activity_id, title, activity_type, filename="", date="Nov 05, 2026, 8:00:00 AM"):
    row = [""] * len(HEADERS)
    row[0] = str(activity_id)
    row[1] = date
    row[2] = title
    row[3] = activity_type
    row[4] = "Generated test activity"
    row[5] = "600"
    row[6] = "0.60"
    row[7] = filename
    row[8] = "600.0"
    row[9] = "540"
    row[10] = "600.0"
    row[11] = "2.5"
    row[12] = "1.111"
    row[13] = "5.0"
    row[14] = "140"
    row[15] = "165"
    row[16] = "80"
    row[17] = "100"
    return row


def gpx_fixture():
    return b'''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="fixture" xmlns="http://www.topografix.com/GPX/1/1" xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">
  <trk><trkseg>
    <trkpt lat="34.000000" lon="-118.000000"><ele>100</ele><time>2026-11-05T16:00:00Z</time><extensions><gpxtpx:TrackPointExtension><gpxtpx:hr>140</gpxtpx:hr><gpxtpx:cad>80</gpxtpx:cad></gpxtpx:TrackPointExtension></extensions></trkpt>
    <trkpt lat="34.000100" lon="-118.000100"><ele>101</ele><time>2026-11-05T16:00:10Z</time></trkpt>
    <trkpt lat="91" lon="0"><time>2026-11-05T16:00:20Z</time></trkpt>
  </trkseg></trk>
</gpx>'''


def tcx_fixture():
    return b'''<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"><Activities><Activity Sport="Running"><Lap StartTime="2026-11-05T16:00:00Z"><Track>
<Trackpoint><Time>2026-11-05T16:00:00Z</Time><Position><LatitudeDegrees>34.1</LatitudeDegrees><LongitudeDegrees>-118.1</LongitudeDegrees></Position><AltitudeMeters>105</AltitudeMeters><HeartRateBpm><Value>141</Value></HeartRateBpm><Cadence>81</Cadence></Trackpoint>
</Track></Lap></Activity></Activities></TrainingCenterDatabase>'''


def make_export(rows=None, include_tracks=True):
    rows = rows or [
        activity_row(12345, "Synthetic run", "Run", "activities/12345.gpx"),
        activity_row(12345, "Repeated row", "Run", "activities/12345.gpx"),
        activity_row(12346, "Synthetic weights", "Weight Training"),
        activity_row(12347, "Unsupported activity", "Paragliding"),
        activity_row(12348, "Synthetic TCX run", "Run", "activities/12348.tcx.gz"),
    ]
    csv_buffer = io.StringIO(newline="")
    writer = csv.writer(csv_buffer)
    writer.writerow(HEADERS)
    writer.writerows(rows)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("activities.csv", csv_buffer.getvalue())
        if include_tracks:
            archive.writestr("activities/12345.gpx", gpx_fixture())
            archive.writestr("activities/12348.tcx.gz", gzip.compress(tcx_fixture()))
    return buffer.getvalue()


def register(client, email="strava@example.com"):
    return client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Import Athlete",
        "password": "secure-strava-import-password",
    })


def upload(client, payload, filename="strava-export.zip", timezone_name="America/Los_Angeles"):
    return client.post(
        "/api/v1/imports/strava/upload",
        data={"timezone": timezone_name},
        files={"file": (filename, payload, "application/zip")},
    )


def test_observed_export_headers_duplicate_rows_gpx_and_tcx_are_parsed():
    parsed = parse_strava_archive(make_export(), "America/Los_Angeles")
    assert parsed.total_rows == 5
    assert parsed.duplicates_in_archive == 1
    assert len(parsed.activities) == 4
    by_id = {item.external_activity_id: item for item in parsed.activities}
    assert by_id["12345"].activity_type == "run"
    assert by_id["12345"].started_at.isoformat() == "2026-11-05T16:00:00+00:00"
    assert by_id["12345"].distance_m == 600
    assert by_id["12345"].duration_seconds == 600
    assert by_id["12345"].moving_duration_seconds == 540
    assert len(by_id["12345"].samples) == 2
    assert by_id["12345"].samples[0].heart_rate == 140
    assert by_id["12345"].samples[0].cadence == 80
    assert by_id["12346"].activity_type == "strength"
    assert by_id["12347"].activity_type == "other"
    assert by_id["12347"].status == "unsupported"
    assert by_id["12348"].source_metadata["track_format"] == "tcx"
    assert len(by_id["12348"].samples) == 1
    assert not any("Synthetic" in str(item.source_metadata) for item in parsed.activities)


def test_missing_optional_track_files_and_timezone_are_handled_explicitly():
    row = activity_row(12350, "Summary-only run", "Run")
    parsed = parse_strava_archive(make_export([row], include_tracks=False), "UTC")
    assert len(parsed.activities) == 1
    assert parsed.activities[0].samples == []
    with pytest.raises(StravaArchiveError, match="IANA timezone"):
        parse_strava_archive(make_export([row], include_tracks=False), "Not/AZone")


def test_invalid_zip_oversized_upload_and_path_traversal_are_rejected(monkeypatch):
    with pytest.raises(StravaArchiveError, match="valid ZIP"):
        parse_strava_archive(b"not a zip", "UTC")
    with monkeypatch.context() as patch:
        patch.setattr("app.services.strava_import.MAX_ARCHIVE_BYTES", 8)
        with pytest.raises(StravaArchiveError, match="250 MiB"):
            parse_strava_archive(b"x" * 9, "UTC")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../activities.csv", "bad")
    with pytest.raises(StravaArchiveError, match="unsafe member path"):
        parse_strava_archive(buffer.getvalue(), "UTC")


def test_tcx_gpx_coordinate_validation_and_malformed_xml():
    assert len(_parse_gpx(gpx_fixture())) == 2
    assert len(_parse_tcx(tcx_fixture())) == 1
    with pytest.raises(Exception):
        _parse_gpx(b"<!DOCTYPE gpx [<!ENTITY x SYSTEM 'file:///etc/passwd'>]><gpx>&x;</gpx>")


def test_upload_preview_confirm_reimport_and_sample_persistence(client):
    assert register(client).status_code == 201
    export = make_export()
    created = upload(client, export)
    assert created.status_code == 201
    job = created.json()
    assert job["total_discovered"] == 5
    assert job["ready_count"] == 3
    assert job["duplicate_count"] == 1
    assert job["unsupported_count"] == 1

    preview = client.get(f"/api/v1/imports/{job['id']}/preview").json()
    run_item = next(item for item in preview["items"] if item["external_activity_id"] == "12345")
    assert run_item["status"] == "ready"
    assert run_item["sample_count"] == 2
    unsupported = next(item for item in preview["items"] if item["external_activity_id"] == "12347")
    assert unsupported["selected"] is False

    selected_items = [
        {"id": item["id"], "selected": item["external_activity_id"] in {"12345", "12348"}}
        for item in preview["items"]
        if item["status"] in {"ready", "unsupported"}
    ]
    updated = client.patch(f"/api/v1/imports/{job['id']}/preview", json={"items": selected_items})
    assert updated.status_code == 200
    confirmed = client.post(f"/api/v1/imports/{job['id']}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["imported"] == 2
    assert confirmed.json()["failed"] == 0
    activities = client.get("/api/v1/activities").json()
    assert len(activities) == 2
    assert sum(item["distance_m"] or 0 for item in activities) == 1200
    assert client.get("/api/v1/dashboard/summary").json()["total_activities"] == 2

    session_generator = client.app.dependency_overrides[get_db]()
    session = next(session_generator)
    try:
        assert session.scalar(select(ImportJob).where(ImportJob.id == job["id"])) is not None
        assert session.scalar(select(ImportedActivitySource).where(ImportedActivitySource.user_id.is_not(None))) is not None
        assert session.scalar(select(ActivitySample).where(ActivitySample.user_id.is_not(None))) is not None
    finally:
        session_generator.close()

    repeated = upload(client, export)
    assert repeated.status_code == 201
    repeated_job = repeated.json()
    assert repeated_job["duplicate_count"] >= 3
    assert repeated_job["ready_count"] == 1


def test_import_jobs_and_preview_are_isolated_between_users(client):
    assert register(client, "first-import@example.com").status_code == 201
    job = upload(client, make_export([activity_row(222, "Private row", "Run")], include_tracks=False)).json()
    client.post("/api/v1/auth/logout")
    assert register(client, "second-import@example.com").status_code == 201
    assert client.get(f"/api/v1/imports/{job['id']}").status_code == 404
    assert client.get(f"/api/v1/imports/{job['id']}/preview").status_code == 404
    assert client.post(f"/api/v1/imports/{job['id']}/confirm").status_code == 404


def test_attached_real_export_parses_in_memory_when_available():
    sample_dir = Path(__file__).resolve().parents[2] / "strava sample 1"
    if not sample_dir.is_dir():
        pytest.skip("real Strava export folder is not available in this checkout")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sample_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(sample_dir).as_posix())
    parsed = parse_strava_archive(buffer.getvalue(), "America/Los_Angeles")
    formats = Counter(item.source_metadata.get("track_format", "none") for item in parsed.activities)
    assert parsed.total_rows == 172
    assert len(parsed.activities) == 172
    assert formats["gpx"] == 44
    assert formats["tcx"] == 1
    assert formats["fit"] == 114
    assert sum(len(item.samples) for item in parsed.activities) > 0