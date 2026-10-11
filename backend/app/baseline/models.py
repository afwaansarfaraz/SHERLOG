"""Data models for deterministic baseline investigation and evidence handling."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """Origin telemetry type of evidence."""

    METRIC = "metric"
    LOG = "log"
    TRACE = "trace"
    ALERT = "alert"
    CONFIG = "config"


class RootCause(str, Enum):
    """Standardized root-cause identifiers matching fault taxonomy."""

    DATABASE_CONNECTION_POOL_EXHAUSTION = "database_connection_pool_exhaustion"
    SLOW_DATABASE_QUERY = "slow_database_query"
    DOWNSTREAM_DEPENDENCY_TIMEOUT = "downstream_dependency_timeout"
    SUDDEN_TRAFFIC_SPIKE = "sudden_traffic_spike"
    INVALID_SERVICE_CONFIGURATION = "invalid_service_configuration"
    MEMORY_LEAK_EXHAUSTION = "memory_leak_exhaustion"


class ConfidenceLevel(str, Enum):
    """Confidence categorization derived strictly from deterministic evidence scores."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvidenceItem(BaseModel):
    """Concrete piece of observability telemetry evidence."""

    source: EvidenceType = Field(..., description="Telemetry source category (metric, log, trace, alert, config)")
    name: str = Field(..., description="Metric name, log tag, span name, or config key")
    value: Any = Field(..., description="Scalar metric value, log line string, or status code")
    service: Optional[str] = Field(None, description="Service generating this evidence")
    description: Optional[str] = Field(None, description="Human explanation of observed signal")
    timestamp: Optional[str] = Field(None, description="Timestamp when evidence was observed")


class HypothesisRanking(BaseModel):
    """Ranked root cause candidate with deterministic evidence scoring."""

    root_cause: str = Field(..., description="Root cause identifier")
    title: str = Field(..., description="Human-readable title")
    score: float = Field(..., description="Deterministic evidence score (evidence-derived, never fabricated)")
    confidence: ConfidenceLevel = Field(..., description="Confidence category derived from score")
    matched_rules: List[str] = Field(default_factory=list, description="Names of deterministic rules that triggered")
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Verifiable evidence strings backing this hypothesis",
    )
    recommended_remediation: Optional[str] = Field(None, description="Allowlisted remediation proposal")


class InvestigationReport(BaseModel):
    """Structured, explainable output of the deterministic baseline investigator."""

    incident_id: Optional[str] = Field(None, description="Associated incident ID if available")
    service: str = Field(..., description="Primary service under investigation")
    has_sufficient_evidence: bool = Field(..., description="True if evidence meets certainty threshold")
    top_root_cause: Optional[HypothesisRanking] = Field(
        None,
        description="Highest ranked root cause (None if evidence is insufficient)",
    )
    ranked_root_causes: List[HypothesisRanking] = Field(
        default_factory=list,
        description="All evaluated hypotheses sorted descending by deterministic score",
    )
    evidence_count: int = Field(..., description="Total pieces of evidence evaluated")
    rules_evaluated: int = Field(..., description="Total deterministic rules evaluated")
    rules_matched: int = Field(..., description="Total rules that matched at least one signal")
    summary: str = Field(..., description="Plain-English explanation of the diagnostic finding")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
