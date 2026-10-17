# Historical Incident Catalog & Postmortems

## Incident INC-2026-001: Orders Service Connection Pool Starvation
- Service: `orders`
- Date: 2026-08-14
- Root Cause: `database_connection_pool_exhaustion`
- Summary: During promotional flash sale, concurrent order submissions spiked from 20 req/s to 120 req/s. Database pool size was capped at 10 with max overflow 10. Queue pool limit was exceeded within 45 seconds, resulting in HTTP 500 error cascade.
- Evidence Observed:
  - Metric: `db_pool_active = 20`, saturation = 100%.
  - Log: `QueuePool limit of size 10 overflow 10 reached, connection timed out`.
  - Trace: Latency p95 jumped to 3400ms.
- Remediation: Increased `DATABASE_POOL_SIZE` to 30 and `DATABASE_MAX_OVERFLOW` to 20; restarted orders container.

---

## Incident INC-2026-002: Payments Gateway Gateway Timeout
- Service: `payments`
- Date: 2026-09-02
- Root Cause: `downstream_dependency_timeout`
- Summary: Downstream payment provider experienced degraded API processing times exceeding 5000ms. Orders service had no circuit breaker and waited for full socket read timeout, exhausting available worker threads.
- Evidence Observed:
  - Trace: `/payments/charge` span duration 5002ms with `error=true`.
  - Log: `httpx.ReadTimeout: The read operation timed out`.
- Remediation: Configured client timeout deadline to 3s with graceful fallback message to customer; scaled payments container replicas.

---

## Incident INC-2026-003: Unindexed Customer Orders Query
- Service: `orders`
- Date: 2026-09-18
- Root Cause: `slow_database_query`
- Summary: New customer history endpoint executed unfiltered sequential table scan across 500k rows in orders table.
- Evidence Observed:
  - Metric: Database query latency p95 = 4200ms.
  - Log: `duration: 3821.432 ms  statement: SELECT * FROM orders WHERE customer_id = ...`.
- Remediation: Added composite B-tree index `CREATE INDEX idx_orders_customer ON orders (customer_id, created_at DESC)`.
