"""Investigation API endpoints for triggering, monitoring, and approving investigations.

Provides endpoints to trigger an AI investigation on an incident, check investigation status,
retrieve results, and approve/reject remediation proposals.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.app.db.session import get_db
from backend.app.db.models.incident import IncidentModel
from backend.app.db.models.investigation import InvestigationModel, AuditLogModel
from backend.app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ==========================================================================
# Request / Response Schemas
# ==========================================================================

class InvestigationTriggerRequest(BaseModel):
    """Request to trigger an investigation on an incident."""
    incident_id: str = Field(..., description="Incident ID to investigate")
    force: bool = Field(default=False, description="Force re-investigation even if one exists")


class HypothesisResponse(BaseModel):
    id: str
    rank: int
    title: str
    root_cause: str
    score: float
    likelihood: str
    causal_explanation: str
    supporting_evidence: List[str] = []
    contradicting_evidence: List[str] = []
    affected_service: Optional[str] = None


class EvidenceItemResponse(BaseModel):
    id: str
    type: str
    title: str
    source: str
    summary: str
    polarity: str = "neutral"
    timestamp: Optional[str] = None


class RemediationResponse(BaseModel):
    id: str
    incident_id: str
    root_cause_title: str
    root_cause_description: str
    action_title: str
    action_description: str
    target_service: str
    status: str = "AWAITING_APPROVAL"
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    rejection_reason: Optional[str] = None


class InvestigationResponse(BaseModel):
    investigation_id: str
    incident_id: str
    status: str
    source: str = "llm"
    summary: str = ""
    confidence: str = "LOW"
    root_cause: Optional[str] = None
    hypotheses: List[HypothesisResponse] = []
    evidence: List[EvidenceItemResponse] = []
    evidence_count: int = 0
    retrieved_sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Knowledge base documents retrieved via RAG during investigation"
    )
    retrieval_status: str = Field(
        default="NOT_ATTEMPTED",
        description="RAG retrieval outcome: SUCCESS, NO_DOCUMENTS_FOUND, DISABLED, or FAILED"
    )
    remediation: Optional[RemediationResponse] = None
    budget_consumed: Dict[str, Any] = {}
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    is_simulated: bool = Field(default=True, description="Whether this uses simulated/demo data")


class ApprovalRequest(BaseModel):
    action: str = Field(..., description="'approve' or 'reject'")
    approved_by: str = Field(default="operator", description="Name of the approver (actor)")
    reason: Optional[str] = Field(default=None, description="Rejection reason if rejected")


class AuditLogEntry(BaseModel):
    id: str
    timestamp: str
    action: str
    actor: str
    investigation_id: str
    incident_id: str
    proposal_id: Optional[str] = None
    reason: Optional[str] = None
    details: str


# ==========================================================================
# In-Memory Investigation Store (cache; persistent store uses PostgreSQL)
# ==========================================================================

_investigations: Dict[str, Dict[str, Any]] = {}
_audit_log: List[Dict[str, Any]] = []


def _format_pipeline_result(
    result,
    incident_id: str,
    incident_service: str,
    now: datetime,
    existing_remediation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convert an InvestigationResult into an API-serializable dict."""
    hypotheses = []
    for i, hyp in enumerate(result.ranked_hypotheses):
        hypotheses.append({
            "id": f"h{i+1}",
            "rank": i + 1,
            "title": hyp.root_cause if hasattr(hyp, 'root_cause') else str(hyp),
            "root_cause": hyp.root_cause if hasattr(hyp, 'root_cause') else str(hyp),
            "score": hyp.score if hasattr(hyp, 'score') else 50.0,
            "likelihood": "LIKELY" if i == 0 else ("POSSIBLE" if i == 1 else "LESS_LIKELY"),
            "causal_explanation": getattr(hyp, 'explanation', "Determined by investigation pipeline"),
            "supporting_evidence": getattr(hyp, 'supporting_evidence', []),
            "contradicting_evidence": getattr(hyp, 'contradicting_evidence', []),
            "affected_service": incident_service,
        })
    
    evidence_items = []
    for j, ref in enumerate(result.evidence_references):
        evidence_items.append({
            "id": f"ev-{j+1}",
            "type": "metric" if "metric" in ref.lower() else ("log" if "log" in ref.lower() else ("config" if "runbook" in ref.lower() else "trace")),
            "title": ref,
            "source": "investigation-pipeline",
            "summary": ref,
            "polarity": "supporting",
            "timestamp": now.isoformat(),
        })

    retrieved_sources = [
        s.model_dump() if hasattr(s, "model_dump") else s
        for s in getattr(result, "retrieved_sources", [])
    ]
    retrieval_status = getattr(result, "retrieval_status", "NOT_ATTEMPTED")

    if not retrieved_sources:
        for tool_exec in (result.tool_executions or []):
            if tool_exec.get("tool") in ("KnowledgeRetriever", "knowledge_retrieval"):
                raw_docs = tool_exec.get("sources") or tool_exec.get("result", [])
                if isinstance(raw_docs, list):
                    retrieved_sources = raw_docs
                elif isinstance(raw_docs, dict):
                    retrieved_sources = [raw_docs]
                if tool_exec.get("status"):
                    retrieval_status = tool_exec["status"]
                break

    remediation = existing_remediation or {
        "id": f"REM-{incident_id}",
        "incident_id": incident_id,
        "root_cause_title": result.root_cause or "Service Degradation",
        "root_cause_description": result.summary,
        "action_title": f"Remediate {result.root_cause or 'incident'}",
        "action_description": f"Apply recommended fix based on investigation findings for {incident_service}",
        "target_service": incident_service,
        "status": "AWAITING_APPROVAL",
        "approved_by": None,
        "approved_at": None,
        "rejection_reason": None,
    }

    return {
        "investigation_id": result.investigation_id,
        "incident_id": incident_id,
        "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
        "source": result.source,
        "summary": result.summary,
        "confidence": result.confidence.value if hasattr(result.confidence, 'value') else str(result.confidence),
        "root_cause": result.root_cause,
        "hypotheses": hypotheses,
        "evidence": evidence_items,
        "evidence_count": result.evidence_count,
        "retrieved_sources": retrieved_sources,
        "retrieval_status": retrieval_status,
        "remediation": remediation,
        "budget_consumed": result.budget_consumed.model_dump() if hasattr(result.budget_consumed, 'model_dump') else {},
        "started_at": result.started_at.isoformat() if result.started_at else now.isoformat(),
        "completed_at": result.completed_at.isoformat() if result.completed_at else now.isoformat(),
        "error_message": result.error_message,
        "is_simulated": False,
    }


