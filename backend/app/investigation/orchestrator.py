"""Investigation Pipeline orchestrating the bounded AI agent loop and state machine.

Workflow:
Incident -> Evidence Collection -> Hypothesis Generation -> Evidence Evaluation ->
Root Cause Assessment -> Persisted Investigation Result
"""

from datetime import datetime, timedelta, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from backend.app.baseline.models import (
    ConfidenceLevel,
    EvidenceItem,
    EvidenceType,
    HypothesisRanking,
    InvestigationReport,
)
from backend.app.config import settings
from backend.app.investigation.router import InvestigationRouter
from backend.app.db.models.investigation import (
    InvestigationCheckpointModel,
    InvestigationModel,
)
from backend.app.investigation.evaluator import DeterministicEvaluator
from backend.app.investigation.evidence import EvidenceCollector
from backend.app.investigation.generator import HypothesisGenerator
from backend.app.investigation.rag import KnowledgeRetriever
from backend.app.investigation.schemas import (
    BudgetConsumption,
    ExecutionBudget,
    HypothesisProposal,
    InvestigationResult,
    RetrievedSourceItem,
)
from backend.app.investigation.states import (
    TERMINAL_STATES,
    InvestigationState,
    validate_transition,
)
from backend.app.schemas.incident import IncidentResponse

logger = logging.getLogger(__name__)


def _sanitize_error(error: Exception) -> str:
    """Sanitize error message to prevent accidental secret or credential leakage."""
    msg = str(error)
    # Redact common credential patterns
    import re
    msg = re.sub(r"(gsk_[A-Za-z0-9_-]+)", "[REDACTED_API_KEY]", msg)
    msg = re.sub(r"(Bearer\s+[A-Za-z0-9._-]+)", "Bearer [REDACTED]", msg)
    msg = re.sub(r"(password|secret|key)=\S+", r"\1=[REDACTED]", msg, flags=re.IGNORECASE)
    return msg[:500]


