"""Comprehensive test suite for Human Approval/Rejection Workflow & Persistent Audit Trail.

Validates:
1. Valid investigation produces a stable persisted remediation proposal.
2. Operator can approve a remediation proposal via API (status -> APPROVED, actor, timestamp).
3. Operator can reject a remediation proposal via API (status -> REJECTED, actor, reason).
4. Rejection is strictly not treated as approval.
5. Idempotent repeated approval/rejection returns existing decision without creating duplicate audit records.
6. Conflicting transitions (approve then reject, or reject then approve) return HTTP 400 Bad Request.
7. Malformed action values return HTTP 400.
8. Non-existent incident / proposal returns HTTP 404.
9. Persistent audit log record is created in PostgreSQL and accessible via GET /api/v1/investigations/audit/log.
10. Safety check: Calling approve or reject NEVER executes destructive commands, subprocesses, or production mutations.
"""

from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.models.incident import IncidentModel
from backend.app.db.models.investigation import InvestigationModel, AuditLogModel
from backend.app.api.investigations import _investigations, _audit_log


@pytest.fixture(autouse=True)
def clean_memory_caches():
    """Ensure in-memory caches are clean before and after each test."""
    _investigations.clear()
    _audit_log.clear()
    yield
    _investigations.clear()
    _audit_log.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_incident(db_session):
    """Seed a test incident in the database."""
    incident = IncidentModel(
        id="INC-00100",
        title="High Database Connection Pool Saturation",
        service="orders",
        severity="HIGH",
        status="OPEN",
        summary="Connection pool exhausted on orders primary database",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(incident)
    db_session.commit()
    return incident


@pytest.fixture
def test_investigation(db_session, test_incident):
    """Seed a test completed investigation with a remediation proposal."""
    inv = InvestigationModel(
        id=f"INV-{test_incident.id}",
        incident_id=test_incident.id,
        state="COMPLETED",
        current_step=4,
        evidence=[{"source": "metrics", "name": "db_pool_utilization", "value": 0.98}],
        hypotheses=[
            {
                "root_cause": "database_connection_pool_exhaustion",
                "title": "PostgreSQL Connection Pool Exhaustion",
                "score": 92.0,
            }
        ],
        evaluation={
            "has_sufficient_evidence": True,
            "top_cause": {
                "root_cause": "database_connection_pool_exhaustion",
                "title": "PostgreSQL Connection Pool Exhaustion",
                "confidence": "HIGH",
            },
            "rationale": "Saturated connection pool confirmed by metrics",
            "remediation": {
                "id": f"REM-{test_incident.id}",
                "incident_id": test_incident.id,
                "root_cause_title": "PostgreSQL Connection Pool Exhaustion",
                "root_cause_description": "Connection pool exhausted on orders primary database",
                "action_title": "Increase PostgreSQL Connection Pool Size to 40",
                "action_description": "Scale connection pool limits from 20 to 40 connections in deployment config.",
                "target_service": "orders",
                "status": "AWAITING_APPROVAL",
                "approved_by": None,
                "approved_at": None,
                "rejection_reason": None,
            },
        },
        root_cause="database_connection_pool_exhaustion",
        investigation_source="llm",
        tool_executions=[],
        budget_consumed={"steps": 4, "tool_calls": 3},
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(inv)
    db_session.commit()
    return inv


def test_get_investigation_returns_stable_remediation(client, test_investigation):
    """Verify that fetching an investigation returns a stable remediation proposal with AWAITING_APPROVAL status."""
    response = client.get(f"/api/v1/investigations/{test_investigation.incident_id}")
    assert response.status_code == 200
    data = response.json()
    assert "remediation" in data
    rem = data["remediation"]
    assert rem["id"] == f"REM-{test_investigation.incident_id}"
    assert rem["status"] == "AWAITING_APPROVAL"
    assert rem["target_service"] == "orders"
    assert rem["approved_by"] is None


def test_approve_remediation_flow(client, test_investigation, db_session):
    """Verify successful approval transitions status to APPROVED, records actor, and persists audit log."""
    payload = {
        "action": "approve",
        "approved_by": "alice_sre",
        "reason": "Verified pool metrics in Grafana; change is safe to proceed.",
    }
    response = client.post(f"/api/v1/investigations/{test_investigation.incident_id}/approve", json=payload)
    assert response.status_code == 200
    rem = response.json()
    assert rem["status"] == "APPROVED"
    assert rem["approved_by"] == "alice_sre"
    assert rem["approved_at"] is not None
    assert rem["rejection_reason"] is None

    # Verify persistence in database
    db_session.expire_all()
    inv_in_db = db_session.query(InvestigationModel).filter_by(id=test_investigation.id).first()
    assert inv_in_db.evaluation["remediation"]["status"] == "APPROVED"
    assert inv_in_db.evaluation["remediation"]["approved_by"] == "alice_sre"

    # Verify persistent audit log entry
    audit_rows = db_session.query(AuditLogModel).filter_by(incident_id=test_investigation.incident_id).all()
    assert len(audit_rows) == 1
    audit = audit_rows[0]
    assert audit.action == "REMEDIATION_APPROVED"
    assert audit.actor == "alice_sre"
    assert audit.proposal_id == f"REM-{test_investigation.incident_id}"
    assert "Verified pool metrics" in audit.reason

    # Verify audit log endpoint returns the record
    log_res = client.get(f"/api/v1/investigations/audit/log?incident_id={test_investigation.incident_id}")
    assert log_res.status_code == 200
    log_entries = log_res.json()
    assert len(log_entries) == 1
    assert log_entries[0]["action"] == "REMEDIATION_APPROVED"
    assert log_entries[0]["actor"] == "alice_sre"


def test_reject_remediation_flow(client, test_investigation, db_session):
    """Verify rejection transitions status to REJECTED with reason, actor, and persists audit log."""
    payload = {
        "action": "reject",
        "approved_by": "bob_lead",
        "reason": "Database server RAM is at 95%; increasing pool will cause OOM.",
    }
    response = client.post(f"/api/v1/investigations/{test_investigation.incident_id}/approve", json=payload)
    assert response.status_code == 200
    rem = response.json()
    assert rem["status"] == "REJECTED"
    assert rem["approved_by"] == "bob_lead"
    assert rem["rejection_reason"] == "Database server RAM is at 95%; increasing pool will cause OOM."

    # Verify persistence
    db_session.expire_all()
    inv_in_db = db_session.query(InvestigationModel).filter_by(id=test_investigation.id).first()
    assert inv_in_db.evaluation["remediation"]["status"] == "REJECTED"

    # Verify persistent audit log entry
    audit_rows = db_session.query(AuditLogModel).filter_by(incident_id=test_investigation.incident_id).all()
    assert len(audit_rows) == 1
    assert audit_rows[0].action == "REMEDIATION_REJECTED"
    assert audit_rows[0].actor == "bob_lead"
    assert "RAM is at 95%" in audit_rows[0].reason


def test_idempotent_duplicate_approval(client, test_investigation, db_session):
    """Submitting approval twice must return existing decision and NOT create duplicate audit log entries."""
    payload = {"action": "approve", "approved_by": "operator"}
    res1 = client.post(f"/api/v1/investigations/{test_investigation.incident_id}/approve", json=payload)
    assert res1.status_code == 200

    # Second approval request
    res2 = client.post(f"/api/v1/investigations/{test_investigation.incident_id}/approve", json=payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "APPROVED"

    # Exactly one audit entry should exist
    audit_count = db_session.query(AuditLogModel).filter_by(incident_id=test_investigation.incident_id).count()
    assert audit_count == 1


def test_idempotent_duplicate_rejection(client, test_investigation, db_session):
    """Submitting rejection twice must return existing decision and NOT create duplicate audit log entries."""
    payload = {"action": "reject", "approved_by": "operator", "reason": "Not appropriate"}
    res1 = client.post(f"/api/v1/investigations/{test_investigation.incident_id}/approve", json=payload)
    assert res1.status_code == 200

    # Second rejection request
    res2 = client.post(f"/api/v1/investigations/{test_investigation.incident_id}/approve", json=payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "REJECTED"

    # Exactly one audit entry should exist
    audit_count = db_session.query(AuditLogModel).filter_by(incident_id=test_investigation.incident_id).count()
    assert audit_count == 1


def test_invalid_state_transition_approved_to_reject(client, test_investigation):
    """Once approved, a proposal cannot be rejected; must return HTTP 400."""
    client.post(f"/api/v1/investigations/{test_investigation.incident_id}/approve", json={"action": "approve"})
    conflict_res = client.post(
        f"/api/v1/investigations/{test_investigation.incident_id}/approve",
        json={"action": "reject", "reason": "Changed mind"},
    )
    assert conflict_res.status_code == 400
    assert "already been approved" in conflict_res.json()["detail"]


def test_invalid_state_transition_rejected_to_approve(client, test_investigation):
    """Once rejected, a proposal cannot be approved; must return HTTP 400."""
    client.post(f"/api/v1/investigations/{test_investigation.incident_id}/approve", json={"action": "reject"})
    conflict_res = client.post(
        f"/api/v1/investigations/{test_investigation.incident_id}/approve",
        json={"action": "approve"},
    )
    assert conflict_res.status_code == 400
    assert "already been rejected" in conflict_res.json()["detail"]


def test_invalid_action_value_returns_400(client, test_investigation):
    """Malformed action must return HTTP 400 Bad Request."""
    res = client.post(
        f"/api/v1/investigations/{test_investigation.incident_id}/approve",
        json={"action": "execute_shell_command"},
    )
    assert res.status_code == 400
    assert "Action must be 'approve' or 'reject'" in res.json()["detail"]


def test_nonexistent_incident_returns_404(client):
    """Nonexistent incident returns HTTP 404 Not Found."""
    res = client.post(
        "/api/v1/investigations/INC-NONEXISTENT/approve",
        json={"action": "approve"},
    )
    assert res.status_code == 404


def test_approval_never_executes_destructive_commands(client, test_investigation):
    """Verifies that approval records human intent without executing subprocesses or mutating services."""
    with patch("subprocess.run") as mock_subproc, patch("os.system") as mock_system:
        res = client.post(
            f"/api/v1/investigations/{test_investigation.incident_id}/approve",
            json={"action": "approve", "approved_by": "safe_operator"},
        )
        assert res.status_code == 200
        mock_subproc.assert_not_called()
        mock_system.assert_not_called()


def test_both_api_and_api_v1_prefixes_work(client, test_investigation):
    """Verify backward-compatible routing: both /api and /api/v1 routes respond identically."""
    res1 = client.get(f"/api/v1/investigations/{test_investigation.incident_id}")
    res2 = client.get(f"/api/investigations/{test_investigation.incident_id}")
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["investigation_id"] == res2.json()["investigation_id"]
