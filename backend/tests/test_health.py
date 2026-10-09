"""Tests for backend health check endpoints."""

from fastapi.testclient import TestClient


def test_health_check_root(client: TestClient):
    """GET /health should return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "environment" in data


def test_health_check_api_prefix(client: TestClient):
    """GET /api/health should also return 200 with status ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
