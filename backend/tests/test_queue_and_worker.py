"""Automated tests for Redis Streams integration, queue publisher, and Incident Worker.

Covers:
- Successful message publishing and consumption
- Acknowledgements (XACK) and pending list (PEL) cleanup
- Consumer group creation and BUSYGROUP handling
- Idempotency and duplicate message delivery guards
- Transient failure retry loop with bounded attempts
- Dead-Letter Queue (DLQ) routing when retries are exhausted
- Malformed message handling
- Stale pending message recovery (autoclaim)
- Redis unavailability resilience (DB persistence never blocked)
"""

import uuid
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import redis
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.main import app
from backend.app.queue.publisher import IncidentPublisher, get_publisher
from backend.app.queue.redis_client import get_redis_client, is_redis_available
from backend.app.schemas.incident import IncidentCreate, IncidentResponse, IncidentSeverity, IncidentStatus
from backend.app.storage.postgres import PostgresIncidentRepository
from backend.app.worker.worker import IncidentWorker


@pytest.fixture
def redis_client():
    """Live Redis client for tests, skipped if Redis is unavailable."""
    if not is_redis_available():
        pytest.skip("Redis server is not running on localhost:6379")
    r = get_redis_client()
    return r


@pytest.fixture
def test_stream_names(redis_client):
    """Generate isolated stream and consumer group names with automatic cleanup."""
    uid = uuid.uuid4().hex[:8]
    stream_name = f"sherlog:test:stream:{uid}"
    dlq_name = f"sherlog:test:dlq:{uid}"
    group_name = f"sherlog:test:group:{uid}"

    yield stream_name, dlq_name, group_name

    # Cleanup test streams and keys after test
    try:
        redis_client.delete(stream_name)
        redis_client.delete(dlq_name)
        for k in redis_client.scan_iter(f"{stream_name}*"):
            redis_client.delete(k)
    except Exception:
        pass


@pytest.fixture
def make_worker(redis_client, db_session_factory):
    """Factory fixture creating IncidentWorker instances wired to isolated test DB."""
    def _create(**kwargs):
        defaults = {
            "redis_client": redis_client,
            "db_session_factory": db_session_factory,
        }
        defaults.update(kwargs)
        return IncidentWorker(**defaults)
    return _create


# ==============================================================================
# 1. PUBLISHER & INGESTION TESTS
# ==============================================================================

def test_publisher_publishes_to_stream_successfully(redis_client, test_stream_names):
    """IncidentPublisher must append a structured event to the Redis Stream."""
    stream_name, dlq_name, _ = test_stream_names
    publisher = IncidentPublisher(redis_client=redis_client, stream_name=stream_name)

    msg_id = publisher.publish_incident(
        incident_id="INC-00101",
        service="orders",
        severity="CRITICAL",
        fingerprint="fp_test_101",
        metadata={"promql": "rate(errors[1m]) > 0"},
    )

    assert msg_id is not None
    assert "-" in msg_id  # Redis stream ID format: <timestamp>-<sequence>

    # Verify stream entry in Redis
    entries = redis_client.xrange(stream_name)
    assert len(entries) == 1
    stream_id, fields = entries[0]
    assert stream_id == msg_id
    assert fields["incident_id"] == "INC-00101"
    assert fields["service"] == "orders"
    assert fields["severity"] == "CRITICAL"
    assert fields["fingerprint"] == "fp_test_101"
    assert fields["retry_count"] == "0"
    assert "enqueued_at" in fields


def test_publisher_handles_redis_unavailability_gracefully():
    """When Redis is offline, publish_incident must return None without raising exceptions."""
    bad_redis = redis.Redis.from_url(
        "redis://127.0.0.1:1/0",  # Unreachable port
        socket_connect_timeout=0.2,
        socket_timeout=0.2,
    )
    publisher = IncidentPublisher(redis_client=bad_redis, stream_name="sherlog:unreachable")

    msg_id = publisher.publish_incident(
        incident_id="INC-00102",
        service="payments",
        severity="HIGH",
    )
    assert msg_id is None


