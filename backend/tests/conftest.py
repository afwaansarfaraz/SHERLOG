"""Pytest fixtures for Sherlog backend testing."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.storage.memory import incident_repo


@pytest.fixture(autouse=True)
def reset_incident_store():
    """Reset the in-memory incident repository before each test."""
    incident_repo.clear()
    yield
    incident_repo.clear()


@pytest.fixture
def client():
    """FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client
