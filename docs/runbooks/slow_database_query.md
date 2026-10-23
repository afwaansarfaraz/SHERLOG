# Runbook: Slow Database Queries and Index Degradation
- **Runbook ID:** RB-002
- **Category:** Slow SQL queries and index degradation
- **Version:** 1.2.0
- **Applicable Services:** `orders`, `payments`, `api`, PostgreSQL databases
- **Keywords:** postgresql, slow query, sequential scan, missing index, index bloat, pg_stat_statements, query plan, latency

## Symptoms
- Elevated database span durations in Jaeger distributed traces (> 1000ms for routine operations).
- Spike in PostgreSQL CPU utilization and Disk Read I/O.
- Application P99 latency degraded across endpoints touching order history or reporting.
- Loki logs show query execution warnings exceeding slow query threshold (`log_min_duration_statement = 250ms`).

## Required Observability Signals
- **Metrics:** `pg_stat_database_xact_commit`, `pg_stat_database_xact_rollback`, `db_query_duration_seconds{quantile="0.99"}`
- **Logs:** Loki query `{service="db"} |= "duration:"` or `{service="orders"} |= "statement timeout"`
- **Traces:** Jaeger trace spans showing SQL statement text with duration >= 1500ms on `db.statement`.

## Diagnostic Steps
1. Identify the top slow queries using `pg_stat_statements`:
   ```sql
   SELECT query, calls, total_exec_time / calls AS avg_time_ms, rows::numeric / calls AS avg_rows
   FROM pg_stat_statements
   ORDER BY total_exec_time DESC
   LIMIT 10;
   ```
2. For reviewed read-only queries (`SELECT`), generate an `EXPLAIN (ANALYZE, BUFFERS)` plan to check for sequential table scans (`Seq Scan`) instead of index scans. **Warning:** `EXPLAIN ANALYZE` actually executes the query; for write queries (`INSERT`, `UPDATE`, `DELETE`), running `EXPLAIN ANALYZE` will execute modifications and may cause duplicate side effects. Restrict `ANALYZE` to reviewed read-only queries, run write queries inside a rolled-back transaction (`BEGIN; EXPLAIN ANALYZE ...; ROLLBACK;`), or inspect them on a safe replica / test environment.
3. Check table and index statistics for dead tuples or stale statistics (`pg_stat_user_tables.n_dead_tup`).
4. Verify if database table size grew rapidly without corresponding index maintenance.

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Missing Index on Frequently Filtered/Joined Column**
  - *Evidence Needed:* `EXPLAIN ANALYZE` shows `Seq Scan` on a large table with filter condition on an unindexed column (e.g. `customer_id`, `created_at`).
- **Hypothesis 2: Stale Statistics Leading to Suboptimal Query Planner Choice**
  - *Evidence Needed:* Large discrepancy between estimated rows and actual rows in `EXPLAIN ANALYZE`, and `last_analyze` timestamp is older than recent table bulk updates.
- **Hypothesis 3: High Table Bloat or Index Fragmentation**
  - *Evidence Needed:* High `n_dead_tup` ratio (> 20%) in `pg_stat_user_tables` and high shared buffer hit misses.

## Contradictory Evidence & Alternative Explanations
- If query execution time is normal when executed directly on the database CLI but application latency is high, the delay is due to network serialization, connection acquisition wait, or application ORM overhead.
- If all queries are slow simultaneously regardless of table, inspect database server CPU throttling, memory swapping, or hardware disk I/O saturation.

## Safe Mitigation & Rollback Guidance
- **Immediate Index Creation:** Create index concurrently to prevent table write locks:
  ```sql
  CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_customer_created ON orders (customer_id, created_at DESC);
  ```
- **Update Statistics:** Run `ANALYZE orders;` to refresh optimizer histogram statistics.
- **Vacuum Dead Tuples:** Run `VACUUM (VERBOSE, ANALYZE) orders;` during non-peak load.
- **Application Workaround:** Temporarily add pagination limits (e.g. `LIMIT 50`) on unbound list endpoints.

## Verification Steps & Escalation Criteria
- **Verification:** Confirm average query execution time on `pg_stat_statements` drops below 50ms, endpoint P95 latency normalizes, and no unexpected sequential scans appear on the affected tables.
- **Escalation Criteria:** If `CREATE INDEX CONCURRENTLY` blocks or deadlocks with long-running transactions, or query plan fails to change after statistics refresh, escalate to Senior DBA (P2).
