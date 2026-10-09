"""Incident schemas and data validation models for Sherlog."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class IncidentSeverity(str, Enum):
    """Incident severity classification matching Case File design system."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentStatus(str, Enum):
    """Current workflow state of an incident."""

    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    RESOLVED = "RESOLVED"


class IncidentCreate(BaseModel):
    """Validation schema for incoming incident alerts."""

    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Concise description of the incident anomaly",
        examples=["Database connection pool exhaustion"],
    )
    service: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the affected service (e.g., orders, payments, api)",
        examples=["orders"],
    )
    severity: IncidentSeverity = Field(
        ...,
        description="Severity level of the incident",
        examples=["CRITICAL"],
    )
    status: IncidentStatus = Field(
        default=IncidentStatus.OPEN,
        description="Initial lifecycle status",
    )
    summary: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Detailed summary of the observed failure or alert message",
        examples=["Orders service connection pool exhausted; queries timing out."],
    )
    source: str = Field(
        default="alertmanager",
        min_length=1,
        max_length=64,
        description="Origin of the alert (e.g., alertmanager, sentry, manual)",
    )
    affected_endpoints: List[str] = Field(
        default_factory=list,
        description="List of HTTP endpoints impacted by the incident",
        examples=[["POST /orders", "GET /orders"]],
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary alert metadata, labels, PromQL queries, or annotations",
    )
    fingerprint: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Optional unique alert deduplication fingerprint",
    )

    @field_validator("title", "service", "summary", "source")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or whitespace only")
        return stripped

    @field_validator("affected_endpoints")
    @classmethod
    def validate_endpoints(cls, endpoints: List[str]) -> List[str]:
        cleaned = []
        for ep in endpoints:
            s = ep.strip()
            if s:
                cleaned.append(s)
        return cleaned


class IncidentResponse(BaseModel):
    """Public representation of an ingested incident."""

    id: str = Field(..., description="Unique incident identifier (e.g., INC-00101)")
    title: str
    service: str
    severity: IncidentSeverity
    status: IncidentStatus
    summary: str
    source: str
    affected_endpoints: List[str]
    metadata: Dict[str, Any]
    fingerprint: Optional[str]
    created_at: datetime
