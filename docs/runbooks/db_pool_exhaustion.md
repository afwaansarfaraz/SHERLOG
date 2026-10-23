# Runbook: PostgreSQL Database Connection Pool Exhaustion
- **Runbook ID:** RB-001
- **Category:** Database connection pool exhaustion
- **Version:** 1.2.0
- **Applicable Services:** `orders`, `payments`, `api`, all database-backed backend services
- **Keywords:** postgresql, connection pool, pool exhaustion, QueuePool, max_overflow, db_pool_active, timeout, pg_stat_activity

## Symptoms
- PromQL Metric: `db_pool_active / db_pool_max > 0.90` indicating connection pool saturation.
- HTTP Status: Elevated HTTP 500 Internal Server Errors on order creation endpoints (`/orders`, `/checkout`).
- Logs: PostgreSQL driver log errors containing `QueuePool limit of size X overflow Y reached`, `connection timeout`, or `pool exhausted`.
- Latency: P95 and P99 latency spikes on database-backed transactions.

## Required Observability Signals
- **Metrics:** `db_pool_active{service="orders"}`, `db_pool_max{service="orders"}`, `http_requests_total{status=~"5.."}`
- **Logs:** Loki query `{service="orders"} |= "QueuePool"` or `{service="orders"} |= "connection timeout"`
- **Traces:** Jaeger trace spans for `db.statement` showing duration exceeding 3000ms or throwing pool acquisition timeout exceptions.

## Diagnostic Steps
1. Query Prometheus metric `db_pool_active` and `db_pool_max` to confirm saturation ratio.
2. Inspect Loki logs for the target service filtering for `database`, `pool`, or `connection timeout`.
3. Check Jaeger traces for database spans exceeding expected duration or showing pool wait errors.
4. Inspect active database sessions via `SELECT count(*), state FROM pg_stat_activity GROUP BY state;`.
5. Check recent git commits or configuration changes for pool size decreases or missing `session.close()` patterns.

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Connection Leak in Application Code**
  - *Evidence Needed:* Active pool connections remain at ceiling even when incoming HTTP traffic drops to near zero.
- **Hypothesis 2: Sudden Concurrency Spike Overwhelming Pool**
  - *Evidence Needed:* Sharp correlation between `http_requests_total` rate increase and pool saturation; query execution time remains normal.
- **Hypothesis 3: Long-Running or Blocked Queries Holding Connections**
  - *Evidence Needed:* Elevated `pg_stat_activity` duration, slow query logs, or lock wait events while connections are active.

## Contradictory Evidence & Alternative Explanations
- If `db_pool_active` is low (< 50%) but HTTP 500 errors occur, the failure is NOT pool exhaustion (check application exceptions, syntax errors, or downstream API timeouts).
- If PostgreSQL server CPU or memory is at 100%, the root cause is database server resource starvation rather than an application-level pool leak.

## Safe Mitigation & Rollback Guidance
- **Immediate Mitigation:** Compare aggregate pool limits across all service replicas (`sum(replicas * (pool_size + max_overflow))`) against PostgreSQL's available connection headroom (`SHOW max_connections;` minus current active connections). Increase `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW` only when capacity safely allows without exceeding server limits.
- **Service Restart:** Restart target service container (e.g. `docker restart sherlog-orders`) to flush leaked or orphaned pool connections.
- **Database Level:** Identify affected sessions and terminate only confirmed blocking sessions for the affected service rather than running a cluster-wide termination query: inspect blockers via `SELECT pid, state, state_change, query, pg_blocking_pids(pid) FROM pg_stat_activity WHERE application_name = '<service>' AND state = 'idle in transaction';` and terminate confirmed blockers using `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name = '<service>' AND state = 'idle in transaction' AND pid IN (SELECT unnest(pg_blocking_pids(w.pid)) FROM pg_stat_activity w WHERE w.wait_event_type = 'Lock');`.
- **Rollback:** If a recent deployment introduced session handling changes, revert to previous stable container image tag.

## Verification Steps & Escalation Criteria
- **Verification:** Confirm `db_pool_active / db_pool_max` drops below 0.60, HTTP 500 rate returns to 0%, and transaction latencies stabilize at baseline P95 (< 150ms).
- **Escalation Criteria:** If pool exhaustion recurs within 10 minutes post-restart or database reports max connections exceeded across all services, escalate to Database Infrastructure On-Call (P1).