def _run_investigation(incident_id: str, db: Session, force: bool = False) -> Dict[str, Any]:
    """Execute the investigation pipeline for an incident.
    
    Uses the real InvestigationPipeline when available, falls back to
    a structured demo result with clear 'simulated' labeling.
    """
    now = datetime.now(timezone.utc)
    inv_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
    
    # Try to load incident from database
    incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found in database",
        )

    incident_title = incident.title
    incident_service = incident.service
    incident_summary = incident.summary

    # Try real pipeline
    try:
        from backend.app.investigation.orchestrator import InvestigationPipeline
        
        pipeline = InvestigationPipeline(db=db)
        result = pipeline.run({
            "id": incident_id,
            "incident_id": incident_id,
            "service": incident_service,
            "title": incident_title,
            "summary": incident_summary,
            "severity": getattr(incident, 'severity', 'HIGH'),
            "force": force,
        }, force=force)
        
        # Check existing remediation in DB if any
        existing_rem = None
        inv_model_check = db.query(InvestigationModel).filter(InvestigationModel.incident_id == incident_id).first()
        if inv_model_check and inv_model_check.evaluation:
            existing_rem = inv_model_check.evaluation.get("remediation")

        inv_data = _format_pipeline_result(result, incident_id, incident_service, now, existing_remediation=existing_rem)
        
        # Persist remediation proposal into inv_model.evaluation in database
        if inv_model_check:
            eval_dict = dict(inv_model_check.evaluation or {})
            eval_dict["remediation"] = inv_data["remediation"]
            inv_model_check.evaluation = eval_dict
            flag_modified(inv_model_check, "evaluation")
            db.commit()

        _investigations[incident_id] = inv_data
        logger.info("Real investigation completed for %s: %s", incident_id, result.status)
        return inv_data

    except Exception as exc:
        logger.warning(
            "Investigation pipeline unavailable for %s, using structured demo: %s",
            incident_id, exc,
        )
        
        # Structured demo fallback with clear labeling
        inv_data = {
            "investigation_id": inv_id,
            "incident_id": incident_id,
            "status": "COMPLETED",
            "source": "demo_fallback",
            "summary": f"[SIMULATED] Investigation of '{incident_title}' affecting {incident_service}. "
                       f"The pipeline detected anomalies consistent with the reported alert. "
                       f"Root cause analysis suggests service degradation in the {incident_service} component.",
            "confidence": "MEDIUM",
            "root_cause": f"{incident_service}_degradation",
            "hypotheses": [
                {
                    "id": "h1",
                    "rank": 1,
                    "title": f"{incident_service.title()} Service Degradation",
                    "root_cause": f"{incident_service}_service_degradation",
                    "score": 72.0,
                    "likelihood": "LIKELY",
                    "causal_explanation": f"[SIMULATED] Elevated error rates and latency spikes in the {incident_service} "
                                         f"service correlate with the reported incident timeframe.",
                    "supporting_evidence": ["error_rate_spike", "latency_p95_increase"],
                    "contradicting_evidence": [],
                    "affected_service": incident_service,
                },
                {
                    "id": "h2",
                    "rank": 2,
                    "title": "Upstream Dependency Timeout",
                    "root_cause": "upstream_dependency_timeout",
                    "score": 45.0,
                    "likelihood": "POSSIBLE",
                    "causal_explanation": "[SIMULATED] Partial evidence of upstream service latency, but insufficient "
                                         "to confirm as primary root cause.",
                    "supporting_evidence": ["upstream_latency_increase"],
                    "contradicting_evidence": ["downstream_healthy"],
                    "affected_service": incident_service,
                },
            ],
            "evidence": [
                {
                    "id": "ev-1",
                    "type": "metric",
                    "title": "Error Rate Spike",
                    "source": "prometheus (simulated)",
                    "summary": f"[SIMULATED] {incident_service} error rate exceeded threshold",
                    "polarity": "supporting",
                    "timestamp": now.isoformat(),
                },
                {
                    "id": "ev-2",
                    "type": "log",
                    "title": "Error Log Entries",
                    "source": "loki (simulated)",
                    "summary": f"[SIMULATED] Multiple error-level log entries from {incident_service}",
                    "polarity": "supporting",
                    "timestamp": now.isoformat(),
                },
                {
                    "id": "ev-3",
                    "type": "trace",
                    "title": "Trace Latency Analysis",
                    "source": "jaeger (simulated)",
                    "summary": "[SIMULATED] Elevated span durations in request traces",
                    "polarity": "supporting",
                    "timestamp": now.isoformat(),
                },
            ],
            "evidence_count": 3,
            "retrieved_sources": [],
            "retrieval_status": "NO_DOCUMENTS_FOUND",
            "remediation": {
                "id": f"REM-{incident_id}",
                "incident_id": incident_id,
                "root_cause_title": f"{incident_service.title()} Service Degradation",
                "root_cause_description": f"[SIMULATED] Root cause analysis indicates degradation in {incident_service}",
                "action_title": f"Restart {incident_service.title()} Service Pods",
                "action_description": f"[SIMULATED] Rolling restart of {incident_service} pods to restore healthy state. "
                                      f"This action requires manual approval before execution.",
                "target_service": incident_service,
                "status": "AWAITING_APPROVAL",
                "approved_by": None,
                "approved_at": None,
                "rejection_reason": None,
            },
            "budget_consumed": {"steps": 4, "llm_calls": 0, "tool_calls": 3, "evidence_items": 3},
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "error_message": None,
            "is_simulated": True,
        }

        _investigations[incident_id] = inv_data
        return inv_data


