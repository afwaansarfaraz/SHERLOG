"""In-memory incident repository for Phase 1.

Provides isolated storage with sequential IDs (INC-00001, INC-00002...).
Does not claim PostgreSQL persistence or Redis queueing until those are explicitly added.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from threading import Lock

from backend.app.schemas.incident import IncidentCreate, IncidentResponse


class IncidentRepository:
    """Thread-safe in-memory store for ingested incidents."""

    def __init__(self):
        self._incidents: Dict[str, IncidentResponse] = {}
        self._counter: int = 0
        self._lock: Lock = Lock()

    def save(self, data: IncidentCreate) -> IncidentResponse:
        """Store an incident and return the saved instance with assigned ID."""
        with self._lock:
            self._counter += 1
            incident_id = f"INC-{self._counter:05d}"
            
            record = IncidentResponse(
                id=incident_id,
                title=data.title,
                service=data.service,
                severity=data.severity,
                status=data.status,
                summary=data.summary,
                source=data.source,
                affected_endpoints=data.affected_endpoints,
                metadata=data.metadata,
                fingerprint=data.fingerprint,
                created_at=datetime.now(timezone.utc),
            )
            self._incidents[incident_id] = record
            return record

    def get_by_id(self, incident_id: str) -> Optional[IncidentResponse]:
        """Fetch an incident by its unique ID."""
        with self._lock:
            return self._incidents.get(incident_id)

    def list_all(self) -> List[IncidentResponse]:
        """List all ingested incidents, latest first."""
        with self._lock:
            return sorted(
                list(self._incidents.values()),
                key=lambda x: x.id,
                reverse=True,
            )

    def clear(self) -> None:
        """Clear all stored incidents (primarily for test resets)."""
        with self._lock:
            self._incidents.clear()
            self._counter = 0


incident_repo = IncidentRepository()
