# Runbook: PostgreSQL Database Connection Pool Exhaustion

## Service Identification
- Primary Service: `orders`
- Secondary Impacted Services: `payments`, `api`

## Symptoms & Observability Signals
- PromQL Metric: `db_pool_active / db_pool_max > 0.90` indicating connection pool saturation.
- HTTP Status: Elevated HTTP 500 Internal Server Errors on order creation endpoints (`/orders`, `/checkout`).
- Logs: PostgreSQL driver log errors containing `QueuePool limit of size X overflow Y reached`, `connection timeout`, or `pool exhausted`.
- Latency: P95 and P99 latency spikes on database-backed transactions.

## Root Cause Analysis
1. Insufficient connection pool size configured relative to incoming request concurrency.
2. Long-running or blocked database queries holding connections open without releasing them back to the pool.
3. Connection leak caused by missing `session.close()` or unhandled exceptions bypassing resource cleanup.

## Investigation Steps
1. Query Prometheus metric `db_pool_active` and `db_pool_max` to confirm saturation ratio.
2. Inspect Loki logs for the `orders` service filtering for `database`, `pool`, or `connection`.
3. Check Jaeger traces for database spans exceeding expected duration or showing error tags.
4. Check recent git commits for changes to database session management or configuration defaults.

## Verified Remediation Actions
- Action: Increase `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW` in service environment configuration.
- Action: Restart `sherlog-orders` service container to purge leaked or hung pool connections.
- Long-term: Optimize transaction boundaries and enforce context-managed session closure.