# ==========================================================================
# Endpoints
# ==========================================================================

@router.post(
    "/trigger",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger an AI investigation on an incident",
)
def trigger_investigation(
    req: InvestigationTriggerRequest,
    db: Session = Depends(get_db),
) -> InvestigationResponse:
    """Start an AI-powered investigation for the given incident ID."""
    # Check for existing investigation in memory
    if req.incident_id in _investigations and not req.force:
        existing = _investigations[req.incident_id]
        return InvestigationResponse(**existing)

    result = _run_investigation(req.incident_id, db, force=req.force)
    return InvestigationResponse(**result)


# ==========================================================================
# Audit Log Endpoint (placed before /{incident_id} to prevent path shadowing)
# ==========================================================================

@router.get(
    "/audit/log",
    response_model=List[AuditLogEntry],
    summary="Get audit trail of all remediation actions",
)
def get_audit_log(
    incident_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> List[AuditLogEntry]:
    """Retrieve persistent audit trail of all approval/rejection actions."""
    query = db.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc())
    if incident_id:
        query = query.filter(AuditLogModel.incident_id == incident_id)
    if action:
        query = query.filter(AuditLogModel.action == action)
    db_entries = query.offset(offset).limit(limit).all()

    results: List[AuditLogEntry] = []
    seen_ids = set()
    for row in db_entries:
        seen_ids.add(row.id)
        results.append(
            AuditLogEntry(
                id=row.id,
                timestamp=row.timestamp.isoformat() if hasattr(row.timestamp, "isoformat") else str(row.timestamp),
                action=row.action,
                actor=row.actor,
                investigation_id=row.investigation_id,
                incident_id=row.incident_id,
                proposal_id=row.proposal_id,
                reason=row.reason,
                details=row.details,
            )
        )

    # Include any in-memory items not yet in DB (fallback cache)
    for entry in reversed(_audit_log):
        if entry["id"] not in seen_ids:
            if incident_id and entry.get("incident_id") != incident_id:
                continue
            if action and entry.get("action") != action:
                continue
            results.append(AuditLogEntry(**entry))

    return results


