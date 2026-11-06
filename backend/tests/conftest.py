import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-only-jwt-secret-not-for-deployment"
os.environ["ALLOW_REGISTRATION"] = "true"

from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def client():
    Base.metadata.create_all(engine)

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)