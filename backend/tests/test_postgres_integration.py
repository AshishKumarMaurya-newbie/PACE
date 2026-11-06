import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url

from app.db.session import get_db
from app.main import app as fastapi_app

POSTGRES_URL = os.getenv("PACE_TEST_POSTGRES_URL")


@pytest.mark.postgres
@pytest.mark.skipif(not POSTGRES_URL, reason="set PACE_TEST_POSTGRES_URL to a dedicated PostgreSQL test database")
def test_postgres_migration_persistence_uuid_and_cascade():
    schema = f"pace_test_{uuid.uuid4().hex}"
    admin_engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
    test_engine = None
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))

        environment = os.environ.copy()
        environment["DATABASE_URL"] = POSTGRES_URL
        environment["PGOPTIONS"] = f"-c search_path={schema}"
        backend_root = Path(__file__).resolve().parents[1]
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=backend_root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )

        test_engine = create_engine(POSTGRES_URL, pool_pre_ping=True)

        @event.listens_for(test_engine, "connect")
        def set_isolated_schema(connection, _record):
            cursor = connection.cursor()
            cursor.execute(f'SET search_path TO "{schema}"')
            cursor.close()

        testing_session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

        def override_get_db():
            with testing_session() as session:
                yield session

        fastapi_app.dependency_overrides[get_db] = override_get_db
        with TestClient(fastapi_app) as client:
            assert client.get("/health").status_code == 200
            registered = client.post("/api/v1/auth/register", json={
                "email": "postgres-integration@example.com",
                "full_name": "PostgreSQL Athlete",
                "password": "postgres-integration-password",
            })
            assert registered.status_code == 201

            activity = client.post("/api/v1/activities", json={
                "activity_type": "run", "title": "PostgreSQL run",
                "started_at": "2026-11-04T07:00:00Z", "duration_seconds": 1800,
                "distance_m": 5000,
            })
            assert activity.status_code == 201
            assert uuid.UUID(activity.json()["id"])

            workout = client.post("/api/v1/strength/workouts", json={
                "title": "PostgreSQL strength", "started_at": "2026-11-04T08:00:00Z",
                "exercises": [{"name": "Squat", "sets": [{"repetitions": 5, "weight_kg": 80}]}],
            })
            assert workout.status_code == 201
            assert workout.json()["exercises"][0]["sets"][0]["weight_kg"] == "80.00"

            health = client.post("/api/v1/health/metrics", json={
                "metric_type": "body_weight", "value": 70.5, "unit": "kg",
                "recorded_at": "2026-11-04T08:00:00Z",
            })
            assert health.status_code == 201

            plan = client.post("/api/v1/training/plans", json={"title": "Postgres plan", "goal": "General fitness"})
            assert plan.status_code == 201
            planned = client.post(f"/api/v1/training/plans/{plan.json()['id']}/workouts", json={
                "title": "Postgres planned run", "activity_type": "run", "scheduled_date": "2026-11-06",
            })
            assert planned.status_code == 201
            assert client.get("/api/v1/training/plans").json()[0]["id"] == plan.json()["id"]

        with test_engine.begin() as connection:
            version = connection.scalar(text("SELECT version_num FROM alembic_version"))
            assert version == "d697d8466ac6"
            connection.execute(text("DELETE FROM training_plans WHERE id = :id"), {"id": uuid.UUID(plan.json()["id"])})
            remaining_planned = connection.scalar(text("SELECT count(*) FROM planned_workouts"))
            assert remaining_planned == 0
            assert connection.scalar(text("SELECT count(*) FROM activities")) == 1
    finally:
        fastapi_app.dependency_overrides.clear()
        if test_engine is not None:
            test_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()