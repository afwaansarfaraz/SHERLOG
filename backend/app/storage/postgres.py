"""PostgreSQL incident repository implementation for Sherlog.

Provides persistence, querying, and idempotency guarantees using SQLAlchemy sessions.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.app.schemas.incident import IncidentCreate, IncidentResponse, IncidentStatus
from backend.app.db.models.incident import IncidentModel
from backend.app.db.session import generate_next_incident_id


class PostgresIncidentRepository:
    """SQLAlchemy-backed repository managing incident records."""

    def __init__(self, db: Session):
        self.db = db

    def save(self, data: IncidentCreate) -> IncidentResponse:
        """Persist an incident alert and return the created record.

        Idempotency:
            If a non-empty `fingerprint` is provided, checks for an existing active
            (OPEN or INVESTIGATING) incident with the same fingerprint. If found,
            returns the existing record to prevent duplicate alert storms.
        """
        # Idempotency check on active fingerprint
        if data.fingerprint:
            existing = (
                self.db.query(IncidentModel)
                .filter(
                    IncidentModel.fingerprint == data.fingerprint,
                    IncidentModel.status.in_([IncidentStatus.OPEN.value, IncidentStatus.INVESTIGATING.value]),
                )
                .first()
            )
            if existing:
                return existing.to_pydantic()

        # Generate unique sequential tracking ID
        incident_id = generate_next_incident_id(self.db)
        now_utc = datetime.now(timezone.utc)

        record = IncidentModel(
            id=incident_id,
            title=data.title,
            service=data.service,
            severity=data.severity.value if hasattr(data.severity, "value") else str(data.severity),
            status=data.status.value if hasattr(data.status, "value") else str(data.status),
            summary=data.summary,
            source=data.source,
            affected_endpoints=data.affected_endpoints,
            extra_metadata=data.metadata,
            fingerprint=data.fingerprint,
            created_at=now_utc,
            updated_at=now_utc,
        )

        try:
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record.to_pydantic()
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def get_by_id(self, incident_id: str) -> Optional[IncidentResponse]:
        """Fetch an incident by its unique tracking ID."""
        try:
            record = (
                self.db.query(IncidentModel)
                .filter(IncidentModel.id == incident_id)
                .first()
            )
            return record.to_pydantic() if record else None
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def get_active_by_fingerprint(self, fingerprint: str) -> Optional[IncidentResponse]:
        """Find an open/investigating incident for an Alertmanager fingerprint."""
        try:
            record = (
                self.db.query(IncidentModel)
                .filter(
                    IncidentModel.fingerprint == fingerprint,
                    IncidentModel.status.in_([IncidentStatus.OPEN.value, IncidentStatus.INVESTIGATING.value]),
                )
                .first()
            )
            return record.to_pydantic() if record else None
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def list_all(self, limit: int = 100, offset: int = 0) -> List[IncidentResponse]:
        """List incidents ordered latest first."""
        try:
            records = (
                self.db.query(IncidentModel)
                .order_by(IncidentModel.created_at.desc(), IncidentModel.id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [r.to_pydantic() for r in records]
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def update_status(
        self,
        incident_id: str,
        status: Optional[Union[IncidentStatus, str]] = None,
        metadata_updates: Optional[Dict[str, Any]] = None,
    ) -> Optional[IncidentResponse]:
        """Update incident lifecycle status and optionally merge metadata updates."""
        try:
            record = (
                self.db.query(IncidentModel)
                .filter(IncidentModel.id == incident_id)
                .first()
            )
            if not record:
                return None

            now_utc = datetime.now(timezone.utc)
            record.updated_at = now_utc

            if status is not None:
                record.status = status.value if hasattr(status, "value") else str(status)

            if metadata_updates:
                current_meta = dict(record.extra_metadata or {})
                current_meta.update(metadata_updates)
                record.extra_metadata = current_meta

            self.db.commit()
            self.db.refresh(record)
            return record.to_pydantic()
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def update_queue_status(
        self,
        incident_id: str,
        queue_status: str,
        extra_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[IncidentResponse]:
        """Record queue dispatch or delivery state in incident metadata."""
        meta_updates: Dict[str, Any] = {"queue_status": queue_status}
        if extra_info:
            meta_updates.update(extra_info)
        return self.update_status(incident_id, status=None, metadata_updates=meta_updates)

    def clear(self) -> None:
        """Clear all stored incidents (for isolated test teardowns)."""
        try:
            self.db.query(IncidentModel).delete()
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise
