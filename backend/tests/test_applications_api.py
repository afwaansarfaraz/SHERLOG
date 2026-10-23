"""Tests for Applications Onboarding & Registration API endpoints."""

from fastapi.testclient import TestClient
import pytest

from backend.app.config import settings
from backend.app.main import app
from backend.app.api.applications import require_probe_authentication, seed_default_applications

client = TestClient(app)
TEST_API_KEY = "test-secret-probe-key"
AUTH_HEADERS = {"Authorization": f"Bearer {TEST_API_KEY}"}


@pytest.fixture(autouse=True)
def ensure_default_applications(db_session, monkeypatch):
    """Ensure default demo applications are seeded in the isolated test database and API_KEY is set."""
    monkeypatch.setattr(settings, "API_KEY", TEST_API_KEY)
    seed_default_applications(db_session)


def test_list_applications_returns_apps():
    """Test GET /api/applications returns seeded applications."""
    response = client.get("/api/applications")
    assert response.status_code == 200
    apps = response.json()
    assert isinstance(apps, list)
    assert len(apps) >= 1
    # Verify required keys in response
    first = apps[0]
    assert "id" in first
    assert "name" in first
    assert "service_name" in first
    assert "integration_type" in first
    assert "status" in first


def test_create_and_delete_application():
    """Test POST /api/applications creates an app, and DELETE removes it."""
    payload = {
        "name": "Inventory Processor",
        "service_name": "inventory-proc",
        "environment": "staging",
        "integration_type": "opentelemetry",
        "endpoint_url": "http://127.0.0.1:8000/inventory/health",
        "telemetry_config": {
            "metrics_interval": "15s"
        }
    }
    
    # 1. Create
    create_res = client.post("/api/applications", json=payload)
    assert create_res.status_code == 201
    app_data = create_res.json()
    app_id = app_data["id"]
    assert app_data["name"] == "Inventory Processor"
    assert app_data["service_name"] == "inventory-proc"
    assert app_data["environment"] == "staging"
    assert "staging" in app_id
    assert app_data["integration_type"] == "opentelemetry"
    assert "instrumentation_instructions" in app_data

    # 2. Get by ID
    get_res = client.get(f"/api/applications/{app_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == app_id
    assert "env_vars" in get_res.json()["instrumentation_instructions"]
    assert "otlp_grpc_endpoint" in get_res.json()["instrumentation_instructions"]

    # 3. Test Connection requires authentication (missing header -> 401)
    unauth_res = client.post(f"/api/applications/{app_id}/test-connection")
    assert unauth_res.status_code == 401

    # 4. Test Connection with invalid token -> 403
    forbidden_res = client.post(
        f"/api/applications/{app_id}/test-connection",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert forbidden_res.status_code == 403

    # 5. Test Connection with valid authentication -> 200
    test_res = client.post(f"/api/applications/{app_id}/test-connection", headers=AUTH_HEADERS)
    assert test_res.status_code == 200
    test_data = test_res.json()
    assert "status" in test_data
    assert "telemetry_summary" in test_data
    assert "is_connected" in test_data
    assert "latency_ms" in test_data

    # 6. Delete
    del_res = client.delete(f"/api/applications/{app_id}")
    assert del_res.status_code == 204

    # 7. Verify 404 after deletion
    get_again = client.get(f"/api/applications/{app_id}")
    assert get_again.status_code == 404


def test_test_connection_fails_closed_when_api_key_unset(monkeypatch):
    """Test require_probe_authentication returns 503 when settings.API_KEY is unset."""
    monkeypatch.setattr(settings, "API_KEY", None)
    res = client.post("/api/applications/app-api-production/test-connection", headers=AUTH_HEADERS)
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"].lower()


def test_test_connection_rejects_non_ascii_credentials():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        require_probe_authentication("Bearer tøkén")
    assert exc.value.status_code == 403


def test_create_application_duplicate_service_fails():
    """Test POST /api/applications fails when duplicate service_name + environment is added."""
    payload = {
        "name": "API Duplicate Test",
        "service_name": "api",
        "environment": "production",
        "integration_type": "opentelemetry"
    }
    res = client.post("/api/applications", json=payload)
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"].lower()


def test_test_connection_nonexistent_app():
    """Test testing connection for non-existent app returns 404 when authenticated."""
    res = client.post("/api/applications/non-existent-id/test-connection", headers=AUTH_HEADERS)
    assert res.status_code == 404
