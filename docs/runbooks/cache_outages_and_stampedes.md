# Runbook: Cache Outages and Cache Stampedes
- **Runbook ID:** RB-004
- **Category:** Cache outages and cache stampedes
- **Version:** 1.0.0
- **Applicable Services:** `api`, `orders`, `redis-cache`, all distributed caching layers
- **Keywords:** redis, cache miss, cache stampede, dog-piling, thundering herd, cache eviction, latency spike, redis down

## Symptoms
- Sudden collapse in cache hit ratio from >95% to near 0%.
- Simultaneous spike in downstream primary database CPU, active connections, and read latency.
- Redis server unavailable, unresponsive (OOM command errors), or connection refused on port 6379.
- Cascade latency spikes across user-facing API endpoints relying on cached product catalogs or sessions.

## Required Observability Signals
- **Metrics:** `redis_connected_clients`, `redis_used_memory_bytes`, `redis_keyspace_hits_total`, `redis_keyspace_misses_total`
- **Logs:** Loki query `{service="redis"} |= "OOM"` or `{service="api"} |= "RedisConnectionError"`
- **Traces:** Jaeger trace spans showing missing cache hits followed immediately by hundreds of concurrent identical SQL queries.

## Diagnostic Steps
1. Verify Redis connectivity and operational status:
   ```bash
   redis-cli -h redis-cache ping
   redis-cli -h redis-cache info memory
   ```
2. Check cache hit ratio in Prometheus:
   `rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))`
3. Inspect whether key expiration aligned with a single synchronized timestamp (thundering herd effect).
4. Verify if Redis maxmemory policy (`maxmemory-policy volatile-lru` or `allkeys-lru`) is active and evicting hot keys prematurely.

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Cache Stampede (Thundering Herd) on High-Traffic Key Expiration**
  - *Evidence Needed:* A popular cached key (e.g., product catalog or configuration) expired without probabilistic early recomputation, causing thousands of concurrent requests to hit the database.
- **Hypothesis 2: Redis Out of Memory (OOM) Termination or Rejection**
  - *Evidence Needed:* Redis log contains `OOM command not allowed when used memory > 'maxmemory'`, or container restart due to cgroup memory limit.
- **Hypothesis 3: Network Partition or Redis Crash**
  - *Evidence Needed:* Application logs report `ConnectionRefusedError: [Errno 111] Connection refused` or `TimeoutError`.

## Contradictory Evidence & Alternative Explanations
- If cache hit ratio remains >90% but database latency spikes, the issue is not cache stampede (investigate un-cached query degradation or batch jobs).
- If Redis is responding with PONG within 1ms and memory is healthy (<60%), verify client connection pool settings in the application config.

## Safe Mitigation & Rollback Guidance
- **Immediate Mitigation (Thundering Herd):** Enable probabilistic early expiration (XFetch algorithm) or distributed lock / single-flight request coalescing (`mutex` on cache miss).
- **Redis OOM Relief:** Temporarily increase Redis `maxmemory` or purge non-critical ephemeral keys:
  ```bash
  redis-cli config set maxmemory 2gb
  ```
- **Fallback Circuit Breaker:** Enable stale-while-revalidate caching fallback so the application returns slightly stale data rather than crashing the primary database.
- **Warm the Cache:** Execute a controlled priming script to re-populate key hot keys sequentially before releasing full traffic.

## Verification Steps & Escalation Criteria
- **Verification:** Cache hit ratio restores above 90%, Redis memory stays within budget (<75% maxmemory), and database connection pressure recedes to normal baselines.
- **Escalation Criteria:** If Redis node is unrecoverable or cluster data corruption is suspected, initiate failover to standby replica and notify Infrastructure Lead (P1).
