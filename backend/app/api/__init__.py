"""API routers for Sherlog backend."""

from fastapi import APIRouter
from backend.app.api.health import router as health_router
from backend.app.api.incidents import router as incidents_router
from backend.app.api.knowledge import router as knowledge_router
from backend.app.api.investigations import router as investigations_router
from backend.app.api.settings import router as settings_router
from backend.app.api.evaluations import router as evaluations_router
from backend.app.api.applications import router as applications_router
from backend.app.api.webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(incidents_router, prefix="/incidents", tags=["incidents"])
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(investigations_router, prefix="/investigations", tags=["investigations"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(evaluations_router, prefix="/evaluations", tags=["evaluations"])
api_router.include_router(applications_router, prefix="/applications", tags=["applications"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])

# Direct alias for /audit-logs
from backend.app.api.investigations import get_audit_log, AuditLogEntry
from typing import List, Optional
from fastapi import Depends
from sqlalchemy.orm import Session
from backend.app.db.session import get_db

@api_router.get("/audit-logs", response_model=List[AuditLogEntry], tags=["audit-logs"])
def list_audit_logs(
    incident_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return get_audit_log(incident_id=incident_id, action=action, limit=limit, offset=offset, db=db)

__all__ = ["api_router", "health_router"]
