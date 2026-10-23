# Runbook: CPU Saturation and Resource Contention
- **Runbook ID:** RB-010
- **Category:** CPU saturation and resource contention
- **Version:** 1.0.0
- **Applicable Services:** `api`, `orders`, `payments`, all hosts/containers
- **Keywords:** cpu saturation, throttling, cfs quota, high load average, noisy neighbor, spinlock, cpu contention, runqueue

## Symptoms
- Alert firing: `HostCPUSaturation` (> 90% CPU usage across all cores for > 3 minutes) or `ContainerCPUThrottled` (> 25% periods throttled).
- Sharp degradation in request processing times without increased database or network latency.
- Container response jitter: P50 latency remains reasonable while P99 latency balloons by 10x-50x.
- OS system load average significantly exceeds the number of allocated CPU cores.

## Required Observability Signals
- **Metrics:** `container_cpu_usage_seconds_total`, `container_cpu_cfs_throttled_periods_total`, `node_load1`, `process_cpu_seconds_total`
- **Logs:** Loki query `{service="api"} |= "throttled"` or system messages showing process scheduling delays.
- **Traces:** Traces show excessive self-time within application handler functions rather than waiting on external downstream spans.

## Diagnostic Steps
1. Determine whether saturation is user space (compute/regex/crypto) or kernel space (I/O wait, lock contention, context switches):
   ```bash
   top -b -n 1
   pidstat -u 1 5
   ```
2. Check CFS quota throttling metrics for Docker / Kubernetes containers:
   `rate(container_cpu_cfs_throttled_periods_total[5m]) / rate(container_cpu_cfs_periods_total[5m])`
3. Profile the running application using a sampling profiler (e.g. `py-spy` or `perf`) to identify the hot code path or infinite loop.
4. Check for noisy neighbor containers running on the same host node competing for CPU cycles.

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Inefficient Algorithm, Unindexed Loop, or Catastrophic Regex Backtracking**
  - *Evidence Needed:* Sampling profiler identifies 80%+ of CPU cycles concentrated in a single function, regular expression evaluation, or nested for-loop.
- **Hypothesis 2: Aggressive CPU CFS Quotas Causing Premature Throttling**
  - *Evidence Needed:* High throttled periods metric despite average container CPU usage appearing relatively modest (< 60%).
- **Hypothesis 3: High Traffic Concurrency Exceeding Available Compute Provisioning**
  - *Evidence Needed:* CPU usage correlates directly with incoming request rate (`http_requests_total`), and work per request remains constant.

## Contradictory Evidence & Alternative Explanations
- If high system load is accompanied by high `%iowait` (> 30%), the bottleneck is disk storage I/O, not CPU processing capability.
- If CPU spikes intermittently for only 1-2 seconds during health checks or garbage collection, do not alter capacity limits prematurely.

## Safe Mitigation & Rollback Guidance
- **Horizontal Scaling:** Deploy additional container replicas to distribute incoming request load:
  ```bash
  docker compose up -d --scale api=4
  ```
- **Adjust or Remove CFS Limits:** Relax overly restrictive CPU limits (or remove hard limits while keeping requests) to eliminate artificial micro-throttling.
- **Optimize Hot Path:** Replace ReDoS-vulnerable regular expressions with safe linear regex engines or direct string matching.
- **Offload Heavy Compute:** Move heavy cryptographic hashing, image resizing, or report generation to asynchronous background workers.

## Verification Steps & Escalation Criteria
- **Verification:** CPU utilization drops below 70%, CFS throttled periods metric falls to 0%, and P99 latency returns to nominal SLA.
- **Escalation Criteria:** If CPU saturation is caused by an active distributed denial of service (DDoS) attack, engage Cloud Security and CDN Edge Protection Teams (P1).
