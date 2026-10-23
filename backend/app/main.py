"""Main FastAPI application entrypoint for Sherlog Backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import api_router, health_router
from backend.app.config import settings


def create_app() -> FastAPI:
    """Factory function to configure and create the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Sherlog AI Incident Investigation & Response Platform - Core Ingestion API",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health router (available at both /health, /api/health, and /api/v1/health)
    app.include_router(health_router)
    app.include_router(health_router, prefix=settings.API_V1_PREFIX)
    if settings.API_V1_PREFIX != "/api/v1":
        app.include_router(health_router, prefix="/api/v1")

    # Core API routers (/api/incidents, /api/v1/incidents, etc.)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    if settings.API_V1_PREFIX != "/api/v1":
        app.include_router(api_router, prefix="/api/v1")

    @app.on_event("startup")
    def on_startup():
        """Seed demo applications on startup if database is empty and demo seeding is enabled."""
        if not settings.ENABLE_DEMO_SEEDING:
            return
        try:
            from backend.app.db.session import SessionLocal
            from backend.app.api.applications import seed_default_applications
            db = SessionLocal()
            try:
                seed_default_applications(db)
            finally:
                db.close()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Startup application seeding skipped: %s", exc)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
