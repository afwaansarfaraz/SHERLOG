"""Incident ingestion and retrieval endpoints backed by PostgreSQL."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.app.schemas.incident import IncidentCreate, IncidentResponse
from backend.app.db.session import get_db
from backend.app.storage.postgres import PostgresIncidentRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def get_repository(db: Session = Depends(get_db)) -> PostgresIncidentRepository:
    """Dependency provider for PostgresIncidentRepository."""
    return PostgresIncidentRepository(db)


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
) -> IncidentResponse:
    """Validate and ingest an incident alert into persistent storage."""
    try:
        saved_incident = repo.save(incident_in)
        return saved_incident
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
            detail=f"Failed to process incident ingestion: {str(exc)}",
        )


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
