# Runbook: Database Locks and Deadlocks
- **Runbook ID:** RB-003
- **Category:** Database locks and deadlocks
- **Version:** 1.0.0
- **Applicable Services:** `orders`, `payments`, PostgreSQL databases
- **Keywords:** postgresql, locks, deadlocks, lock contention, row exclusive, pg_locks, deadlocked, 40P01, transaction timeout

## Symptoms
- Application error logs reporting PostgreSQL error code `40P01` (`deadlock detected`).
- Spike in transaction wait times and database connection wait states (`exclusive lock` or `row exclusive lock`).
- Client requests timing out at the gateway while waiting for database row locks to be released.
- Increased transaction rollback rates in Prometheus metrics.

## Required Observability Signals
- **Metrics:** `pg_stat_database_deadlocks_total`, `pg_locks_count{mode="exclusive"}`, `http_requests_total{status="500"}`
- **Logs:** Loki query `{service="db"} |= "deadlock detected"` or `{service="orders"} |= "deadlock detected"`
- **Traces:** Jaeger trace spans showing SQL transaction span durations stretching past statement timeout (e.g., 5000ms+).

## Diagnostic Steps
1. Query active locks and blocking transactions using `pg_blocking_pids`:
   ```sql
   SELECT blocked_activity.pid AS blocked_pid,
          blocked_activity.usename AS blocked_user,
          blocking_activity.pid AS blocking_pid,
          blocking_activity.usename AS blocking_user,
          blocked_activity.query AS blocked_statement,
          blocking_activity.query AS current_statement_in_blocking_process,
          blocked_activity.wait_event_type,
          blocked_activity.wait_event
   FROM pg_catalog.pg_stat_activity blocked_activity
   JOIN pg_catalog.pg_stat_activity blocking_activity 
       ON blocking_activity.pid = ANY(pg_blocking_pids(blocked_activity.pid))
   WHERE cardinality(pg_blocking_pids(blocked_activity.pid)) > 0;
   ```
2. Inspect deadlock log entries in PostgreSQL engine logs: identify the two conflicting transactions and the resource IDs involved.
3. Review application transaction boundaries: check if multiple services or threads update resources in differing orders (e.g. updating Order then Inventory vs. Inventory then Order).

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Inconsistent Locking Order Across Concurrent Transactions**
  - *Evidence Needed:* Deadlock graph in logs demonstrates Process A holds lock on Row 1 waiting for Row 2, while Process B holds lock on Row 2 waiting for Row 1.
- **Hypothesis 2: Long-Running Transaction Holding Row Locks Unnecessarily**
  - *Evidence Needed:* Blocking transaction has state `idle in transaction` while executing external HTTP calls or heavy computations before committing.
- **Hypothesis 3: High Concurrency Row Contention on Single Hotspot Record**
  - *Evidence Needed:* Multiple parallel workers competing to update the same counter, balance, or inventory ledger item simultaneously.

## Contradictory Evidence & Alternative Explanations
- If queries are failing with connection timeouts but `pg_stat_database_deadlocks` is zero and no blocking locks exist in `pg_locks`, the issue is network congestion or pool exhaustion, not locking.
- If table-level exclusive locks are present, check if an unindexed foreign key cascade or an automated schema migration (`ALTER TABLE`) was triggered during peak hours.

## Safe Mitigation & Rollback Guidance
- **Terminate Blocking Transaction:** Terminate the blocker causing cascading queue delays:
  ```sql
  SELECT pg_cancel_backend(blocking_pid); -- graceful cancel
  -- Or terminate if unresponsive:
  SELECT pg_terminate_backend(blocking_pid);
  ```
- **Configure Application Connection Timeouts:** Set lock and statement timeouts at the database/role level, or in application connection pool settings (e.g., SQLAlchemy `connect_args={"options": "-c lock_timeout=3s -c statement_timeout=5s"}`). Do not rely on session-scoped `SET` commands in an administrative `psql` session as they only affect that single session:
  ```sql
  -- Set role/database level defaults:
  ALTER ROLE orders_user SET lock_timeout = '3s';
  ALTER ROLE orders_user SET statement_timeout = '5s';
  -- Recycle application connection pool or restart service replicas to adopt updated settings.
  ```
- **Code Fix:** Enforce deterministic locking order (e.g. `SELECT ... FOR UPDATE` with sorted IDs: `ORDER BY id ASC FOR UPDATE`).
- **Shorten Transactions:** Move external API requests and email dispatches outside the database transaction block.

## Verification Steps & Escalation Criteria
- **Verification:** Verify `pg_locks` shows zero ungranted locks, deadlock count ceases incrementing, and order checkout success rate returns to 100%.
- **Escalation Criteria:** If deadlocks persist on critical transaction pathways or automated cancel fails to restore database throughput, escalate to Principal Backend Engineer (P1).
