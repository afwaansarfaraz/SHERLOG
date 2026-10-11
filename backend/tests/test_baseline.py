"""Unit tests for the deterministic rule-based baseline investigator."""

import pytest
from backend.app.baseline import (
    ConfidenceLevel,
    EvidenceItem,
    EvidenceType,
    RootCause,
    RuleBasedInvestigator,
)
from backend.app.schemas.incident import IncidentCreate, IncidentSeverity


@pytest.fixture
def investigator():
    return RuleBasedInvestigator()


def test_baseline_db_pool_exhaustion(investigator):
    incident = {
        "id": "INC-00001",
        "service": "orders",
        "title": "Database connection pool exhaustion in orders service",
        "summary": "Orders service is experiencing connection checkout timeouts from PostgreSQL pool",
        "metadata": {"alertname": "DbPoolExhausted"},
    }
    evidence = [
        EvidenceItem(
            source=EvidenceType.METRIC,
            name="db_pool_exhaustion_errors_total",
            value=12.0,
            service="orders",
        ),
        EvidenceItem(
            source=EvidenceType.METRIC,
            name="db_connections_active",
            value=30.0,
            service="orders",
        ),
        EvidenceItem(
            source=EvidenceType.LOG,
            name="orders_app_log",
            value="QueuePool limit of size 10 overflow 20 reached, connection timed out",
            service="orders",
        ),
    ]

    report = investigator.investigate(incident, evidence)

    assert report.has_sufficient_evidence is True
    assert report.top_root_cause is not None
    assert report.top_root_cause.root_cause == RootCause.DATABASE_CONNECTION_POOL_EXHAUSTION.value
    assert report.top_root_cause.confidence == ConfidenceLevel.HIGH
    assert report.top_root_cause.score >= 100.0
    assert len(report.top_root_cause.supporting_evidence) >= 3
    assert report.top_root_cause.recommended_remediation == "increase_db_connection_pool_size"


def test_baseline_slow_query(investigator):
    incident = {
        "id": "INC-00002",
        "service": "orders",
        "title": "Slow database query detected",
        "summary": "Database queries exceeding threshold detected in orders service",
        "metadata": {"alertname": "SlowQueryDetected"},
    }
    evidence = [
        EvidenceItem(
            source=EvidenceType.METRIC,
            name="slow_queries_total",
            value=8.0,
            service="orders",
        ),
        EvidenceItem(
            source=EvidenceType.METRIC,
            name="http_request_duration_seconds",
            value=1.85,
            service="orders",
        ),
        EvidenceItem(
            source=EvidenceType.LOG,
            name="orders_app_log",
            value="Slow query fault active: executing heavy DB query with delay=1.8s",
            service="orders",
        ),
    ]

    report = investigator.investigate(incident, evidence)

    assert report.has_sufficient_evidence is True
    assert report.top_root_cause is not None
    assert report.top_root_cause.root_cause == RootCause.SLOW_DATABASE_QUERY.value
    assert report.top_root_cause.confidence == ConfidenceLevel.HIGH
    assert report.top_root_cause.recommended_remediation == "optimize_query_or_add_index"


def test_baseline_dependency_timeout(investigator):
    incident = {
        "id": "INC-00003",
        "service": "orders",
        "title": "Downstream dependency timeout",
        "summary": "Orders service timed out attempting to communicate with payments downstream",
        "metadata": {"alertname": "DependencyTimeout"},
    }
    evidence = [
        EvidenceItem(
            source=EvidenceType.METRIC,
            name="dependency_timeouts_total",
            value=15.0,
            service="orders",
        ),
        EvidenceItem(
            source=EvidenceType.TRACE,
            name="payments_http_span",
            value=504,
            service="orders",
        ),
        EvidenceItem(
            source=EvidenceType.LOG,
            name="orders_app_log",
            value="Downstream dependency timeout calling Payments service for Order #104: Payment service timed out",
            service="orders",
        ),
    ]

    report = investigator.investigate(incident, evidence)

    assert report.has_sufficient_evidence is True
    assert report.top_root_cause is not None
    assert report.top_root_cause.root_cause == RootCause.DOWNSTREAM_DEPENDENCY_TIMEOUT.value
    assert report.top_root_cause.confidence == ConfidenceLevel.HIGH
    assert report.top_root_cause.recommended_remediation == "increase_downstream_timeout"


def test_baseline_traffic_spike(investigator):
    incident = {
        "id": "INC-00004",
        "service": "api",
        "title": "Sudden traffic spike on API gateway",
        "summary": "High concurrency load against API gateway checkout endpoint causing saturation",
        "metadata": {"alertname": "TrafficSpikeDetected"},
    }
    evidence = [
        EvidenceItem(
            source=EvidenceType.METRIC,
            name="checkout_requests_per_second",
            value=150.0,
            service="api",
        ),
        EvidenceItem(
            source=EvidenceType.LOG,
            name="api_gateway_log",
            value="High concurrency load: concurrency limit reached for checkout",
            service="api",
        ),
    ]

    report = investigator.investigate(incident, evidence)

    assert report.has_sufficient_evidence is True
    assert report.top_root_cause is not None
    assert report.top_root_cause.root_cause == RootCause.SUDDEN_TRAFFIC_SPIKE.value
    assert report.top_root_cause.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
    assert report.top_root_cause.recommended_remediation == "apply_rate_limiting_and_scale"


