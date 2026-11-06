from datetime import datetime, time, timedelta, timezone


def register(client, email):
    return client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Pace Runner",
        "password": "a-secure-test-password",
    })


def create_activity(client, title="Morning run"):
    return client.post("/api/v1/activities", json={
        "activity_type": "run",
        "title": title,
        "started_at": "2026-11-04T07:30:00Z",
        "duration_seconds": 1800,
        "distance_m": 5000,
        "elevation_gain_m": 250,
    })


def test_activity_crud_and_dashboard_uses_stored_data(client):
    assert register(client, "one@example.com").status_code == 201
    created = create_activity(client)
    assert created.status_code == 201
    activity_id = created.json()["id"]

    summary = client.get("/api/v1/dashboard/summary").json()
    assert summary["total_activities"] == 1
    assert summary["total_distance_m"] == 5000
    assert summary["total_duration_seconds"] == 1800
    analytics = client.get("/api/v1/analytics/overview").json()
    assert analytics["running"]["average_elapsed_pace_seconds_per_km"] == 360
    trend = client.get("/api/v1/analytics/trends?period=week").json()
    assert sum(item["distance_m"] for item in trend["data"]) == 5000
    assert sum(item["elevation_gain_m"] for item in trend["data"]) == 250
    assert sum(item["average_elapsed_pace_seconds_per_km"] or 0 for item in trend["data"]) == 360

    updated = client.patch(f"/api/v1/activities/{activity_id}", json={"title": "Tempo run"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Tempo run"
    assert client.patch(f"/api/v1/activities/{activity_id}", json={"title": None}).status_code == 422
    csv_export = client.get("/api/v1/export/activities?format=csv").text
    assert ",run,Tempo run," in csv_export
    assert client.delete(f"/api/v1/activities/{activity_id}").status_code == 204
    assert client.get("/api/v1/activities").json() == []


def test_csv_export_escapes_formula_cells_after_leading_whitespace(client):
    assert register(client, "csv@example.com").status_code == 201
    response = client.post("/api/v1/activities", json={
        "activity_type": "run", "title": "Safe title", "started_at": "2026-11-04T07:30:00Z",
        "duration_seconds": 1800, "notes": "  =HYPERLINK(\"https://example.invalid\")",
    })
    assert response.status_code == 201
    export = client.get("/api/v1/export/activities?format=csv").text
    assert "'  =HYPERLINK" in export


def test_activity_data_is_isolated_between_users(client):
    register(client, "one@example.com")
    activity_id = create_activity(client).json()["id"]
    client.post("/api/v1/auth/logout")

    register(client, "two@example.com")
    assert client.get("/api/v1/activities").json() == []
    assert client.get(f"/api/v1/activities/{activity_id}").status_code == 404


def test_validation_and_authentication_are_enforced(client):
    assert client.get("/api/v1/activities").status_code == 401
    register(client, "one@example.com")
    invalid = client.post("/api/v1/activities", json={
        "activity_type": "run",
        "title": "Bad run",
        "started_at": "2026-11-04T07:30:00Z",
        "duration_seconds": 0,
        "distance_m": -20,
    })
    assert invalid.status_code == 422
    missing_timezone = client.post("/api/v1/activities", json={
        "activity_type": "run", "title": "Local time", "started_at": "2026-11-04T07:30:00",
        "duration_seconds": 1800,
    })
    assert missing_timezone.status_code == 422
    client.post("/api/v1/auth/logout")
    logged_in = client.post("/api/v1/auth/login", json={"email": "one@example.com", "password": "a-secure-test-password"})
    assert logged_in.status_code == 200


def test_dashboard_week_starts_at_utc_midnight_and_ignores_future_activity(client):
    assert register(client, "week@example.com").status_code == 201
    now = datetime.now(timezone.utc)
    monday = now.date() - timedelta(days=now.weekday())
    monday_early = datetime.combine(monday, time.min, timezone.utc) + timedelta(minutes=1)
    assert monday_early < now
    current_week = client.post("/api/v1/activities", json={
        "activity_type": "run", "title": "Monday early run", "started_at": monday_early.isoformat(),
        "duration_seconds": 1800, "distance_m": 5000,
    })
    future = client.post("/api/v1/activities", json={
        "activity_type": "run", "title": "Future run", "started_at": (now + timedelta(days=1)).isoformat(),
        "duration_seconds": 1800, "distance_m": 10000,
    })
    assert current_week.status_code == 201
    assert future.status_code == 201
    summary = client.get("/api/v1/dashboard/summary").json()
    assert summary["total_activities"] == 1
    assert summary["week_activities"] == 1
    assert summary["week_distance_m"] == 5000


def test_calendar_uses_requested_timezone_for_local_date_boundaries(client):
    assert register(client, "calendar@example.com").status_code == 201
    created = client.post("/api/v1/activities", json={
        "activity_type": "run", "title": "Late local run", "started_at": "2026-11-02T07:30:00Z",
        "duration_seconds": 1800,
    })
    assert created.status_code == 201
    activity_id = created.json()["id"]

    local_day = client.get("/api/v1/training/calendar?start=2026-11-01&end=2026-11-01&timezone=America%2FLos_Angeles")
    assert [item["id"] for item in local_day.json()["activities"]] == [activity_id]
    utc_day = client.get("/api/v1/training/calendar?start=2026-11-01&end=2026-11-01&timezone=UTC")
    assert utc_day.json()["activities"] == []
    assert client.get("/api/v1/training/calendar?start=2026-11-01&end=2026-11-01&timezone=Invalid%2FZone").status_code == 422