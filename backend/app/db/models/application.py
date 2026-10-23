"""Registered Application and Monitored Service Database Model."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import Column, DateTime, String, Text, JSON, UniqueConstraint
from backend.app.db.base import Base


class ApplicationModel(Base):
    """Represents an application or monitored service registered in Sherlog."""

    __tablename__ = "registered_applications"
    __table_args__ = (
        UniqueConstraint("service_name", "environment", name="uq_registered_applications_service_env"),
    )

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    service_name = Column(String(64), nullable=False, index=True)
    environment = Column(String(32), nullable=False, default="production")
    integration_type = Column(String(32), nullable=False, default="opentelemetry")
    endpoint_url = Column(String(256), nullable=True)
    telemetry_config = Column(JSON, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="REGISTERED")
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
