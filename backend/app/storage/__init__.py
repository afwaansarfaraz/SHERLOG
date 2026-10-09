"""Storage module for incident persistence in Phase 1."""

from backend.app.storage.memory import IncidentRepository, incident_repo

__all__ = ["IncidentRepository", "incident_repo"]
