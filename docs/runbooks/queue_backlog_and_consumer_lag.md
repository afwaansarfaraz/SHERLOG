# Runbook: Queue Backlog and Consumer Lag
- **Runbook ID:** RB-007
- **Category:** Queue backlog and consumer lag
- **Version:** 1.0.0
- **Applicable Services:** `redis-stream`, `worker`, `event-consumer`, asynchronous pipelines
- **Keywords:** redis stream, celery, consumer lag, queue backlog, unack messages, poison pill, throughput, dead letter queue

## Symptoms
- Alert firing: `HighConsumerLag` (unprocessed queue backlog exceeds 10,000 items or age of oldest unprocessed item exceeds 15 minutes).
- Asynchronous task processing delays: webhooks, notifications, or background transaction settlements arriving hours late.
- Redis stream length (`XLEN`) or RabbitMQ/Kafka queue depth continually climbing while consumption rate plateaus or drops.
- Worker processes reporting repeated unhandled exceptions or restart loops.

## Required Observability Signals
- **Metrics:** `redis_stream_length{stream="incident-events"}`, `consumer_lag_seconds`, `tasks_processed_total`, `tasks_failed_total`
- **Logs:** Loki query `{service="worker"} |= "error"` or `{service="worker"} |= "retrying job"`
- **Traces:** Jaeger trace spans for background job execution showing duration spikes or repeated abort/retry cycles.

## Diagnostic Steps
1. Query queue depth and consumer group state across deployed brokers:
   ```bash
   # Redis Streams (Sherlog default pipeline):
   redis-cli XINFO GROUPS incident-events
   redis-cli XPENDING incident-events sherlog-workers - + 10

   # RabbitMQ (if deployed for worker queue):
   rabbitmqctl list_queues name messages_ready messages_unacknowledged consumers

   # Kafka (if deployed for event streaming):
   kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group sherlog-workers
   ```
2. Measure the ingestion rate vs. processing rate: if ingestion rate > processing rate, identify if lag is caused by throughput limits or a slow consumer.
3. Check worker container logs for poison pill messages (messages triggering fatal errors or unhandled timeouts every time they are processed).
4. Verify if worker concurrency settings (`CONCURRENCY`, `PREFETCH_COUNT`) are tuned properly for available CPU/memory.

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Poison Pill Message Crashing Workers Repeatedly**
  - *Evidence Needed:* Repeated error logs for the same message ID followed by worker process exit or repeated retry count exhaustion.
- **Hypothesis 2: Consumer Under-Provisioning Relative to Traffic Surge**
  - *Evidence Needed:* Processing rate per worker is at nominal capacity, worker CPU is 100%, but incoming message rate increased 5x-10x.
- **Hypothesis 3: Consumer Dependency Slowdown (Database or External API)**
  - *Evidence Needed:* Average job execution time increased from 50ms to 2000ms due to downstream database locks or third-party API rate limits.

## Contradictory Evidence & Alternative Explanations
- If queue depth is high but consumer lag time is under 2 seconds, the queue is operating as a normal shock-absorber for bursty traffic; do not panic.
- If worker processes are crashing with memory errors, investigate memory leaks in data ingestion rather than pure queue configuration issues.

## Safe Mitigation & Rollback Guidance
- **Scale Worker Consumers:** Dynamically increase worker instances:
  ```bash
  docker compose up -d --scale worker=4
  ```
- **Quarantine Poison Pill Messages:** Safely move crashing messages to a Dead Letter Queue (DLQ) by publishing the payload to `incident-events-dlq` first, and acknowledging it with `XACK` only after the publish succeeds:
  ```bash
  # 1. Fetch message payload from pending stream:
  redis-cli XRANGE incident-events <bad-message-id> <bad-message-id>
  # 2. Publish payload to DLQ:
  redis-cli XADD incident-events-dlq * original_id <bad-message-id> payload "<message-data>"
  # 3. Only after DLQ publish succeeds, acknowledge to remove from worker pending entries:
  redis-cli XACK incident-events sherlog-workers <bad-message-id>
  ```
- **Tune Batch Size:** Adjust consumer batch size (`COUNT`) to avoid long-lived transaction locks.
- **Temporary Ingestion Throttling:** If downstream storage is saturating, rate-limit upstream producers temporarily.

## Verification Steps & Escalation Criteria
- **Verification:** Consumer pending message count (`XPENDING`) returns to near zero, stream length stabilizes, and end-to-end task completion latency drops under 500ms.
- **Escalation Criteria:** If backlog exceeds 100,000 items and queue storage threatens broker disk capacity, notify Streaming Infrastructure On-Call (P1).