class InvestigationPipeline:
    """Orchestrates Sherlog's bounded investigation pipeline with PostgreSQL checkpointing."""

    def __init__(
        self,
        db: Session,
        budget: Optional[ExecutionBudget] = None,
        evaluator: Optional[DeterministicEvaluator] = None,
        generator: Optional[HypothesisGenerator] = None,
        evidence_collector: Optional[EvidenceCollector] = None,
        retriever: Optional[KnowledgeRetriever] = None,
    ):
        self.db = db
        self.budget = budget or ExecutionBudget()
        self.evaluator = evaluator or DeterministicEvaluator()
        self.generator = generator or HypothesisGenerator()
        self.evidence_collector = evidence_collector or EvidenceCollector()
        self.retriever = retriever or KnowledgeRetriever(
            db=self.db,
            vector_enabled=settings.RAG_ENABLED,
        )
        self.router = InvestigationRouter()

    def run(
        self,
        incident: Union[IncidentResponse, Dict[str, Any]],
        force: bool = False,
    ) -> InvestigationResult:
        """Execute bounded incident investigation pipeline.
        
        Guarantees:
        1. Safe retries & idempotency: will not rerun already-completed investigations unless force=True.
        2. Bounded execution limits (steps, tokens, tools, duration).
        3. Strict state transition validation.
        4. Durable PostgreSQL checkpoints on each transition.
        5. Safe deterministic fallback if LLM is unavailable.
        """
        start_time = time.time()
        incident_dict = incident.model_dump() if isinstance(incident, IncidentResponse) else dict(incident)
        incident_id = incident_dict.get("id") or incident_dict.get("incident_id")
        if not incident_id:
            raise ValueError("Incident missing mandatory identifier ('id' or 'incident_id')")

        consumption = BudgetConsumption(
            steps=0,
            llm_calls=0,
            tool_calls=0,
            evidence_items=0,
            tokens_used=0,
            duration_seconds=0.0,
        )

        is_force = force or bool(incident_dict.get("force", False))

        # 1. Idempotency & Duplicate Delivery Check
        existing = (
            self.db.query(InvestigationModel)
            .filter(InvestigationModel.incident_id == incident_id)
            .first()
        )
        is_stale = False

        if existing and existing.state in {s.value for s in TERMINAL_STATES} and not is_force:
            logger.info(
                "Incident %s has already been investigated (terminal state: %s). Returning existing result.",
                incident_id,
                existing.state,
            )
            return self._build_result_from_model(existing, termination_reason="Already investigated (idempotent)")

        if (
            existing
            and existing.state not in {InvestigationState.QUEUED.value}
            and existing.state not in {s.value for s in TERMINAL_STATES}
            and not is_force
        ):
            started_at = existing.started_at
            if started_at is None:
                is_stale = True
            else:
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                is_stale = datetime.now(timezone.utc) - started_at > timedelta(
                    seconds=self.budget.max_seconds
                )

            if not is_stale:
                logger.info(
                    "Incident %s already has a fresh in-progress investigation (state: %s); not starting a duplicate run.",
                    incident_id,
                    existing.state,
                )
                return self._build_result_from_model(
                    existing,
                    termination_reason="Investigation already in progress; duplicate trigger was ignored.",
                )

            logger.warning(
                "Recovering stale investigation for incident %s (state: %s, started_at: %s).",
                incident_id,
                existing.state,
                existing.started_at,
            )

        # 2. Initialize or Resume Investigation Record
        inv_id = f"INV-{incident_id}"
        if not existing:
            inv_model = InvestigationModel(
                id=inv_id,
                incident_id=incident_id,
                state=InvestigationState.QUEUED.value,
                current_step=0,
                evidence=[],
                hypotheses=[],
                evaluation={},
                root_cause=None,
                investigation_source="llm",
                tool_executions=[],
                budget_consumed=consumption.model_dump(),
                started_at=datetime.now(timezone.utc),
            )
            self.db.add(inv_model)
            self.db.commit()
            self.db.refresh(inv_model)
            self._save_checkpoint(inv_model, step=0, snapshot={"status": "initialized"})
        else:
            inv_model = existing
            if is_force or is_stale:
                inv_model.state = InvestigationState.QUEUED.value
                inv_model.current_step = 0
                inv_model.evidence = []
                inv_model.hypotheses = []
                inv_model.evaluation = {}
                inv_model.root_cause = None
                inv_model.investigation_source = "llm"
                inv_model.tool_executions = []
                inv_model.budget_consumed = consumption.model_dump()
                inv_model.started_at = datetime.now(timezone.utc)
                inv_model.completed_at = None
                inv_model.error_message = None
                self.db.commit()
                self._save_checkpoint(
                    inv_model,
                    step=0,
                    snapshot={
                        "status": "re-initialized",
                        "force": is_force,
                        "recovered_stale_run": is_stale and not is_force,
                    },
                )
            else:
                logger.info("Resuming non-terminal investigation %s from state %s", inv_id, inv_model.state)

        evidence_items: List[EvidenceItem] = []
        hypotheses: List[HypothesisProposal] = []
        tool_logs: List[Dict[str, Any]] = []
        investigation_source = "llm"
        termination_reason: Optional[str] = None

        try:
            # ==================================================================
            # STEP 1: COLLECTING_EVIDENCE
            # ==================================================================
            self._transition(inv_model, InvestigationState.COLLECTING_EVIDENCE, consumption)
            evidence_items, tool_logs = self.evidence_collector.collect_for_incident(
                incident=incident_dict,
                budget=self.budget,
                consumption=consumption,
            )
            consumption.evidence_items = len(evidence_items)
            consumption.duration_seconds = time.time() - start_time

            serialized_evidence = [
                {
                    "source": e.source.value,
                    "name": e.name,
                    "value": e.value,
                    "service": e.service,
                    "description": e.description,
                    "timestamp": e.timestamp if isinstance(e.timestamp, str) else (e.timestamp.isoformat() if e.timestamp else None),
                }
                for e in evidence_items
            ]
            inv_model.evidence = serialized_evidence
            inv_model.tool_executions = tool_logs
            inv_model.budget_consumed = consumption.model_dump()
            self.db.commit()
            self._save_checkpoint(
                inv_model,
                step=inv_model.current_step,
                snapshot={
                    "evidence_count": len(evidence_items),
                    "tool_executions": len(tool_logs),
                },
            )

            # Check budget
            exceeded, reason = consumption.check_exceeded(self.budget)
            if exceeded:
                termination_reason = reason
                return self._finalize_with_insufficient_evidence(
                    inv_model,
                    evidence_items,
                    tool_logs,
                    consumption,
                    start_time,
                    investigation_source,
                    termination_reason=termination_reason,
                )

            # ==================================================================
            # STEP 2: GENERATING_HYPOTHESES (with Baseline Fallback)
            # ==================================================================
            self._transition(inv_model, InvestigationState.GENERATING_HYPOTHESES, consumption)

            # Vector RAG retrieval (non-blocking, fails safely)
            rag_result = self.retriever.retrieve_similar_incidents(
                service_name=incident_dict.get("service", "unknown"),
                incident_title=incident_dict.get("title", ""),
                max_results=3,
            )

            retrieved_sources: List[RetrievedSourceItem] = []
            if not rag_result.is_vector_enabled:
                if rag_result.vector_backend in {"db_error", "embedding_error"}:
                    retrieval_status = "FAILED"
                else:
                    retrieval_status = "DISABLED"
            elif not rag_result.documents:
                retrieval_status = "NO_DOCUMENTS_FOUND"
            else:
                retrieval_status = "SUCCESS"

            # Check if LLM hypothesis generation will actually be attempted (budget guards)
            will_attempt_llm = (
                consumption.llm_calls < self.budget.max_llm_calls
                and consumption.tokens_used < self.budget.max_tokens
            )

            # Record retrieved runbook sources in evidence items, structured sources, and tool logs
            if rag_result.documents:
                for idx, doc in enumerate(rag_result.documents):
                    # Top 3 docs are passed into generator prompt if LLM is called
                    is_included = will_attempt_llm and (idx < 3)
                    why_rel = (
                        f"Matched query '{rag_result.query}' with similarity {doc.similarity_score:.2f} "
                        f"for service '{incident_dict.get('service', 'unknown')}'; contains operational guidance for {doc.title}."
                    )
                    source_item = RetrievedSourceItem(
                        doc_id=doc.doc_id,
                        chunk_id=doc.chunk_id,
                        title=doc.title,
                        source=doc.source,
                        service=doc.service,
                        excerpt=doc.content,
                        similarity_score=doc.similarity_score,
                        rank=idx + 1,
                        included_in_context=is_included,
                        why_relevant=why_rel,
                    )
                    retrieved_sources.append(source_item)

                    evidence_items.append(
                        EvidenceItem(
                            source=EvidenceType.CONFIG,
                            name=f"runbook:{doc.doc_id}",
                            value=f"{doc.title} (similarity: {doc.similarity_score:.2f})",
                            service=doc.service,
                            description=f"Retrieved operational guidance from {doc.source}",
                            timestamp=datetime.now(timezone.utc),
                        )
                    )

            tool_logs.append({
                "tool": "KnowledgeRetriever",
                "query": rag_result.query,
                "status": retrieval_status,
                "retrieved_count": len(rag_result.documents),
                "vector_backend": rag_result.vector_backend,
                "sources": [s.model_dump() for s in retrieved_sources],
                "result": [s.model_dump() for s in retrieved_sources],
            })

            # Attempt LLM hypothesis generation with retrieved context
            proposals, llm_err = self.generator.generate_hypotheses(
                incident=incident_dict,
                evidence=evidence_items,
                budget=self.budget,
                consumption=consumption,
                retrieved_docs=rag_result.documents,
            )

            if proposals:
                hypotheses = proposals
                investigation_source = "llm"
            else:
                logger.warning(
                    "LLM hypothesis generation failed or unavailable (%s). Falling back to deterministic baseline.",
                    llm_err,
                )
                investigation_source = "baseline_fallback"
                baseline_report: InvestigationReport = self.evaluator.evaluate_with_baseline_fallback(
                    incident=incident_dict,
                    evidence=evidence_items,
                )
                # Convert baseline hypotheses to proposals
                hypotheses = [
                    HypothesisProposal(
                        root_cause=h.root_cause,
                        title=h.title,
                        affected_service=incident_dict.get("service"),
                        supporting_evidence_refs=h.supporting_evidence,
                        contradicting_evidence_refs=[],
                        uncertainty=None,
                        causal_explanation=f"Rule-based match: {', '.join(h.matched_rules)}",
                    )
                    for h in baseline_report.ranked_root_causes
                ]

            consumption.duration_seconds = time.time() - start_time
            inv_model.hypotheses = [h.model_dump() for h in hypotheses]
            inv_model.investigation_source = investigation_source
            inv_model.tool_executions = tool_logs
            inv_model.budget_consumed = consumption.model_dump()
            self.db.commit()
            self._save_checkpoint(
                inv_model,
                step=inv_model.current_step,
                snapshot={
                    "hypotheses_count": len(hypotheses),
                    "source": investigation_source,
                    "rag_enabled": rag_result.is_vector_enabled,
                    "retrieved_sources_count": len(retrieved_sources),
                },
            )

            # Check budget
            exceeded, reason = consumption.check_exceeded(self.budget)
            if exceeded:
                termination_reason = reason
                return self._finalize_with_insufficient_evidence(
                    inv_model,
                    evidence_items,
                    tool_logs,
                    consumption,
                    start_time,
                    investigation_source,
                    retrieved_sources=retrieved_sources,
                    retrieval_status=retrieval_status,
                    termination_reason=termination_reason,
                )

            # ==================================================================
            # STEP 3: EVALUATING_HYPOTHESES (Deterministic Scoring)
            # ==================================================================
            self._transition(inv_model, InvestigationState.EVALUATING_HYPOTHESES, consumption)

            ranked_hypotheses, has_sufficient_evidence, top_cause, rationale = (
                self.evaluator.evaluate_hypotheses(
                    hypotheses=hypotheses,
                    evidence=evidence_items,
                )
            )

            consumption.duration_seconds = time.time() - start_time
            evaluation_summary = {
                "has_sufficient_evidence": has_sufficient_evidence,
                "top_cause": top_cause.model_dump() if top_cause else None,
                "rationale": rationale,
                "ranked_count": len(ranked_hypotheses),
                "retrieved_sources": [s.model_dump() for s in retrieved_sources],
                "retrieval_status": retrieval_status,
            }
            inv_model.evaluation = evaluation_summary
            inv_model.tool_executions = tool_logs
            inv_model.budget_consumed = consumption.model_dump()
            self.db.commit()

            # ==================================================================
            # STEP 4: FINAL STATE DECISION (COMPLETED or INSUFFICIENT_EVIDENCE)
            # ==================================================================
            if has_sufficient_evidence and top_cause:
                self._transition(inv_model, InvestigationState.COMPLETED, consumption)
                inv_model.root_cause = top_cause.root_cause
                final_summary = rationale
                final_confidence = top_cause.confidence
            else:
                self._transition(inv_model, InvestigationState.INSUFFICIENT_EVIDENCE, consumption)
                inv_model.root_cause = None
                final_summary = rationale
                final_confidence = ConfidenceLevel.INSUFFICIENT_EVIDENCE

            inv_model.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            self._save_checkpoint(
                inv_model,
                step=inv_model.current_step,
                snapshot={
                    "final_state": inv_model.state,
                    "root_cause": inv_model.root_cause,
                },
            )

            return InvestigationResult(
                incident_id=incident_id,
                investigation_id=inv_model.id,
                status=InvestigationState(inv_model.state),
                has_sufficient_evidence=has_sufficient_evidence,
                root_cause=inv_model.root_cause,
                confidence=final_confidence,
                ranked_hypotheses=ranked_hypotheses,
                evidence_count=len(evidence_items),
                evidence_references=[f"{e.source.value}: {e.name}" for e in evidence_items],
                retrieved_sources=retrieved_sources,
                retrieval_status=retrieval_status,
                tool_executions=tool_logs,
                budget_consumed=consumption,
                source=investigation_source,
                summary=final_summary,
                started_at=inv_model.started_at,
                completed_at=inv_model.completed_at,
                termination_reason=termination_reason,
            )

        except Exception as exc:
            sanitized_err = _sanitize_error(exc)
            logger.error("Investigation pipeline failed for incident %s: %s", incident_id, sanitized_err, exc_info=True)
            self._handle_pipeline_failure(inv_model, sanitized_err, consumption)
            return InvestigationResult(
                incident_id=incident_id,
                investigation_id=inv_model.id,
                status=InvestigationState.FAILED,
                has_sufficient_evidence=False,
                root_cause=None,
                confidence=ConfidenceLevel.INSUFFICIENT_EVIDENCE,
                ranked_hypotheses=[],
                evidence_count=len(evidence_items),
                evidence_references=[f"{e.source.value}: {e.name}" for e in evidence_items],
                tool_executions=tool_logs,
                budget_consumed=consumption,
                source=investigation_source,
                summary=f"Investigation failed: {sanitized_err}",
                started_at=inv_model.started_at,
                completed_at=datetime.now(timezone.utc),
                error_message=sanitized_err,
            )

    def _transition(
        self,
        model: InvestigationModel,
        target_state: InvestigationState,
        consumption: BudgetConsumption,
    ) -> None:
        """Enforce transition validation, update step and model state, and persist to PostgreSQL."""
        current_state = InvestigationState(model.state)
        validate_transition(current_state, target_state)
        consumption.steps += 1
        model.state = target_state.value
        model.current_step = consumption.steps
        self.db.commit()

    def _save_checkpoint(
        self,
        model: InvestigationModel,
        step: int,
        snapshot: Dict[str, Any],
    ) -> None:
        """Persist durable investigation checkpoint to database."""
        try:
            checkpoint = InvestigationCheckpointModel(
                investigation_id=model.id,
                incident_id=model.incident_id,
                step=step,
                state=model.state,
                snapshot=snapshot,
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(checkpoint)
            self.db.commit()
        except Exception as cp_err:
            logger.warning("Failed to save investigation checkpoint: %s", cp_err)

    def _handle_pipeline_failure(
        self,
        model: InvestigationModel,
        sanitized_error: str,
        consumption: BudgetConsumption,
    ) -> None:
        """Mark investigation as FAILED and record error safely."""
        try:
            model.state = InvestigationState.FAILED.value
            model.error_message = sanitized_error
            model.completed_at = datetime.now(timezone.utc)
            model.budget_consumed = consumption.model_dump()
            self.db.commit()
            self._save_checkpoint(
                model,
                step=model.current_step + 1,
                snapshot={"failure_error": sanitized_error},
            )
        except Exception as fail_err:
            logger.critical("Failed to persist investigation FAILED state: %s", fail_err)

    def _finalize_with_insufficient_evidence(
        self,
        model: InvestigationModel,
        evidence: List[EvidenceItem],
        tool_logs: List[Dict[str, Any]],
        consumption: BudgetConsumption,
        start_time: float,
        source: str,
        retrieved_sources: Optional[List[RetrievedSourceItem]] = None,
        retrieval_status: str = "NOT_ATTEMPTED",
        termination_reason: Optional[str] = None,
    ) -> InvestigationResult:
        """Terminate early with INSUFFICIENT_EVIDENCE when budget is breached."""
        current_state = InvestigationState(model.state)
        if current_state not in TERMINAL_STATES:
            # Transition to INSUFFICIENT_EVIDENCE
            if current_state in {InvestigationState.QUEUED}:
                # Transition via COLLECTING_EVIDENCE
                validate_transition(current_state, InvestigationState.COLLECTING_EVIDENCE)
                model.state = InvestigationState.COLLECTING_EVIDENCE.value
                current_state = InvestigationState.COLLECTING_EVIDENCE

            validate_transition(current_state, InvestigationState.INSUFFICIENT_EVIDENCE)
            model.state = InvestigationState.INSUFFICIENT_EVIDENCE.value

        consumption.duration_seconds = time.time() - start_time
        model.completed_at = datetime.now(timezone.utc)
        model.budget_consumed = consumption.model_dump()
        self.db.commit()
        self._save_checkpoint(
            model,
            step=model.current_step,
            snapshot={"status": "terminated_early", "reason": termination_reason},
        )

        return InvestigationResult(
            incident_id=model.incident_id,
            investigation_id=model.id,
            status=InvestigationState.INSUFFICIENT_EVIDENCE,
            has_sufficient_evidence=False,
            root_cause=None,
            confidence=ConfidenceLevel.INSUFFICIENT_EVIDENCE,
            ranked_hypotheses=[],
            evidence_count=len(evidence),
            evidence_references=[f"{e.source.value}: {e.name}" for e in evidence],
            retrieved_sources=retrieved_sources or [],
            retrieval_status=retrieval_status,
            tool_executions=tool_logs,
            budget_consumed=consumption,
            source=source,
            summary=f"Investigation stopped: {termination_reason or 'Insufficient evidence'}",
            started_at=model.started_at,
            completed_at=model.completed_at,
            termination_reason=termination_reason,
        )

    def _build_result_from_model(
        self,
        model: InvestigationModel,
        termination_reason: Optional[str] = None,
    ) -> InvestigationResult:
        """Reconstruct InvestigationResult from a persisted database model."""
        eval_dict = model.evaluation or {}
        has_sufficient = bool(eval_dict.get("has_sufficient_evidence", False))
        top_cause = eval_dict.get("top_cause")
        conf_str = top_cause.get("confidence", "INSUFFICIENT_EVIDENCE") if top_cause else "INSUFFICIENT_EVIDENCE"
        try:
            confidence = ConfidenceLevel(conf_str)
        except Exception:
            confidence = ConfidenceLevel.INSUFFICIENT_EVIDENCE

        ranked_hypotheses = []
        if top_cause:
            try:
                ranked_hypotheses.append(HypothesisRanking(**top_cause))
            except Exception:
                pass

        evidence_list = model.evidence or []
        evidence_refs = [f"{e.get('source')}: {e.get('name')}" for e in evidence_list if isinstance(e, dict)]

        try:
            budget_consumed = BudgetConsumption(**(model.budget_consumed or {}))
        except Exception:
            budget_consumed = BudgetConsumption()

        # Reconstruct retrieved sources from evaluation summary or tool logs
        raw_sources = eval_dict.get("retrieved_sources", [])
        retrieval_status = eval_dict.get("retrieval_status")

        if not raw_sources:
            for tool_exec in (model.tool_executions or []):
                if tool_exec.get("tool") in ("KnowledgeRetriever", "knowledge_retrieval"):
                    raw_sources = tool_exec.get("sources") or tool_exec.get("result", [])
                    if not retrieval_status:
                        retrieval_status = tool_exec.get("status")
                    break

        retrieved_sources: List[RetrievedSourceItem] = []
        for s in raw_sources:
            try:
                retrieved_sources.append(RetrievedSourceItem(**s) if isinstance(s, dict) else s)
            except Exception:
                pass

        if not retrieval_status:
            retrieval_status = "SUCCESS" if retrieved_sources else "NOT_ATTEMPTED"

        return InvestigationResult(
            incident_id=model.incident_id,
            investigation_id=model.id,
            status=InvestigationState(model.state),
            has_sufficient_evidence=has_sufficient,
            root_cause=model.root_cause,
            confidence=confidence,
            ranked_hypotheses=ranked_hypotheses,
            evidence_count=len(evidence_list),
            evidence_references=evidence_refs,
            retrieved_sources=retrieved_sources,
            retrieval_status=retrieval_status,
            tool_executions=model.tool_executions or [],
            budget_consumed=budget_consumed,
            source=model.investigation_source or "llm",
            summary=eval_dict.get("rationale") or f"Investigation status: {model.state}",
            started_at=model.started_at,
            completed_at=model.completed_at,
            termination_reason=termination_reason,
            error_message=model.error_message,
        )
