import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from config import settings
from telemetry import (
    DB_CONNECTIONS_ACTIVE,
    DB_POOL_EXHAUSTION_ERRORS,
)

logger = logging.getLogger("orders.db")

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session and tracks active pool connections."""
    db = SessionLocal()
    try:
        # Update metric with checked out pool connections
        DB_CONNECTIONS_ACTIVE.labels(service=settings.SERVICE_NAME).set(
            engine.pool.checkedout()
        )
        yield db
    except Exception as exc:
        if "timeout" in str(exc).lower() or "queuepool" in str(exc).lower():
            DB_POOL_EXHAUSTION_ERRORS.labels(service=settings.SERVICE_NAME).inc()
            logger.error(f"Database connection pool exhausted: {exc}")
        raise
    finally:
        db.close()
        DB_CONNECTIONS_ACTIVE.labels(service=settings.SERVICE_NAME).set(
            engine.pool.checkedout()
        )


def check_db_health() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
