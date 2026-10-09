"""Health check router for Sherlog backend."""

from fastapi import APIRouter
from backend.app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Service health endpoint indicating backend process availability."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }
