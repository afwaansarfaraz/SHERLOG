"""Tests for Settings, Evaluations, and Audit Log API endpoints."""

import json
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.db.models.investigation import AuditLogModel
from backend.app.db.session import get_db

client = TestClient(app)


def test_settings_status_connectivity(db_session: Session):
    """Test /api/settings/status returns live status with masked secrets."""
    response = client.get("/api/settings/status")
    assert response.status_code == 200
    data = response.json()

    assert "services" in data
    assert "postgres" in data["services"]
    assert data["services"]["postgres"]["is_connected"] is True
    assert "redis" in data["services"]

    # Security check: Never expose raw passwords in endpoint
    pg_endpoint = data["services"]["postgres"]["endpoint"]
    assert "postgres:postgres" not in pg_endpoint
    assert ":***@" in pg_endpoint

    # LLM configuration check
    assert "llm" in data
    assert data["llm"]["provider"] == "groq"
    if data["llm"]["is_configured"]:
        assert "••••" in data["llm"]["api_key_masked"]

    # RAG configuration check
    assert "rag" in data
    assert data["rag"]["embedding_provider"] == "fastembed"
    assert data["rag"]["indexed_documents_count"] >= 0

    # Budget guards check
    assert "budget_guards" in data
    assert data["budget_guards"]["max_steps"] == 8
    assert data["budget_guards"]["max_tokens"] == 12000

    # OAuth status check
    assert data["security"]["oauth_status"] == "not_implemented"


def test_evaluations_scenarios_listing():
    """Test /api/evaluations/scenarios returns all 10 ground truth scenarios."""
    response = client.get("/api/evaluations/scenarios")
    assert response.status_code == 200
    scenarios = response.json()

    assert len(scenarios) == 10
    scenario_ids = [s["scenario_id"] for s in scenarios]
    assert "SCN-001" in scenario_ids
    assert "SCN-010" in scenario_ids

    first = scenarios[0]
    assert "name" in first
    assert "fault_id" in first
    assert "expected_root_cause" in first
    assert first["evidence_count"] >= 0


def test_evaluations_runs_listing_and_retrieval():
    """Test /api/evaluations/runs listing and fetching specific run."""
    response = client.get("/api/evaluations/runs")
    assert response.status_code == 200
    runs = response.json()
    assert isinstance(runs, list)
    assert len(runs) >= 1

    first_run_id = runs[0]["run_id"]
    run_detail_resp = client.get(f"/api/evaluations/runs/{first_run_id}")
    assert run_detail_resp.status_code == 200
    detail = run_detail_resp.json()
    assert detail["run_id"] == first_run_id
    assert "results" in detail
    assert len(detail["results"]) == 10


def test_evaluations_run_invalid_id():
    """Test /api/evaluations/runs/{run_id} returns 404 on invalid ID."""
    response = client.get("/api/evaluations/runs/eval-run-nonexistent-999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_evaluations_trigger_benchmark_run():
    """Test POST /api/evaluations/run executes real evaluation and returns report."""
    response = client.post(
        "/api/evaluations/run",
        json={"evaluator_name": "Pytest Baseline Runner", "save_results": True},
    )
    assert response.status_code == 200
    report = response.json()

    assert report["total_scenarios"] == 10
    assert report["passed_scenarios"] == 10
    assert report["top_1_accuracy"] == 100.0
    assert len(report["results"]) == 10
    assert report["evaluator_name"] == "Pytest Baseline Runner"


def test_evaluations_comparative_data():
    """Test /api/evaluations/comparative returns baseline vs LLM comparative metrics."""
    response = client.get("/api/evaluations/comparative")
    assert response.status_code == 200
    comp = response.json()

    assert "baseline" in comp
    assert "llm_no_rag" in comp
    assert "llm_rag" in comp
    assert comp["baseline"]["top_1_accuracy"] > 0


def test_audit_logs_listing_and_filtering(db_session: Session):
    """Test /api/audit-logs and /api/investigations/audit/log filtering and pagination."""
    # Seed test audit log entries
    test_entry_1 = AuditLogModel(
        id="AUD-TEST-001",
        action="REMEDIATION_APPROVED",
        actor="Alice",
        investigation_id="INV-TEST-1",
        incident_id="INC-AUD-001",
        proposal_id="REM-AUD-001",
        reason=None,
        details="Approved proposal 1",
    )
    test_entry_2 = AuditLogModel(
        id="AUD-TEST-002",
        action="REMEDIATION_REJECTED",
        actor="Bob",
        investigation_id="INV-TEST-2",
        incident_id="INC-AUD-002",
        proposal_id="REM-AUD-002",
        reason="Budget frozen",
        details="Rejected proposal 2",
    )
    db_session.add(test_entry_1)
    db_session.add(test_entry_2)
    db_session.commit()

    # List all
    res_all = client.get("/api/audit-logs")
    assert res_all.status_code == 200
    all_logs = res_all.json()
    ids = [entry["id"] for entry in all_logs]
    assert "AUD-TEST-001" in ids
    assert "AUD-TEST-002" in ids

    # Filter by incident_id
    res_filtered = client.get("/api/audit-logs?incident_id=INC-AUD-001")
    assert res_filtered.status_code == 200
    filtered_logs = res_filtered.json()
    assert all(e["incident_id"] == "INC-AUD-001" for e in filtered_logs)
    assert any(e["id"] == "AUD-TEST-001" for e in filtered_logs)

    # Filter by action
    res_rejected = client.get("/api/audit-logs?action=REMEDIATION_REJECTED")
    assert res_rejected.status_code == 200
    rejected_logs = res_rejected.json()
    assert all(e["action"] == "REMEDIATION_REJECTED" for e in rejected_logs)

    # Pagination with limit
    res_limit = client.get("/api/audit-logs?limit=1")
    assert res_limit.status_code == 200
    assert len(res_limit.json()) == 1
