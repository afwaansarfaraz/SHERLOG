"""Storage layer for Sherlog incidents."""

from backend.app.storage.memory import IncidentRepository, incident_repo
from backend.app.storage.postgres import PostgresIncidentRepository

__all__ = ["IncidentRepository", "incident_repo", "PostgresIncidentRepository"]
