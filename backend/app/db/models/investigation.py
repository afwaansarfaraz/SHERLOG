"""PostgreSQL Investigation and Checkpoint SQLAlchemy Models for Sherlog."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class InvestigationModel(Base):
    """PostgreSQL database table model for AI incident investigations."""

    __tablename__ = "investigations"

    id = Column(
        String(36),
        primary_key=True,
        index=True,
        doc="Unique investigation tracking ID (e.g. INV-INC-00001 or UUID)",
    )
    incident_id = Column(
        String(32),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key reference to the investigated incident",
    )
    state = Column(
        String(32),
        nullable=False,
        default="QUEUED",
        index=True,
        doc="Investigation state (QUEUED, COLLECTING_EVIDENCE, GENERATING_HYPOTHESES, EVALUATING_HYPOTHESES, COMPLETED, INSUFFICIENT_EVIDENCE, FAILED)",
    )
    current_step = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Current execution step count of the state machine",
    )
    evidence = Column(
        JSON,
        nullable=False,
        default=list,
        doc="JSON list of collected and bounded telemetry evidence items",
    )
    hypotheses = Column(
        JSON,
        nullable=False,
        default=list,
        doc="JSON list of generated root cause hypotheses",
    )
    evaluation = Column(
        JSON,
        nullable=False,
        default=dict,
        doc="JSON object containing deterministic scores, ranking, and rationale",
    )
    root_cause = Column(
        String(128),
        nullable=True,
        doc="Identified leading root cause, if sufficiently supported",
    )
    investigation_source = Column(
        String(32),
        nullable=False,
        default="llm",
        doc="Origin of investigation reasoning (llm, baseline_fallback, insufficient_evidence)",
    )
    tool_executions = Column(
        JSON,
        nullable=False,
        default=list,
        doc="JSON list of tool execution logs with status, latency, and sanitized outputs",
    )
    budget_consumed = Column(
        JSON,
        nullable=False,
        default=dict,
        doc="JSON tracking steps, tool calls, LLM calls, tokens, and duration",
    )
    error_message = Column(
        Text,
        nullable=True,
        doc="Sanitized error description if state is FAILED",
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp when investigation began",
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when investigation reached a terminal state",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp of investigation record creation",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="Timestamp of last update",
    )

    checkpoints = relationship(
        "InvestigationCheckpointModel",
        back_populates="investigation",
        cascade="all, delete-orphan",
        order_by="InvestigationCheckpointModel.step.asc()",
    )

    __table_args__ = (
        Index("idx_investigations_incident_state", "incident_id", "state"),
        Index("idx_investigations_started_at", "started_at"),
    )


class InvestigationCheckpointModel(Base):
    """PostgreSQL model for persistent investigation state checkpoints."""

    __tablename__ = "investigation_checkpoints"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Auto-incrementing checkpoint identifier",
    )
    investigation_id = Column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key reference to parent investigation",
    )
    incident_id = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Associated incident ID for quick lookup",
    )
    step = Column(
        Integer,
        nullable=False,
        doc="Step index at which this checkpoint was captured",
    )
    state = Column(
        String(32),
        nullable=False,
        doc="State machine state at checkpoint",
    )
    snapshot = Column(
        JSON,
        nullable=False,
        doc="Complete state snapshot (evidence, hypotheses, evaluation, budgets)",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp when checkpoint was committed",
    )

    investigation = relationship("InvestigationModel", back_populates="checkpoints")

    __table_args__ = (
        Index("idx_checkpoints_inv_step", "investigation_id", "step"),
        Index("idx_checkpoints_incident", "incident_id"),
    )


class AuditLogModel(Base):
    """PostgreSQL model for persistent human approval/rejection audit trail."""

    __tablename__ = "audit_logs"

    id = Column(
        String(36),
        primary_key=True,
        index=True,
        doc="Unique audit log identifier (e.g. AUD-XXXXXXXX)",
    )
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Timestamp of the decision action",
    )
    action = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Audit action: REMEDIATION_APPROVED or REMEDIATION_REJECTED",
    )
    actor = Column(
        String(128),
        nullable=False,
        doc="Identity of operator or system performing the action",
    )
    investigation_id = Column(
        String(36),
        nullable=False,
        index=True,
        doc="Investigation ID associated with the decision",
    )
    incident_id = Column(
        String(32),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Incident ID associated with the decision",
    )
    proposal_id = Column(
        String(64),
        nullable=True,
        index=True,
        doc="Remediation proposal identifier (e.g. REM-INC-XXXXX)",
    )
    reason = Column(
        Text,
        nullable=True,
        doc="Optional operator rejection or approval justification",
    )
    details = Column(
        Text,
        nullable=False,
        doc="Human-readable audit summary of the decision",
    )