def test_baseline_configuration_error(investigator):
    incident = {
        "id": "INC-00005",
        "service": "orders",
        "title": "Service configuration error",
        "summary": "Invalid downstream service configuration causing connection failures",
        "metadata": {"alertname": "ConfigError"},
    }
    evidence = [
        EvidenceItem(
            source=EvidenceType.TRACE,
            name="payments_connection",
            value=502,
            service="orders",
        ),
        EvidenceItem(
            source=EvidenceType.CONFIG,
            name="PAYMENTS_SERVICE_URL",
            value="http://invalid-payments-host:9999",
            service="orders",
        ),
        EvidenceItem(
            source=EvidenceType.LOG,
            name="orders_app_log",
            value="Downstream connection error calling Payments at http://invalid-payments-host:9999: ConnectError",
            service="orders",
        ),
    ]

    report = investigator.investigate(incident, evidence)

    assert report.has_sufficient_evidence is True
    assert report.top_root_cause is not None
    assert report.top_root_cause.root_cause == RootCause.INVALID_SERVICE_CONFIGURATION.value
    assert report.top_root_cause.recommended_remediation == "revert_configuration_change"


def test_baseline_memory_leak(investigator):
    incident = {
        "id": "INC-00006",
        "service": "payments",
        "title": "Memory leak detected",
        "summary": "RSS usage exceeded 90% memory ceiling with progressive leak",
        "metadata": {"alertname": "MemoryLeakDetected"},
    }
    evidence = [
        EvidenceItem(
            source=EvidenceType.METRIC,
            name="process_resident_memory_bytes_ratio",
            value=0.94,
            service="payments",
        ),
        EvidenceItem(
            source=EvidenceType.LOG,
            name="payments_log",
            value="OOMKilled: RSS memory consumption leak detected",
            service="payments",
        ),
        EvidenceItem(
            source=EvidenceType.TRACE,
            name="container_exit_code",
            value=137,
            service="payments",
        ),
    ]

    report = investigator.investigate(incident, evidence)

    assert report.has_sufficient_evidence is True
    assert report.top_root_cause is not None
    assert report.top_root_cause.root_cause == RootCause.MEMORY_LEAK_EXHAUSTION.value
    assert report.top_root_cause.confidence == ConfidenceLevel.HIGH
    assert report.top_root_cause.recommended_remediation == "restart_service_and_inspect_heap"


def test_baseline_insufficient_evidence_unmatched(investigator):
    """An incident without matching observable evidence must NOT fabricate hypotheses."""
    incident = {
        "id": "INC-00099",
        "service": "api",
        "title": "Vague intermittent anomaly",
        "summary": "Users reporting occasional sluggishness without metric anomalies",
        "metadata": {},
    }
    evidence = []  # No observability evidence

    report = investigator.investigate(incident, evidence)

    assert report.has_sufficient_evidence is False
    assert report.top_root_cause is None
    assert len(report.ranked_root_causes) == 0
    assert "Insufficient evidence" in report.summary


def test_baseline_competing_hypotheses_ranking(investigator):
    """When multiple signals exist, hypotheses must be ranked deterministically by score."""
    incident = {
        "id": "INC-00010",
        "service": "orders",
        "title": "Severe database degradation",
        "summary": "Orders service connection pool exhausted and queries slow",
        "metadata": {"alertname": "DbPoolExhausted"},
    }
    # 2 signals for DB pool exhaustion, 1 weak signal for slow query
    evidence = [
        EvidenceItem(
            source=EvidenceType.METRIC,
            name="db_pool_exhaustion_errors_total",
            value=25.0,
            service="orders",
        ),
        EvidenceItem(
            source=EvidenceType.LOG,
            name="orders_app_log",
            value="QueuePool limit of size 10 overflow 20 reached, connection timed out",
            service="orders",
        ),
        EvidenceItem(
            source=EvidenceType.METRIC,
            name="slow_queries_total",
            value=1.0,
            service="orders",
        ),
    ]

    report = investigator.investigate(incident, evidence)

    assert report.has_sufficient_evidence is True
    assert len(report.ranked_root_causes) >= 2
    # Top rank should be DB pool exhaustion
    assert report.ranked_root_causes[0].root_cause == RootCause.DATABASE_CONNECTION_POOL_EXHAUSTION.value
    # Second rank should be slow query
    assert report.ranked_root_causes[1].root_cause == RootCause.SLOW_DATABASE_QUERY.value
    assert report.ranked_root_causes[0].score > report.ranked_root_causes[1].score


def test_baseline_accepts_pydantic_incident(investigator):
    """Investigator must seamlessly accept Pydantic schema instances."""
    pydantic_incident = IncidentCreate(
        title="Database connection pool exhaustion",
        service="orders",
        severity=IncidentSeverity.CRITICAL,
        summary="Orders service connection pool exhausted.",
        metadata={"alertname": "DbPoolExhausted"},
    )
    evidence = [
        EvidenceItem(
            source=EvidenceType.METRIC,
            name="db_pool_exhaustion_errors_total",
            value=5.0,
            service="orders",
        )
    ]

    report = investigator.investigate(pydantic_incident, evidence)
    assert report.has_sufficient_evidence is True
    assert report.top_root_cause.root_cause == RootCause.DATABASE_CONNECTION_POOL_EXHAUSTION.value
