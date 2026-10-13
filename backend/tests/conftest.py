"""Pytest fixtures for Sherlog backend testing with isolated database."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.db.models import Base, IncidentModel
from backend.app.db.session import get_db
from backend.app.storage.memory import incident_repo

# Isolated in-memory database for unit tests so development/production PostgreSQL is never touched
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Dependency override providing an isolated test database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_and_teardown_test_db():
    """Create fresh tables before each test and drop them after, preventing data leakage."""
    Base.metadata.create_all(bind=test_engine)
    incident_repo.clear()
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=test_engine)
    incident_repo.clear()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def db_session_factory():
    """Session factory for the isolated test database."""
    return TestingSessionLocal


@pytest.fixture
def db_session():
    """Direct session fixture for tests needing direct DB access."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """FastAPI TestClient instance with isolated database."""
    with TestClient(app) as test_client:
        yield test_client