@router.get(
    "/{incident_id}",
    response_model=InvestigationResponse,
    summary="Get investigation results for an incident",
)
def get_investigation(
    incident_id: str,
    db: Session = Depends(get_db),
) -> InvestigationResponse:
    """Retrieve the investigation results for a specific incident."""
    # Check PostgreSQL database for persisted investigation
    from backend.app.investigation.orchestrator import InvestigationPipeline

    inv_model = db.query(InvestigationModel).filter(InvestigationModel.incident_id == incident_id).first()
    if inv_model:
        incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
        incident_service = incident.service if incident else "unknown"
        pipeline = InvestigationPipeline(db=db)
        result = pipeline._build_result_from_model(inv_model)

        eval_dict = dict(inv_model.evaluation or {})
        existing_rem = eval_dict.get("remediation")
        if not existing_rem:
            # Check if cached in memory
            if incident_id in _investigations and _investigations[incident_id].get("remediation"):
                existing_rem = _investigations[incident_id]["remediation"]
            else:
                existing_rem = {
                    "id": f"REM-{incident_id}",
                    "incident_id": incident_id,
                    "root_cause_title": result.root_cause or "Service Degradation",
                    "root_cause_description": result.summary,
                    "action_title": f"Remediate {result.root_cause or 'incident'}",
                    "action_description": f"Apply recommended fix based on investigation findings for {incident_service}",
                    "target_service": incident_service,
                    "status": "AWAITING_APPROVAL",
                    "approved_by": None,
                    "approved_at": None,
                    "rejection_reason": None,
                }
            eval_dict["remediation"] = existing_rem
            inv_model.evaluation = eval_dict
            flag_modified(inv_model, "evaluation")
            db.commit()

        inv_data = _format_pipeline_result(
            result, incident_id, incident_service, datetime.now(timezone.utc), existing_remediation=existing_rem
        )
        _investigations[incident_id] = inv_data
        return InvestigationResponse(**inv_data)

    if incident_id in _investigations:
        return InvestigationResponse(**_investigations[incident_id])

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No investigation found for incident '{incident_id}'. Trigger one first via POST /api/investigations/trigger",
    )


