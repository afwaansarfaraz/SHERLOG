"""Incident event publisher for Redis Streams.

Publishes ingested incident IDs and metadata to the stream so workers can consume them asynchronously.
Guarantees database persistence never depends on Redis availability.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional
import redis
from redis.exceptions import RedisError

from backend.app.config import settings
from backend.app.queue.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class QueuePublishError(Exception):
    """Raised when an incident cannot be published to Redis Stream in strict mode."""
    pass


class IncidentPublisher:
    """Publishes incident events to Redis Streams."""

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        stream_name: Optional[str] = None,
    ):
        self._redis = redis_client
        self.stream_name = stream_name or settings.REDIS_STREAM_NAME

    @property
    def redis(self) -> redis.Redis:
        """Lazily retrieve Redis client."""
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis

    def publish_incident(
        self,
        incident_id: str,
        service: str = "unknown",
        severity: str = "MEDIUM",
        fingerprint: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Publish an incident event to Redis Stream.

        Returns:
            Redis stream message ID (e.g. '1712345678-0') if successful.
            None if Redis is unavailable or publishing failed (non-blocking).
        """
        payload = {
            "incident_id": incident_id,
            "service": service,
            "severity": severity,
            "fingerprint": fingerprint or "",
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
            "retry_count": "0",
        }
        if metadata:
            payload["extra_meta"] = json.dumps(metadata)

        try:
            msg_id = self.redis.xadd(self.stream_name, payload)
            logger.info(
                "Published incident %s to Redis Stream '%s' with message ID %s",
                incident_id,
                self.stream_name,
                msg_id,
            )
            return str(msg_id)
        except (RedisError, Exception) as exc:
            logger.warning(
                "Failed to publish incident %s to Redis Stream '%s': %s. "
                "Database persistence remains intact.",
                incident_id,
                self.stream_name,
                exc,
            )
            return None

    def publish_strict(
        self,
        incident_id: str,
        service: str = "unknown",
        severity: str = "MEDIUM",
        fingerprint: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Publish incident event; raises QueuePublishError if Redis is unavailable."""
        msg_id = self.publish_incident(
            incident_id=incident_id,
            service=service,
            severity=severity,
            fingerprint=fingerprint,
            metadata=metadata,
        )
        if not msg_id:
            raise QueuePublishError(
                f"Failed to publish incident {incident_id} to Redis Stream {self.stream_name}"
            )
        return msg_id


def get_publisher() -> IncidentPublisher:
    """FastAPI dependency provider for IncidentPublisher."""
    return IncidentPublisher()
