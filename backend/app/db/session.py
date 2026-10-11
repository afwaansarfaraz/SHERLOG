"""Database engine and session management for Sherlog.

Provides managed SQLAlchemy sessions with connection pooling, health pre-ping,
and safe dependency cleanup for FastAPI routes.
"""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.app.config import settings
from backend.app.db.models.incident import incident_id_seq, IncidentModel

# Engine configuration
engine_kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

# Configure pooling depending on database dialect
db_url = settings.sync_database_url
if "sqlite" in db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in db_url:
        engine_kwargs["poolclass"] = StaticPool
else:
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = settings.DATABASE_POOL_TIMEOUT

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped database session.

    Guarantees session closure after request handling.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_next_incident_id(db: Session) -> str:
    """Generate sequential tracking ID (e.g. INC-00001) safely across PostgreSQL and SQLite.

    Prefers native PostgreSQL sequence; falls back to table scan on SQLite/unit tests.
    """
    # 1. Try PostgreSQL sequence
    try:
        if db.bind and db.bind.dialect.name == "postgresql":
            val = db.scalar(incident_id_seq)
            if val:
                return f"INC-{int(val):05d}"
    except Exception:
        # Fall back to table query if sequence is not yet created or during SQLite testing
        pass

    # 2. Resilient fallback query: determine highest numeric suffix in table
    try:
        # Fetch existing IDs to determine highest counter
        existing_ids = db.query(IncidentModel.id).all()
        max_num = 0
        for (row_id,) in existing_ids:
            if row_id and row_id.startswith("INC-"):
                try:
                    num = int(row_id.replace("INC-", ""))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    continue
        return f"INC-{(max_num + 1):05d}"
    except Exception:
        # Default starting point if table is empty
        return "INC-00001"