@router.post(
    "/{incident_id}/approve",
    response_model=RemediationResponse,
    summary="Approve or reject a remediation proposal",
)
def approve_remediation(
    incident_id: str,
    req: ApprovalRequest,
    db: Session = Depends(get_db),
) -> RemediationResponse:
    """Approve or reject the remediation proposal for an investigation.
    
    Guarantees:
    - Input validation: action must be 'approve' or 'reject'.
    - Safety: records human decision; never executes destructive commands or mutates production.
    - Idempotency: duplicate approvals or rejections return existing decision without creating duplicate audit events.
    - State transition validation: cannot approve an already rejected proposal or reject an already approved proposal.
    - Persistence: decision and audit log are atomically committed to PostgreSQL.
    """
    if req.action not in ("approve", "reject"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve' or 'reject'",
        )

    # Check incident & investigation existence
    incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
    inv_model = db.query(InvestigationModel).filter(InvestigationModel.incident_id == incident_id).first()

    if not incident and not inv_model and incident_id not in _investigations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident or investigation '{incident_id}' not found",
        )

    # Extract remediation proposal
    remediation: Optional[Dict[str, Any]] = None
    if inv_model and inv_model.evaluation:
        remediation = dict(inv_model.evaluation.get("remediation") or {})
    
    if not remediation and incident_id in _investigations:
        remediation = dict(_investigations[incident_id].get("remediation") or {})

    if not remediation:
        if inv_model:
            incident_service = incident.service if incident else "unknown"
            remediation = {
                "id": f"REM-{incident_id}",
                "incident_id": incident_id,
                "root_cause_title": inv_model.root_cause or "Service Degradation",
                "root_cause_description": f"Root cause analysis for {incident_id}",
                "action_title": f"Remediate {inv_model.root_cause or 'incident'}",
                "action_description": f"Apply recommended fix based on investigation findings for {incident_service}",
                "target_service": incident_service,
                "status": "AWAITING_APPROVAL",
                "approved_by": None,
                "approved_at": None,
                "rejection_reason": None,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No remediation proposal exists for this investigation",
            )

    current_status = remediation.get("status", "AWAITING_APPROVAL")

    # Validate state transitions & enforce idempotency
    if current_status == "APPROVED":
        if req.action == "approve":
            # Idempotent repeated approval: do not create duplicate audit log
            logger.info("Idempotent repeated approval for %s by %s", incident_id, req.approved_by)
            return RemediationResponse(**remediation)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remediation proposal has already been approved and cannot be rejected",
            )
    elif current_status == "REJECTED":
        if req.action == "reject":
            # Idempotent repeated rejection: do not create duplicate audit log
            logger.info("Idempotent repeated rejection for %s by %s", incident_id, req.approved_by)
            return RemediationResponse(**remediation)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remediation proposal has already been rejected and cannot be approved",
            )

    now = datetime.now(timezone.utc)
    if req.action == "approve":
        remediation["status"] = "APPROVED"
        remediation["approved_by"] = req.approved_by
        remediation["approved_at"] = now.isoformat()
        remediation["rejection_reason"] = None
        audit_action = "REMEDIATION_APPROVED"
    else:
        remediation["status"] = "REJECTED"
        remediation["approved_by"] = req.approved_by
        remediation["approved_at"] = None
        remediation["rejection_reason"] = req.reason or "Rejected by operator"
        audit_action = "REMEDIATION_REJECTED"

    # Persist in DB transaction
    audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
    inv_id = inv_model.id if inv_model else (_investigations.get(incident_id, {}).get("investigation_id", f"INV-{incident_id}"))
    proposal_id = remediation.get("id", f"REM-{incident_id}")

    audit_details = (
        f"Remediation proposal {proposal_id} ({remediation.get('action_title', '')}) "
        f"was {req.action}d by {req.approved_by}."
    )
    if req.reason:
        audit_details += f" Reason: {req.reason}"

    audit_entry = AuditLogModel(
        id=audit_id,
        timestamp=now,
        action=audit_action,
        actor=req.approved_by,
        investigation_id=inv_id,
        incident_id=incident_id,
        proposal_id=proposal_id,
        reason=req.reason,
        details=audit_details,
    )
    db.add(audit_entry)

    if inv_model:
        eval_dict = dict(inv_model.evaluation or {})
        eval_dict["remediation"] = remediation
        inv_model.evaluation = eval_dict
        flag_modified(inv_model, "evaluation")
        inv_model.updated_at = now

    db.commit()
    if inv_model:
        db.refresh(inv_model)

    # Sync in-memory cache
    if incident_id in _investigations:
        _investigations[incident_id]["remediation"] = remediation

    _audit_log.append({
        "id": audit_id,
        "timestamp": now.isoformat(),
        "action": audit_action,
        "actor": req.approved_by,
        "investigation_id": inv_id,
        "incident_id": incident_id,
        "proposal_id": proposal_id,
        "reason": req.reason,
        "details": audit_details,
    })

    logger.info("Audit: %s for %s by %s", audit_action, incident_id, req.approved_by)
    return RemediationResponse(**remediation)


@router.get(
    "",
    response_model=List[InvestigationResponse],
    summary="List all investigations",
)
def list_investigations() -> List[InvestigationResponse]:
    """Retrieve all investigations."""
    return [InvestigationResponse(**inv) for inv in _investigations.values()]
