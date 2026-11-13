"""
Test environment and shared fixtures.

The environment variables are set before any app module is imported, so
importing app.main never needs a real database or a real secret. API tests
override get_db with an in-memory SQLite session; the real models in
ml_artifacts/ are loaded by the app's startup, so scores are the real thing.
"""

import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-only-secret-" + "x" * 40
os.environ["ENVIRONMENT"] = "development"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

import pytest  # noqa: E402  (must come after the environment is set)
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_PASSWORD = "correct horse battery"


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared in-memory database for the whole test
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:  # `with` runs startup, which loads the models
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sign_in(client):
    """Returns a function that registers + logs in a user and gives back auth headers."""

    def _sign_in(email="a@example.com"):
        registered = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": TEST_PASSWORD,
                "consent_accepted": True,
                "consent_version": get_settings().consent_version,
            },
        )
        assert registered.status_code == 201, registered.text
        login = client.post("/auth/login", json={"email": email, "password": TEST_PASSWORD})
        assert login.status_code == 200, login.text
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    return _sign_in
