# Runbook: Slow Database Queries and Index Degradation

## Service Identification
- Primary Service: `orders`, `payments`
- Impacted Infrastructure: PostgreSQL Database

## Symptoms & Observability Signals
- Latency Metrics: P95 and P99 latency exceeding 2000ms on database read/write queries.
- CPU Utilization: Elevated PostgreSQL CPU usage (> 80%) with sequential scans.
- Slow Query Logs: Database logs recording queries with `duration > 1000ms` on `orders` or `payments` tables.
- Alert: `SlowDatabaseQueryAlert` triggered via Alertmanager.

## Root Cause Analysis
1. Missing index on filtered columns such as `orders.customer_id` or `payments.status`.
2. Inefficient query plan performing sequential scans across large tables without partition pruning.
3. Lock contention or lock waits on concurrent row updates.

## Investigation Steps
1. Execute `EXPLAIN ANALYZE` on slow queries reported in PostgreSQL query logs.
2. Check PostgreSQL index usage statistics via `pg_stat_user_indexes`.
3. Check Jaeger spans tagged with `db.statement` for slow execution duration.

## Verified Remediation Actions
- Action: Create missing database indexes on query filter columns.
- Action: Optimize SQL query structure or add query limit and pagination.
- Action: Kill long-running blocking query sessions if holding table locks.
