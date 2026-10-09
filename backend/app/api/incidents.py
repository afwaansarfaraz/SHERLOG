"""Incident ingestion and retrieval endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.incident import IncidentCreate, IncidentResponse
from backend.app.storage.memory import incident_repo

router = APIRouter()


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new incident alert",
    description="Validates incoming alert payload, assigns a tracking ID, and registers the incident.",
)
async def ingest_incident(incident_in: IncidentCreate) -> IncidentResponse:
    """Validate and ingest an incident alert."""
    try:
        saved_incident = incident_repo.save(incident_in)
        return saved_incident
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process incident ingestion: {str(exc)}",
        )


@router.get(
    "",
    response_model=List[IncidentResponse],
    summary="List all ingested incidents",
)
async def list_incidents() -> List[IncidentResponse]:
    """Retrieve all ingested incidents."""
    return incident_repo.list_all()


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get incident details by ID",
)
async def get_incident(incident_id: str) -> IncidentResponse:
    """Retrieve an incident by its ID."""
    incident = incident_repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found",
        )
    return incident
