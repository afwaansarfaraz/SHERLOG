"""PostgreSQL Incident SQLAlchemy Model for Sherlog."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, String, Text, DateTime, JSON, Index, Sequence
from sqlalchemy.orm import validates

from backend.app.db.base import Base
from backend.app.schemas.incident import IncidentSeverity, IncidentStatus, IncidentResponse

# Global sequence for human-readable sequential IDs (INC-00001, INC-00002...)
incident_id_seq = Sequence("incident_id_seq", start=1)


class IncidentModel(Base):
    """PostgreSQL database table model for ingested incidents."""

    __tablename__ = "incidents"

    id = Column(
        String(32),
        primary_key=True,
        index=True,
        doc="Human-readable unique incident tracking ID (e.g. INC-00001)",
    )
    title = Column(
        String(200),
        nullable=False,
        doc="Short description of the incident anomaly",
    )
    service = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Name of the affected service (e.g. orders, payments, api)",
    )
    severity = Column(
        String(32),
        nullable=False,
        doc="Incident severity level (CRITICAL, HIGH, MEDIUM, LOW)",
    )
    status = Column(
        String(32),
        nullable=False,
        default=IncidentStatus.OPEN.value,
        doc="Current lifecycle state (OPEN, INVESTIGATING, AWAITING_APPROVAL, RESOLVED)",
    )
    summary = Column(
        Text,
        nullable=False,
        doc="Detailed summary of the observed failure or alert description",
    )
    source = Column(
        String(64),
        nullable=False,
        default="alertmanager",
        doc="Origin of the alert (alertmanager, sentry, manual)",
    )
    affected_endpoints = Column(
        JSON,
        nullable=False,
        default=list,
        doc="JSON list of HTTP routes impacted by this incident",
    )
    # Note: 'metadata' is reserved on SQLAlchemy Base, so map column 'metadata' with alias property
    extra_metadata = Column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        doc="Arbitrary alert metadata, PromQL queries, annotations",
    )
    fingerprint = Column(
        String(128),
        nullable=True,
        index=True,
        doc="Optional alert deduplication fingerprint",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="UTC timestamp when the incident was ingested",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="UTC timestamp when the incident was last modified",
    )

    __table_args__ = (
        Index("idx_incidents_service_status", "service", "status"),
        Index("idx_incidents_created_at_desc", created_at.desc()),
    )

    @property
    def alert_metadata(self) -> Dict[str, Any]:
        """Expose metadata property without colliding with Declarative Base.metadata."""
        return self.extra_metadata or {}

    @alert_metadata.setter
    def alert_metadata(self, value: Dict[str, Any]) -> None:
        self.extra_metadata = value or {}

    def to_pydantic(self) -> IncidentResponse:
        """Convert ORM model to validated Pydantic IncidentResponse schema."""
        return IncidentResponse(
            id=self.id,
            title=self.title,
            service=self.service,
            severity=IncidentSeverity(self.severity),
            status=IncidentStatus(self.status),
            summary=self.summary,
            source=self.source,
            affected_endpoints=self.affected_endpoints or [],
            metadata=self.extra_metadata or {},
            fingerprint=self.fingerprint,
            created_at=self.created_at,
        )
