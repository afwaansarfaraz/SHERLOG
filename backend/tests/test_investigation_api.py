from unittest.mock import patch

from backend.app.api.investigations import _investigation_trigger_lock
from backend.app.db.models.incident import IncidentModel
from backend.app.db.models.investigation import InvestigationModel
from backend.app.investigation.orchestrator import InvestigationPipeline
from backend.app.investigation.states import InvestigationState


def test_investigation_trigger_lock_rejects_a_concurrent_local_trigger(db_session):
    with _investigation_trigger_lock(db_session, "INC-LOCK-1") as acquired:
        assert acquired is True
        with _investigation_trigger_lock(db_session, "INC-LOCK-1") as duplicate_acquired:
            assert duplicate_acquired is False


def test_investigation_pipeline_failure_is_not_replaced_with_demo_results(client, db_session):
    db_session.add(
        IncidentModel(
            id="INC-API-FAIL",
            title="Orders slow query",
            service="orders",
            severity="MEDIUM",
            status="OPEN",
            summary="Slow query alert from Orders telemetry.",
            source="alertmanager",
            affected_endpoints=[],
            extra_metadata={},
        )
    )
    db_session.commit()

    with patch(
        "backend.app.investigation.orchestrator.InvestigationPipeline.run",
        side_effect=RuntimeError("test failure"),
    ):
        response = client.post(
            "/api/v1/investigations/trigger",
            json={"incident_id": "INC-API-FAIL", "force": True},
        )

    assert response.status_code == 500
    assert "pipeline failed" in response.json()["detail"].lower()
    assert "SIMULATED" not in response.text
    assert "demo_fallback" not in response.text


def test_pipeline_does_not_restart_a_persisted_in_progress_investigation(db_session):
    db_session.add(
        IncidentModel(
            id="INC-IN-PROGRESS",
            title="Orders slow query",
            service="orders",
            severity="MEDIUM",
            status="OPEN",
            summary="Slow query alert from Orders telemetry.",
            source="alertmanager",
            affected_endpoints=[],
            extra_metadata={},
        )
    )
    db_session.add(
        InvestigationModel(
            id="INV-INC-IN-PROGRESS",
            incident_id="INC-IN-PROGRESS",
            state=InvestigationState.GENERATING_HYPOTHESES.value,
            current_step=2,
            evidence=[],
            hypotheses=[],
            evaluation={},
            tool_executions=[],
            budget_consumed={},
        )
    )
    db_session.commit()

    pipeline = InvestigationPipeline(db_session)
    result = pipeline.run({
        "id": "INC-IN-PROGRESS",
        "incident_id": "INC-IN-PROGRESS",
        "service": "orders",
        "title": "Orders slow query",
        "summary": "Slow query alert from Orders telemetry.",
    })

    assert result.status is InvestigationState.GENERATING_HYPOTHESES
    assert result.termination_reason == "Investigation already in progress; duplicate trigger was ignored."
    assert result.budget_consumed.tool_calls == 0