def test_ingestion_api_persists_to_db_when_redis_is_down(client: TestClient):
    """POST /api/incidents must succeed with 201 Created even if Redis queue publishing fails."""
    mock_publisher = MagicMock(spec=IncidentPublisher)
    mock_publisher.publish_incident.return_value = None

    app.dependency_overrides[get_publisher] = lambda: mock_publisher

    payload = {
        "title": "Database connection pool exhaustion",
        "service": "orders",
        "severity": "CRITICAL",
        "summary": "Connection pool checkout timeout under load.",
    }

    try:
        response = client.post("/api/incidents", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"].startswith("INC-")
        assert data["title"] == payload["title"]

        # Verify DB record is persisted and marked PUBLISH_FAILED
        list_resp = client.get(f"/api/incidents/{data['id']}")
        assert list_resp.status_code == 200
        fetched = list_resp.json()
        assert fetched["metadata"].get("queue_status") == "PUBLISH_FAILED"
    finally:
        app.dependency_overrides.pop(get_publisher, None)


# ==============================================================================
# 2. WORKER CONSUMPTION & ACKNOWLEDGEMENT TESTS
# ==============================================================================

def test_worker_setup_consumer_group(test_stream_names, make_worker):
    """Worker must create consumer group and handle existing group (BUSYGROUP) idempotently."""
    stream_name, dlq_name, group_name = test_stream_names
    worker = make_worker(
        stream_name=stream_name,
        group_name=group_name,
        dlq_stream_name=dlq_name,
    )

    # First call creates group
    assert worker.setup_consumer_group() is True

    # Second call detects existing group and succeeds cleanly
    assert worker.setup_consumer_group() is True


def test_worker_consumes_and_acknowledges_incident(redis_client, test_stream_names, make_worker, client: TestClient):
    """Worker must consume incident from stream, transition status to INVESTIGATING, and call XACK."""
    stream_name, dlq_name, group_name = test_stream_names

    # 1. Ingest incident via API
    resp = client.post(
        "/api/incidents",
        json={
            "title": "Payment gateway latency spike",
            "service": "payments",
            "severity": "HIGH",
            "summary": "P95 latency elevated above threshold.",
        },
    )
    assert resp.status_code == 201
    incident_id = resp.json()["id"]

    # 2. Publish to test stream
    publisher = IncidentPublisher(redis_client=redis_client, stream_name=stream_name)
    msg_id = publisher.publish_incident(incident_id=incident_id, service="payments", severity="HIGH")
    assert msg_id is not None

    # 3. Process via worker wired to test DB
    worker = make_worker(
        stream_name=stream_name,
        group_name=group_name,
        dlq_stream_name=dlq_name,
        consumer_name="test-consumer-1",
    )

    success = worker.process_next(block_ms=500)
    assert success is True

    # 4. Verify incident status updated to INVESTIGATING
    inc_resp = client.get(f"/api/incidents/{incident_id}")
    inc_data = inc_resp.json()
    assert inc_data["status"] == "INVESTIGATING"
    assert "worker_consumed_at" in inc_data["metadata"]

    # 5. Verify message was acknowledged (PEL is empty)
    pending = redis_client.xpending(stream_name, group_name)
    assert pending["pending"] == 0


def test_worker_handles_duplicate_message_idempotently(redis_client, test_stream_names, make_worker, client: TestClient):
    """Duplicate message delivery must be detected and ACKed without executing duplicate processing."""
    stream_name, dlq_name, group_name = test_stream_names

    resp = client.post(
        "/api/incidents",
        json={
            "title": "Memory leak detected",
            "service": "orders",
            "severity": "CRITICAL",
            "summary": "Process RSS memory growing steadily.",
        },
    )
    incident_id = resp.json()["id"]

    publisher = IncidentPublisher(redis_client=redis_client, stream_name=stream_name)
    publisher.publish_incident(incident_id=incident_id, service="orders")
    publisher.publish_incident(incident_id=incident_id, service="orders")  # Duplicate

    process_call_count = 0

    def mock_processor(incident, db):
        nonlocal process_call_count
        process_call_count += 1

    worker = make_worker(
        stream_name=stream_name,
        group_name=group_name,
        dlq_stream_name=dlq_name,
        processor=mock_processor,
    )

    # Process first message -> calls processor
    res1 = worker.process_next(block_ms=500)
    assert res1 is True
    assert process_call_count == 1

    # Process duplicate message -> skips processor, still ACKs
    res2 = worker.process_next(block_ms=500)
    assert res2 is True
    assert process_call_count == 1  # Not executed again!

    # Stream PEL is clean
    pending = redis_client.xpending(stream_name, group_name)
    assert pending["pending"] == 0


# ==============================================================================
# 3. RETRY & DEAD-LETTER QUEUE (DLQ) TESTS
# ==============================================================================

def test_worker_retries_transient_failure(redis_client, test_stream_names, make_worker, client: TestClient):
    """When a transient error occurs, worker must requeue with incremented retry count."""
    stream_name, dlq_name, group_name = test_stream_names

    resp = client.post(
        "/api/incidents",
        json={
            "title": "Downstream timeout",
            "service": "orders",
            "severity": "HIGH",
            "summary": "Payments service temporarily unresponsive.",
        },
    )
    incident_id = resp.json()["id"]

    publisher = IncidentPublisher(redis_client=redis_client, stream_name=stream_name)
    publisher.publish_incident(incident_id=incident_id, service="orders")

    call_count = 0

    def failing_processor(incident, db):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Transient connection timeout to observability agent")

    worker = make_worker(
        stream_name=stream_name,
        group_name=group_name,
        dlq_stream_name=dlq_name,
        processor=failing_processor,
        max_retries=3,
    )

    # First attempt: processor fails -> worker requeues with retry_count = 1
    res1 = worker.process_next(block_ms=500)
    assert res1 is False

    # Second attempt: reads retried message -> processor succeeds -> worker ACKs
    res2 = worker.process_next(block_ms=500)
    assert res2 is True

    # Both messages ACKed, PEL is clean
    pending = redis_client.xpending(stream_name, group_name)
    assert pending["pending"] == 0


def test_worker_moves_to_dlq_after_max_retries(redis_client, test_stream_names, make_worker, client: TestClient):
    """When max retries are exceeded, message must be routed to DLQ and ACKed from main stream."""
    stream_name, dlq_name, group_name = test_stream_names

    resp = client.post(
        "/api/incidents",
        json={
            "title": "Persistent corrupt payload incident",
            "service": "api",
            "severity": "MEDIUM",
            "summary": "Fails unrecoverably during investigation.",
        },
    )
    incident_id = resp.json()["id"]

    publisher = IncidentPublisher(redis_client=redis_client, stream_name=stream_name)
    publisher.publish_incident(incident_id=incident_id, service="api")

    def unrecoverable_processor(incident, db):
        raise ValueError("Fatal parser error: unsupported format")

    worker = make_worker(
        stream_name=stream_name,
        group_name=group_name,
        dlq_stream_name=dlq_name,
        processor=unrecoverable_processor,
        max_retries=2,  # Fail on attempt 1 & 2, then DLQ on attempt 3
    )

    # Attempt 1 (retry_count 0 -> 1)
    res1 = worker.process_next(block_ms=500)
    assert res1 is False
    # Attempt 2 (retry_count 1 -> 2)
    res2 = worker.process_next(block_ms=500)
    assert res2 is False
    # Attempt 3 (retry_count 2 -> 3 > max_retries: routed to DLQ)
    res3 = worker.process_next(block_ms=500)
    assert res3 is False

    # Verify DLQ received the failed incident
    dlq_entries = redis_client.xrange(dlq_name)
    assert len(dlq_entries) == 1
    _, dlq_fields = dlq_entries[0]
    assert dlq_fields["incident_id"] == incident_id
    assert dlq_fields["error_type"] == "ValueError"
    assert "Fatal parser error" in dlq_fields["error_message"]
    assert dlq_fields["retry_count"] == "3"

    # Verify main stream is clean and ACKed
    pending = redis_client.xpending(stream_name, group_name)
    assert pending["pending"] == 0

    # Verify incident metadata in DB records DLQ state
    inc = client.get(f"/api/incidents/{incident_id}").json()
    assert inc["metadata"].get("queue_status") == "DLQ"
    assert "Fatal parser error" in inc["metadata"].get("dlq_reason", "")


def test_worker_handles_malformed_message_without_incident_id(redis_client, test_stream_names, make_worker):
    """Malformed messages lacking incident_id must go to DLQ and be ACKed without crashing."""
    stream_name, dlq_name, group_name = test_stream_names
    worker = make_worker(
        stream_name=stream_name,
        group_name=group_name,
        dlq_stream_name=dlq_name,
    )
    worker.setup_consumer_group()

    # Inject malformed message directly
    redis_client.xadd(stream_name, {"corrupt_key": "corrupt_data"})

    res = worker.process_next(block_ms=500)
    assert res is False

    # Verify routed to DLQ
    dlq_entries = redis_client.xrange(dlq_name)
    assert len(dlq_entries) == 1
    assert dlq_entries[0][1]["incident_id"] == "MALFORMED"

    # Main stream acknowledged
    pending = redis_client.xpending(stream_name, group_name)
    assert pending["pending"] == 0


def test_worker_claims_stale_messages_from_crashed_consumer(redis_client, test_stream_names, make_worker, client: TestClient):
    """Worker must reclaim abandoned pending messages from crashed consumers using autoclaim."""
    stream_name, dlq_name, group_name = test_stream_names

    resp = client.post(
        "/api/incidents",
        json={
            "title": "Abandoned job incident",
            "service": "orders",
            "severity": "HIGH",
            "summary": "Simulating worker crash during processing.",
        },
    )
    incident_id = resp.json()["id"]

    # Publish message
    publisher = IncidentPublisher(redis_client=redis_client, stream_name=stream_name)
    publisher.publish_incident(incident_id=incident_id, service="orders")

    worker_a = make_worker(
        stream_name=stream_name,
        group_name=group_name,
        consumer_name="crashed-worker-A",
    )
    worker_a.setup_consumer_group()

    # Worker A reads message from group (message enters PEL as pending for Consumer A)
    streams = redis_client.xreadgroup(
        groupname=group_name,
        consumername="crashed-worker-A",
        streams={stream_name: ">"},
        count=1,
    )
    assert len(streams) == 1
    # Worker A "crashes" -> never calls XACK!
    pending_a = redis_client.xpending(stream_name, group_name)
    assert pending_a["pending"] == 1

    # Worker B claims stale messages with min_idle_ms = 0
    worker_b = make_worker(
        stream_name=stream_name,
        group_name=group_name,
        dlq_stream_name=dlq_name,
        consumer_name="healthy-worker-B",
    )

    reclaimed = worker_b.claim_stale_messages(min_idle_ms=0)
    assert reclaimed == 1

    # Message was reclaimed, processed, and ACKed
    pending_after = redis_client.xpending(stream_name, group_name)
    assert pending_after["pending"] == 0

    inc = client.get(f"/api/incidents/{incident_id}").json()
    assert inc["status"] == "INVESTIGATING"
