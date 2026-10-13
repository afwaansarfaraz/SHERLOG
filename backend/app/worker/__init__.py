"""Incident worker package for consuming and processing Redis Streams events."""

from backend.app.worker.worker import IncidentWorker

__all__ = ["IncidentWorker"]
