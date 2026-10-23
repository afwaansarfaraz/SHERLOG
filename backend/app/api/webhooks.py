"""Authenticated Alertmanager ingestion into Sherlog's incident pipeline."""

import hmac
import logging
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from backend.app.api.incidents import get_repository, persist_and_publish_incident
from backend.app.config import settings
from backend.app.queue.publisher import IncidentPublisher, get_publisher
from backend.app.schemas.incident import IncidentCreate, IncidentSeverity, IncidentStatus
from backend.app.storage.postgres import PostgresIncidentRepository

logger = logging.getLogger(__name__)
router = APIRouter()


class AlertmanagerAlert(BaseModel):
    status: Literal["firing", "resolved"]
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: str = Field(..., min_length=1, max_length=128)
    value: Optional[str] = None


class AlertmanagerWebhookPayload(BaseModel):
    version: Optional[str] = None
    groupKey: Optional[str] = None
    status: Literal["firing", "resolved"]
    receiver: Optional[str] = None
    alerts: List[AlertmanagerAlert] = Field(default_factory=list)
    commonLabels: Dict[str, str] = Field(default_factory=dict)
    commonAnnotations: Dict[str, str] = Field(default_factory=dict)


def _require_webhook_authentication(authorization: Optional[str]) -> None:
    """Fail closed unless the configured Alertmanager bearer token matches."""
    secret = (settings.WEBHOOK_SECRET or "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alertmanager webhook authentication is not configured on the server.",
        )

    scheme, separator, token = (authorization or "").partition(" ")
    if not separator or scheme.lower() != "bearer" or not hmac.compare_digest(
        token.strip().encode("utf-8"), secret.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for Alertmanager webhook.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _severity(value: Optional[str]) -> IncidentSeverity:
    mapping = {
        "critical": IncidentSeverity.CRITICAL,
        "high": IncidentSeverity.HIGH,
        "warning": IncidentSeverity.MEDIUM,
        "medium": IncidentSeverity.MEDIUM,
        "info": IncidentSeverity.LOW,
        "low": IncidentSeverity.LOW,
    }
    return mapping.get((value or "").strip().lower(), IncidentSeverity.MEDIUM)


def _alert_metadata(alert: AlertmanagerAlert) -> Dict[str, Any]:
    return {
        "status": alert.status,
        "labels": alert.labels,
        "annotations": alert.annotations,
        "starts_at": alert.startsAt,
        "ends_at": alert.endsAt,
        "generator_url": alert.generatorURL,
        "value": alert.value,
    }


@router.post("/alertmanager", summary="Ingest authenticated Alertmanager events")
def ingest_alertmanager_webhook(
    payload: AlertmanagerWebhookPayload,
    authorization: Optional[str] = Header(default=None),
    repo: PostgresIncidentRepository = Depends(get_repository),
    publisher: IncidentPublisher = Depends(get_publisher),
) -> Dict[str, Any]:
    """Persist firing alerts, deduplicate retries, and resolve incidents on recovery."""
    _require_webhook_authentication(authorization)

    created_ids: List[str] = []
    resolved_ids: List[str] = []
    duplicates = 0
    unmatched_resolutions = 0

    for alert in payload.alerts:
        try:
            existing = repo.get_active_by_fingerprint(alert.fingerprint)
            if alert.status == "resolved":
                if existing:
                    resolved = repo.update_status(
                        existing.id,
                        status=IncidentStatus.RESOLVED,
                        metadata_updates={"alertmanager": _alert_metadata(alert)},
                    )
                    if resolved:
                        resolved_ids.append(resolved.id)
                else:
                    unmatched_resolutions += 1
                continue

            if existing:
                duplicates += 1
                continue

            title = alert.annotations.get("summary") or alert.labels.get("alertname") or "Alertmanager alert"
            summary = (
                alert.annotations.get("description")
                or alert.annotations.get("summary")
                or f"Alert {alert.labels.get('alertname', 'unknown')} is firing."
            )
            incident = IncidentCreate(
                title=title[:200],
                service=alert.labels.get("service", "unknown")[:100],
                severity=_severity(alert.labels.get("severity")),
                status=IncidentStatus.OPEN,
                summary=summary[:2000],
                source="alertmanager",
                metadata={"alertmanager": _alert_metadata(alert)},
                fingerprint=alert.fingerprint,
            )
            saved = persist_and_publish_incident(incident, repo, publisher)
            created_ids.append(saved.id)
        except SQLAlchemyError:
            logger.exception("Database error processing Alertmanager event")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error processing Alertmanager event.",
            )

    return {
        "status": "accepted",
        "received_alerts": len(payload.alerts),
        "created_incidents": len(created_ids),
        "resolved_incidents": len(resolved_ids),
        "duplicate_alerts": duplicates,
        "unmatched_resolutions": unmatched_resolutions,
        "incident_ids": created_ids + resolved_ids,
    }
