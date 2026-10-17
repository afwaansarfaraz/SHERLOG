"""Incident Worker consuming Redis Streams via Consumer Groups.

Handles message consumption, acknowledgements, duplicate delivery protection,
bounded retries, and dead-letter queue (DLQ) routing.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import logging
import os
import socket
from typing import Any, Callable, Dict, Generator, List, Optional
import redis
from redis.exceptions import RedisError, ResponseError
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import settings
from backend.app.db.session import SessionLocal
from backend.app.queue.redis_client import get_redis_client
from backend.app.schemas.incident import IncidentResponse, IncidentStatus
from backend.app.storage.postgres import PostgresIncidentRepository

logger = logging.getLogger(__name__)


class IncidentWorker:
    """Asynchronous worker consuming incident events from Redis Streams."""

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        db_session_factory: Optional[sessionmaker] = None,
        stream_name: Optional[str] = None,
        group_name: Optional[str] = None,
        consumer_name: Optional[str] = None,
        dlq_stream_name: Optional[str] = None,
        max_retries: Optional[int] = None,
        claim_min_idle_ms: Optional[int] = None,
        processor: Optional[Callable[[IncidentResponse, Session], Any]] = None,
    ):
        self.redis = redis_client or get_redis_client()
        self.db_session_factory = db_session_factory or SessionLocal
        self.stream_name = stream_name or settings.REDIS_STREAM_NAME
        self.group_name = group_name or settings.REDIS_CONSUMER_GROUP
        self.dlq_stream_name = dlq_stream_name or settings.REDIS_DLQ_STREAM_NAME
        self.max_retries = max_retries if max_retries is not None else settings.WORKER_MAX_RETRIES
        self.claim_min_idle_ms = claim_min_idle_ms or settings.WORKER_CLAIM_TIMEOUT_MS

        # Generate unique consumer identifier
        hostname = socket.gethostname().split(".")[0]
        pid = os.getpid()
        self.consumer_name = consumer_name or f"worker-{hostname}-{pid}"

        self.processor = processor or self._default_processor
        self.is_running = False

    @contextmanager
    def get_db(self) -> Generator[Session, None, None]:
        """Managed database session context manager."""
        session: Session = self.db_session_factory()
        try:
            yield session
        finally:
            session.close()

    def setup_consumer_group(self) -> bool:
        """Create the Redis consumer group if it does not already exist."""
        try:
            # id="0" ensures newly created group processes all pending/new messages
            self.redis.xgroup_create(
                name=self.stream_name,
                groupname=self.group_name,
                id="0",
                mkstream=True,
            )
            logger.info(
                "Created consumer group '%s' on stream '%s'",
                self.group_name,
                self.stream_name,
            )
            return True
        except ResponseError as err:
            if "BUSYGROUP" in str(err):
                logger.debug(
                    "Consumer group '%s' already exists on stream '%s'",
                    self.group_name,
                    self.stream_name,
                )
                return True
            logger.error("Failed to create consumer group: %s", err, exc_info=True)
            raise

    def _default_processor(self, incident: IncidentResponse, db: Session) -> None:
        """Default processing logic: transitions incident to INVESTIGATING and executes investigation pipeline."""
        repo = PostgresIncidentRepository(db)
        repo.update_status(
            incident_id=incident.id,
            status=IncidentStatus.INVESTIGATING,
            metadata_updates={
                "worker_consumed_at": datetime.now(timezone.utc).isoformat(),
                "worker_consumer": self.consumer_name,
                "queue_status": "PROCESSING",
            },
        )
        logger.info(
            "Worker '%s' updated incident %s status to INVESTIGATING",
            self.consumer_name,
            incident.id,
        )

        # Run Sherlog bounded AI investigation pipeline
        try:
            from backend.app.investigation.orchestrator import InvestigationPipeline
            pipeline = InvestigationPipeline(db=db)
            result = pipeline.run(incident)

            # Persist summary outcome back to incident metadata
            repo.update_status(
                incident_id=incident.id,
                status=IncidentStatus.INVESTIGATING,
                metadata_updates={
                    "investigation_id": result.investigation_id,
                    "investigation_status": result.status.value,
                    "investigation_source": result.source,
                    "root_cause": result.root_cause,
                    "investigation_confidence": result.confidence.value,
                    "evidence_count": result.evidence_count,
                    "investigation_summary": result.summary,
                    "queue_status": "COMPLETED",
                },
            )
            logger.info(
                "Completed investigation %s for incident %s with status %s (source: %s)",
                result.investigation_id,
                incident.id,
                result.status.value,
                result.source,
            )
        except Exception as inv_err:
            logger.error(
                "Investigation pipeline failed for incident %s: %s",
                incident.id,
                inv_err,
                exc_info=True,
            )
            repo.update_status(
                incident_id=incident.id,
                status=IncidentStatus.INVESTIGATING,
                metadata_updates={
                    "queue_status": "FAILED",
                    "investigation_error": str(inv_err),
                },
            )
            raise


    def process_message(self, msg_id: str, fields: Dict[str, str]) -> bool:
        """Process a single stream message with idempotency, retry, and DLQ handling.

        Returns:
            True if processed or acknowledged successfully.
            False if processing failed and was retried or sent to DLQ.
        """
        incident_id = fields.get("incident_id")

        # 1. Validate payload schema
        if not incident_id:
            logger.error(
                "Malformed message %s on stream %s (missing incident_id): %s. Moving to DLQ.",
                msg_id,
                self.stream_name,
                fields,
            )
            self._send_to_dlq(
                msg_id=msg_id,
                incident_id="MALFORMED",
                fields=fields,
                error=ValueError("Missing incident_id in stream message payload"),
                retry_count=0,
            )
            self.redis.xack(self.stream_name, self.group_name, msg_id)
            return False

        try:
            retry_count = int(fields.get("retry_count", 0))
        except (ValueError, TypeError):
            retry_count = 0

        # 2. Duplicate Delivery & Idempotency Check (namespaced per stream)
        idempotency_key = f"{self.stream_name}:processed:{incident_id}"
        if self.redis.get(idempotency_key):
            logger.info(
                "Incident %s was already processed recently (idempotency key present). "
                "Acknowledging duplicate stream message %s.",
                incident_id,
                msg_id,
            )
            self.redis.xack(self.stream_name, self.group_name, msg_id)
            return True

        # Check DB status
        with self.get_db() as db:
            repo = PostgresIncidentRepository(db)
            incident = repo.get_by_id(incident_id)

            if not incident:
                # DB record not found (unexpected or desynchronized)
                logger.warning("Incident %s not found in PostgreSQL during processing.", incident_id)
                return self._handle_failure(
                    msg_id=msg_id,
                    incident_id=incident_id,
                    fields=fields,
                    retry_count=retry_count,
                    error=ValueError(f"Incident {incident_id} not found in database"),
                )

            # If already resolved or actively under investigation with completed processing
            if incident.status == IncidentStatus.RESOLVED:
                logger.info(
                    "Incident %s is already RESOLVED. Acknowledging message %s without reprocessing.",
                    incident_id,
                    msg_id,
                )
                self.redis.set(idempotency_key, "1", ex=86400)
                self.redis.xack(self.stream_name, self.group_name, msg_id)
                return True

            # 3. Execute processing
            try:
                self.processor(incident, db)

                # 4. Success: set idempotency key and acknowledge
                self.redis.set(idempotency_key, "1", ex=86400)
                self.redis.xack(self.stream_name, self.group_name, msg_id)
                logger.info(
                    "Successfully processed and acknowledged incident %s (stream msg %s)",
                    incident_id,
                    msg_id,
                )
                return True

            except Exception as proc_exc:
                logger.error(
                    "Error executing processor for incident %s: %s",
                    incident_id,
                    proc_exc,
                    exc_info=True,
                )
                return self._handle_failure(
                    msg_id=msg_id,
                    incident_id=incident_id,
                    fields=fields,
                    retry_count=retry_count,
                    error=proc_exc,
                )

    def _handle_failure(
        self,
        msg_id: str,
        incident_id: str,
        fields: Dict[str, str],
        retry_count: int,
        error: Exception,
    ) -> bool:
        """Handle processing failure: retry if within limit, otherwise route to DLQ."""
        new_retry_count = retry_count + 1

        if new_retry_count <= self.max_retries:
            # Requeue with incremented retry count
            retry_payload = dict(fields)
            retry_payload["retry_count"] = str(new_retry_count)
            retry_payload["last_error"] = str(error)
            retry_payload["retried_at"] = datetime.now(timezone.utc).isoformat()

            try:
                self.redis.xadd(self.stream_name, retry_payload)
                self.redis.xack(self.stream_name, self.group_name, msg_id)
                logger.warning(
                    "Requeued incident %s for retry (attempt %d of %d). Error: %s",
                    incident_id,
                    new_retry_count,
                    self.max_retries,
                    error,
                )
                # Update DB metadata indicating retry state
                with self.get_db() as db:
                    repo = PostgresIncidentRepository(db)
                    repo.update_queue_status(
                        incident_id,
                        f"RETRYING_{new_retry_count}",
                        {"last_retry_error": str(error)},
                    )
            except RedisError as r_err:
                logger.error("Failed to requeue incident %s for retry: %s", incident_id, r_err)
            return False

        else:
            # Exceeded maximum retries -> Dead-Letter Queue
            logger.error(
                "Incident %s exceeded maximum retries (%d). Dispatching to Dead-Letter Queue '%s'.",
                incident_id,
                self.max_retries,
                self.dlq_stream_name,
            )
            self._send_to_dlq(
                msg_id=msg_id,
                incident_id=incident_id,
                fields=fields,
                error=error,
                retry_count=new_retry_count,
            )
            self.redis.xack(self.stream_name, self.group_name, msg_id)

            # Update DB with DLQ audit state
            with self.get_db() as db:
                repo = PostgresIncidentRepository(db)
                repo.update_queue_status(
                    incident_id,
                    "DLQ",
                    {
                        "dlq_reason": str(error),
                        "retries_exhausted": new_retry_count,
                        "dlq_timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            return False

    def _send_to_dlq(
        self,
        msg_id: str,
        incident_id: str,
        fields: Dict[str, str],
        error: Exception,
        retry_count: int,
    ) -> Optional[str]:
        """Dispatch a failed message to the Dead-Letter Queue."""
        dlq_payload = {
            "incident_id": incident_id,
            "original_stream_id": msg_id,
            "service": fields.get("service", "unknown"),
            "retry_count": str(retry_count),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "raw_payload": json.dumps(fields),
        }
        try:
            dlq_id = self.redis.xadd(self.dlq_stream_name, dlq_payload)
            logger.info("Sent incident %s to DLQ with ID %s", incident_id, dlq_id)
            return str(dlq_id)
        except RedisError as r_err:
            logger.critical(
                "CRITICAL: Failed to write to DLQ for incident %s: %s",
                incident_id,
                r_err,
                exc_info=True,
            )
            return None

    def claim_stale_messages(self, min_idle_ms: Optional[int] = None) -> int:
        """Autoclaim pending messages that were abandoned by crashed workers.

        Returns:
            Count of reclaimed messages processed.
        """
        idle_time = self.claim_min_idle_ms if min_idle_ms is None else min_idle_ms
        processed_count = 0

        try:
            # xautoclaim reclaims messages idle > idle_time in PEL
            res = self.redis.xautoclaim(
                name=self.stream_name,
                groupname=self.group_name,
                consumername=self.consumer_name,
                min_idle_time=idle_time,
                start_id="0-0",
                count=10,
            )
            # Response: (next_start_id, [(msg_id, fields), ...], [deleted_msg_ids, ...])
            if res and len(res) >= 2:
                messages = res[1]
                for msg_id, fields in messages:
                    logger.info(
                        "Autoclaimed stale message %s from PEL. Reprocessing.",
                        msg_id,
                    )
                    self.process_message(msg_id, fields)
                    processed_count += 1
        except (ResponseError, RedisError) as err:
            logger.debug("xautoclaim check: %s", err)

        return processed_count

    def process_next(self, block_ms: int = 1000) -> Optional[bool]:
        """Read and process the next pending message from the consumer group.

        Returns:
            True if a message was successfully processed.
            False if a message was processed with failure (requeued or DLQ).
            None if no message was available in the stream.
        """
        self.setup_consumer_group()

        try:
            # Read new messages from stream for this consumer group (ID '>')
            streams = self.redis.xreadgroup(
                groupname=self.group_name,
                consumername=self.consumer_name,
                streams={self.stream_name: ">"},
                count=1,
                block=block_ms,
            )
            if not streams:
                return None

            # streams is [(stream_name, [(msg_id, fields)])]
            for _, messages in streams:
                for msg_id, fields in messages:
                    return self.process_message(msg_id, fields)

        except RedisError as r_err:
            logger.error("Redis error reading from consumer group: %s", r_err)
            return None

        return None

    def run(self, max_iterations: Optional[int] = None) -> None:
        """Start worker loop consuming from Redis Streams until stopped."""
        self.is_running = True
        self.setup_consumer_group()
        logger.info(
            "Worker '%s' started listening on stream '%s' (group: '%s')",
            self.consumer_name,
            self.stream_name,
            self.group_name,
        )

        iterations = 0
        while self.is_running:
            if max_iterations is not None and iterations >= max_iterations:
                break

            # Periodically claim abandoned messages from PEL
            self.claim_stale_messages()

            # Read and process next message
            self.process_next(block_ms=settings.WORKER_BLOCK_TIMEOUT_MS)
            iterations += 1

        logger.info("Worker '%s' shutdown completed.", self.consumer_name)

    def stop(self) -> None:
        """Signal worker to stop processing gracefully."""
        self.is_running = False
