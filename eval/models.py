"""Data models for Sherlog Evaluation Benchmark Scenarios and Results."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.baseline.models import EvidenceItem


class BenchmarkScenario(BaseModel):
    """Definition of a benchmark incident scenario with ground truth."""

    scenario_id: str = Field(..., description="Unique scenario ID, e.g. SCN-001")
    fault_id: str = Field(..., description="Fault scenario identifier, e.g. db_pool_exhaustion")
    name: str = Field(..., description="Descriptive scenario name")
    description: str = Field(..., description="Contextual scenario description")
    service: str = Field(..., description="Primary affected service")
    expected_root_cause: str = Field(..., description="Ground truth root cause identifier")
    expected_remediations: List[str] = Field(
        default_factory=list,
        description="List of allowlisted remediation actions considered valid",
    )
    incident: Dict[str, Any] = Field(..., description="Incident payload (title, summary, metadata, etc.)")
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Observability evidence items collected during incident",
    )
    expect_insufficient_evidence: bool = Field(
        default=False,
        description="True for edge cases where the correct answer is to decline diagnosis due to lack of evidence",
    )


class ScenarioEvaluationResult(BaseModel):
    """Result of evaluating a single scenario against an investigator."""

    scenario_id: str
    name: str
    fault_id: str
    expected_root_cause: str
    predicted_root_cause: Optional[str] = None
    ranked_hypotheses: List[str] = Field(default_factory=list)
    top_1_match: bool
    top_3_match: bool
    confidence: str
    score: float
    evidence_count: int
    supporting_evidence: List[str] = Field(default_factory=list)
    recommended_remediation: Optional[str] = None
    passed: bool
    failure_reason: Optional[str] = None
    execution_time_ms: float


class EvaluationRunReport(BaseModel):
    """Comprehensive evaluation summary across all benchmark scenarios."""

    run_id: str
    timestamp: str
    evaluator_name: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    top_1_accuracy: float = Field(..., description="Percentage of scenarios where Top-1 hypothesis matches ground truth")
    top_3_accuracy: float = Field(..., description="Percentage of scenarios where ground truth is in Top-3 hypotheses")
    avg_latency_ms: float
    results: List[ScenarioEvaluationResult]
    failed_cases: List[ScenarioEvaluationResult]
