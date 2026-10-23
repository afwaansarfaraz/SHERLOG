"""Incident ingestion and retrieval endpoints backed by PostgreSQL."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.app.schemas.incident import IncidentCreate, IncidentResponse
from backend.app.db.session import get_db
from backend.app.storage.postgres import PostgresIncidentRepository
from backend.app.queue.publisher import IncidentPublisher, get_publisher

logger = logging.getLogger(__name__)

router = APIRouter()


def get_repository(db: Session = Depends(get_db)) -> PostgresIncidentRepository:
    """Dependency provider for PostgresIncidentRepository."""
    return PostgresIncidentRepository(db)


def persist_and_publish_incident(
    incident_in: IncidentCreate,
    repo: PostgresIncidentRepository,
    publisher: IncidentPublisher,
) -> IncidentResponse:
    """Persist an incident before attempting its asynchronous queue dispatch."""
    try:
        saved_incident = repo.save(incident_in)
    except SQLAlchemyError as db_err:
        logger.error("Database error during incident ingestion: %s", str(db_err), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database persistence error occurred while saving the incident alert.",
        )
    except Exception as exc:
        logger.error("Unexpected error during incident ingestion: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process incident ingestion.",
        )

    # Database persistence is authoritative; Redis dispatch is best-effort.
    try:
        severity_str = (
            saved_incident.severity.value
            if hasattr(saved_incident.severity, "value")
            else str(saved_incident.severity)
        )
        msg_id = publisher.publish_incident(
            incident_id=saved_incident.id,
            service=saved_incident.service,
            severity=severity_str,
            fingerprint=saved_incident.fingerprint,
            metadata=saved_incident.metadata,
        )
        if msg_id:
            logger.info("Incident %s enqueued to Redis Stream (msg ID: %s)", saved_incident.id, msg_id)
            repo.update_queue_status(saved_incident.id, "ENQUEUED", {"stream_id": msg_id})
        else:
            logger.warning(
                "Incident %s persisted in PostgreSQL but Redis publish was unavailable; "
                "marking it for backfill.",
                saved_incident.id,
            )
            repo.update_queue_status(saved_incident.id, "PUBLISH_FAILED")
    except Exception as q_exc:
        logger.error(
            "Unexpected error enqueueing incident %s to Redis Streams: %s. Persistence is preserved.",
            saved_incident.id,
            str(q_exc),
            exc_info=True,
        )
        repo.update_queue_status(saved_incident.id, "PUBLISH_FAILED", {"error": str(q_exc)})

    return saved_incident


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new incident alert",
    description="Validates incoming alert payload, assigns a tracking ID, and registers the incident in PostgreSQL.",
)
def ingest_incident(
    incident_in: IncidentCreate,
    repo: PostgresIncidentRepository = Depends(get_repository),
    publisher: IncidentPublisher = Depends(get_publisher),
) -> IncidentResponse:
    """Validate and ingest an incident alert into persistent storage, then queue to Redis Streams."""
    return persist_and_publish_incident(incident_in, repo, publisher)


@router.get(
    "",
    response_model=List[IncidentResponse],
    summary="List all ingested incidents",
)
def list_incidents(
    repo: PostgresIncidentRepository = Depends(get_repository),
) -> List[IncidentResponse]:
    """Retrieve all ingested incidents from database, ordered latest first."""
    try:
        return repo.list_all()
    except SQLAlchemyError as db_err:
        logger.error("Database error retrieving incidents list: %s", str(db_err), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while retrieving incidents.",
        )


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get incident details by ID",
)
def get_incident(
    incident_id: str,
    repo: PostgresIncidentRepository = Depends(get_repository),
) -> IncidentResponse:
    """Retrieve an incident by its unique tracking ID."""
    try:
        incident = repo.get_by_id(incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident with ID '{incident_id}' not found",
            )
        return incident
    except HTTPException:
        raise
    except SQLAlchemyError as db_err:
        logger.error("Database error retrieving incident %s: %s", incident_id, str(db_err), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while retrieving incident.",
        )
