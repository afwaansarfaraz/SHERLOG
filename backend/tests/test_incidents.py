"""Automated tests for incident ingestion, validation, and retrieval."""

import pytest
from fastapi.testclient import TestClient


def test_ingest_incident_success_complete_payload(client: TestClient):
    """POST /api/incidents with full valid payload should return 201 Created with assigned ID."""
    payload = {
        "title": "Database connection pool exhaustion",
        "service": "orders",
        "severity": "CRITICAL",
        "status": "OPEN",
        "summary": "High checkout latency and connection checkout timeout errors in orders service.",
        "source": "alertmanager",
        "affected_endpoints": ["POST /orders", "GET /orders"],
        "metadata": {
            "promql": "rate(db_pool_exhaustion_errors_total[1m]) > 0",
            "cluster": "prod-us-east-1",
        },
        "fingerprint": "alert_fp_orders_pool_001",
    }

    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["id"] == "INC-00001"
    assert data["title"] == payload["title"]
    assert data["service"] == payload["service"]
    assert data["severity"] == "CRITICAL"
    assert data["status"] == "OPEN"
    assert data["summary"] == payload["summary"]
    assert data["source"] == "alertmanager"
    assert data["affected_endpoints"] == ["POST /orders", "GET /orders"]
    assert data["metadata"]["cluster"] == "prod-us-east-1"
    assert data["fingerprint"] == "alert_fp_orders_pool_001"
    assert "created_at" in data


def test_ingest_incident_success_minimal_payload(client: TestClient):
    """POST /api/incidents with minimal required fields should succeed with default values."""
    payload = {
        "title": "Payment gateway timeout",
        "service": "payments",
        "severity": "HIGH",
        "summary": "Socket timeout calling external processor.",
    }

    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["id"] == "INC-00001"
    assert data["status"] == "OPEN"
    assert data["source"] == "alertmanager"
    assert data["affected_endpoints"] == []
    assert data["metadata"] == {}
    assert data["fingerprint"] is None


def test_ingest_incident_missing_required_fields(client: TestClient):
    """POST /api/incidents missing required fields must return 422 Unprocessable Entity."""
    required_fields = ["title", "service", "severity", "summary"]

    for field in required_fields:
        payload = {
            "title": "API latency spike",
            "service": "api",
            "severity": "MEDIUM",
            "summary": "Spike in P95 latency observed.",
        }
        del payload[field]

        response = client.post("/api/incidents", json=payload)
        assert response.status_code == 422, f"Expected 422 when '{field}' is missing"
        errors = response.json()["detail"]
        assert any(err["loc"][-1] == field for err in errors)


def test_ingest_incident_invalid_severity(client: TestClient):
    """POST /api/incidents with unknown severity should return 422."""
    payload = {
        "title": "Memory leak detected",
        "service": "orders",
        "severity": "EXTREME",  # Invalid severity value
        "summary": "RSS usage exceeded 90% memory ceiling.",
    }

    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(err["loc"][-1] == "severity" for err in errors)


def test_ingest_incident_blank_whitespace_fields(client: TestClient):
    """POST /api/incidents with blank or whitespace-only strings should return 422."""
    payload = {
        "title": "   ",  # Blank title
        "service": "orders",
        "severity": "LOW",
        "summary": "Normal low priority warning.",
    }

    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 422


def test_ingest_incident_short_length_bounds(client: TestClient):
    """POST /api/incidents with title shorter than 3 chars or summary shorter than 5 chars should return 422."""
    payload_short_title = {
        "title": "ab",
        "service": "orders",
        "severity": "LOW",
        "summary": "Valid summary description.",
    }
    resp1 = client.post("/api/incidents", json=payload_short_title)
    assert resp1.status_code == 422

    payload_short_summary = {
        "title": "Valid title",
        "service": "orders",
        "severity": "LOW",
        "summary": "bad",  # < 5 chars
    }
    resp2 = client.post("/api/incidents", json=payload_short_summary)
    assert resp2.status_code == 422


def test_get_incident_by_id(client: TestClient):
    """GET /api/incidents/{id} should return the incident if found, or 404 if missing."""
    # Ingest incident
    create_resp = client.post(
        "/api/incidents",
        json={
            "title": "Slow database query",
            "service": "orders",
            "severity": "MEDIUM",
            "summary": "Query execution time exceeded 2000ms threshold.",
        },
    )
    assert create_resp.status_code == 201
    incident_id = create_resp.json()["id"]

    # Fetch existing
    get_resp = client.get(f"/api/incidents/{incident_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == incident_id
    assert get_resp.json()["title"] == "Slow database query"

    # Fetch non-existent
    missing_resp = client.get("/api/incidents/INC-99999")
    assert missing_resp.status_code == 404
    assert "not found" in missing_resp.json()["detail"].lower()


def test_list_incidents(client: TestClient):
    """GET /api/incidents should list all ingested incidents in reverse chronological order."""
    # List empty initially
    init_resp = client.get("/api/incidents")
    assert init_resp.status_code == 200
    assert init_resp.json() == []

    # Ingest two incidents
    client.post(
        "/api/incidents",
        json={
            "title": "Incident 1",
            "service": "api",
            "severity": "LOW",
            "summary": "First anomaly summary.",
        },
    )
    client.post(
        "/api/incidents",
        json={
            "title": "Incident 2",
            "service": "orders",
            "severity": "HIGH",
            "summary": "Second anomaly summary.",
        },
    )

    list_resp = client.get("/api/incidents")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 2
    # Verify latest first
    assert items[0]["id"] == "INC-00002"
    assert items[1]["id"] == "INC-00001"
