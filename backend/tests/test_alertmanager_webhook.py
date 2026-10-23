"""Authenticated Alertmanager-to-incident persistence tests."""

from fastapi.testclient import TestClient
import pytest

from backend.app.config import settings
from backend.app.main import app
from backend.app.queue.publisher import get_publisher
from backend.app.api.webhooks import _require_webhook_authentication

TEST_WEBHOOK_SECRET = "unit-test-alertmanager-secret"


@pytest.fixture(autouse=True)
def disable_external_startup_seeding(monkeypatch):
    """Keep the API TestClient isolated from the developer's configured database."""
    monkeypatch.setattr(settings, "ENABLE_DEMO_SEEDING", False)


class RecordingPublisher:
    def __init__(self):
        self.events = []

    def publish_incident(self, **event):
        self.events.append(event)
        return "1700000000000-0"


def alert_payload(status="firing"):
    return {
        "version": "4",
        "groupKey": "{alertname=\"SlowQueryDetected\",service=\"orders\"}",
        "status": status,
        "receiver": "sherlog-webhook",
        "alerts": [
            {
                "status": status,
                "labels": {
                    "alertname": "SlowQueryDetected",
                    "service": "orders",
                    "severity": "warning",
                },
                "annotations": {
                    "summary": "Slow queries detected in orders service",
                    "description": "Orders slow-query counter increased during the last minute.",
                },
                "startsAt": "2026-10-23T10:00:00Z",
                "endsAt": "2026-10-23T10:01:00Z" if status == "resolved" else "0001-01-01T00:00:00Z",
                "generatorURL": "http://prometheus:9090/graph?g0.expr=increase(slow_queries_total%5B1m%5D)%20%3E%200",
                "fingerprint": "slow-query-orders-test-fingerprint",
                "value": "1e+00",
            }
        ],
    }


def test_alertmanager_webhook_fails_closed_when_secret_is_missing(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SECRET", None)
    response = client.post("/api/v1/webhooks/alertmanager", json=alert_payload())
    assert response.status_code == 503
    assert response.json()["detail"] == "Alertmanager webhook authentication is not configured on the server."


def test_alertmanager_webhook_rejects_non_ascii_token(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _require_webhook_authentication("Bearer tøkén")
    assert exc.value.status_code == 401


def test_alertmanager_webhook_persists_deduplicates_and_resolves_incidents(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    publisher = RecordingPublisher()
    app.dependency_overrides[get_publisher] = lambda: publisher
    headers = {"Authorization": f"Bearer {TEST_WEBHOOK_SECRET}"}

    try:
        unauthorized = client.post("/api/v1/webhooks/alertmanager", json=alert_payload())
        assert unauthorized.status_code == 401

        firing = client.post("/api/v1/webhooks/alertmanager", json=alert_payload(), headers=headers)
        assert firing.status_code == 200
        result = firing.json()
        assert result["created_incidents"] == 1
        assert result["incident_ids"] == ["INC-00001"]
        assert len(publisher.events) == 1

        persisted = client.get("/api/incidents").json()
        assert len(persisted) == 1
        assert persisted[0]["id"] == "INC-00001"
        assert persisted[0]["source"] == "alertmanager"
        assert persisted[0]["severity"] == "MEDIUM"
        assert persisted[0]["metadata"]["alertmanager"]["labels"]["alertname"] == "SlowQueryDetected"
        assert persisted[0]["metadata"]["alertmanager"]["value"] == "1e+00"
        assert persisted[0]["metadata"]["queue_status"] == "ENQUEUED"

        duplicate = client.post("/api/v1/webhooks/alertmanager", json=alert_payload(), headers=headers)
        assert duplicate.status_code == 200
        assert duplicate.json()["duplicate_alerts"] == 1
        assert len(client.get("/api/incidents").json()) == 1
        assert len(publisher.events) == 1

        resolved = client.post(
            "/api/v1/webhooks/alertmanager",
            json=alert_payload(status="resolved"),
            headers=headers,
        )
        assert resolved.status_code == 200
        assert resolved.json()["resolved_incidents"] == 1
        record = client.get("/api/incidents/INC-00001").json()
        assert record["status"] == "RESOLVED"
        assert record["metadata"]["alertmanager"]["status"] == "resolved"
    finally:
        app.dependency_overrides.pop(get_publisher, None)
