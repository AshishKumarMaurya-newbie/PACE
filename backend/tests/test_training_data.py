from datetime import datetime, timedelta, timezone


def register(client, email="athlete@example.com"):
    return client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Test Athlete",
        "password": "a-secure-test-password",
    })


def test_strength_health_training_records_and_export(client):
    assert register(client).status_code == 201
    workout = client.post("/api/v1/strength/workouts", json={
        "title": "Lower body",
        "started_at": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
        "duration_seconds": 3600,
        "exercises": [{
            "name": "Squat",
            "sets": [
                {"repetitions": 5, "weight_kg": 100, "rest_seconds": 120},
                {"repetitions": 8, "weight_kg": None},
            ],
        }],
    })
    assert workout.status_code == 201
    assert len(workout.json()["exercises"][0]["sets"]) == 2
    dashboard = client.get("/api/v1/dashboard/summary").json()
    assert dashboard["total_activities"] == 1
    assert dashboard["total_duration_seconds"] == 3600
    assert dashboard["week_activities"] == 1
    assert client.get("/api/v1/analytics/strength").json()["data"][0]["volume_kg"] == 500
    records = client.get("/api/v1/records").json()["records"]
    assert any(item["category"] == "Heaviest lift · Squat" for item in records)

    metric = client.post("/api/v1/health/metrics", json={
        "metric_type": "body_weight", "value": 72.4, "unit": "kg", "recorded_at": "2026-11-05T08:00:00Z",
    })
    assert metric.status_code == 201
    assert len(client.get("/api/v1/health/metrics?metric_type=body_weight").json()) == 1

    plan = client.post("/api/v1/training/plans", json={"title": "Base block", "goal": "Improve endurance"})
    assert plan.status_code == 201
    scheduled = client.post(f"/api/v1/training/plans/{plan.json()['id']}/workouts", json={
        "title": "Easy run", "activity_type": "run", "scheduled_date": "2026-11-06",
    })
    assert scheduled.status_code == 201
    calendar = client.get("/api/v1/training/calendar?start=2026-11-05&end=2026-11-07").json()
    assert len(calendar["planned_workouts"]) == 1
    assert len(calendar["strength_workouts"]) == 1
    completed = client.post(f"/api/v1/training/workouts/{scheduled.json()['id']}/complete")
    assert completed.json()["is_completed"] is True

    exported = client.get("/api/v1/export/activities?format=json")
    assert exported.status_code == 200
    assert exported.json() == []


def test_new_module_data_is_isolated(client):
    register(client, "first@example.com")
    client.post("/api/v1/health/metrics", json={
        "metric_type": "daily_steps", "value": 6000, "unit": "steps", "recorded_at": "2026-11-05T08:00:00Z",
    })
    client.post("/api/v1/auth/logout")
    register(client, "second@example.com")
    assert client.get("/api/v1/health/metrics").json() == []
    assert client.get("/api/v1/strength/workouts").json() == []
    assert client.get("/api/v1/training/plans").json() == []


def test_all_resource_families_are_scoped_to_the_current_user(client):
    register(client, "owner@example.com")
    activity = client.post("/api/v1/activities", json={
        "activity_type": "run", "title": "Owned run", "started_at": "2026-11-05T07:00:00Z",
        "duration_seconds": 1800, "distance_m": 5000,
    }).json()
    workout = client.post("/api/v1/strength/workouts", json={
        "title": "Owned workout", "started_at": "2026-11-05T08:00:00Z",
        "exercises": [{"name": "Press", "sets": [{"repetitions": 5, "weight_kg": 50}]}],
    }).json()
    client.post("/api/v1/health/metrics", json={
        "metric_type": "body_weight", "value": 70, "unit": "kg", "recorded_at": "2026-11-05T08:00:00Z",
    })
    plan = client.post("/api/v1/training/plans", json={"title": "Owned plan", "goal": "General fitness"}).json()
    planned = client.post(f"/api/v1/training/plans/{plan['id']}/workouts", json={
        "title": "Owned session", "activity_type": "run", "scheduled_date": "2026-11-06",
    }).json()
    client.post("/api/v1/auth/logout")

    assert register(client, "other@example.com").status_code == 201
    activity_path = f"/api/v1/activities/{activity['id']}"
    assert client.get(activity_path).status_code == 404
    assert client.patch(activity_path, json={"title": "Hijacked"}).status_code == 404
    assert client.delete(activity_path).status_code == 404

    workout_path = f"/api/v1/strength/workouts/{workout['id']}"
    assert client.get(workout_path).status_code == 404
    assert client.patch(workout_path, json={"title": "Hijacked"}).status_code == 404
    assert client.delete(workout_path).status_code == 404

    assert client.get("/api/v1/health/metrics").json() == []
    assert client.get("/api/v1/training/plans").json() == []
    assert client.post(f"/api/v1/training/plans/{plan['id']}/workouts", json={
        "title": "Foreign plan session", "activity_type": "run", "scheduled_date": "2026-11-07",
    }).status_code == 404
    assert client.post(f"/api/v1/training/workouts/{planned['id']}/complete").status_code == 404

    calendar = client.get("/api/v1/training/calendar?start=2026-11-01&end=2026-11-30").json()
    assert calendar == {"activities": [], "planned_workouts": [], "strength_workouts": []}
    assert client.get("/api/v1/analytics/overview").json()["activity_count"] == 0
    assert all(item["activities"] == 0 for item in client.get("/api/v1/analytics/trends?period=month").json()["data"])
    assert client.get("/api/v1/analytics/strength").json()["data"] == []
    assert client.get("/api/v1/records").json()["records"] == []
    assert client.get("/api/v1/export/activities?format=json").json() == []