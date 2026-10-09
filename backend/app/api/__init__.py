"""API routers for Sherlog backend."""

from fastapi import APIRouter
from backend.app.api.health import router as health_router
from backend.app.api.incidents import router as incidents_router

api_router = APIRouter()
api_router.include_router(incidents_router, prefix="/incidents", tags=["incidents"])

__all__ = ["api_router", "health_router"]
