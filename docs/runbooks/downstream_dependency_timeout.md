# Runbook: Downstream Dependency Timeout & Cascade Failure
- **Runbook ID:** RB-005
- **Category:** Downstream dependency timeouts
- **Version:** 1.2.0
- **Applicable Services:** `orders`, `payments`, `api`, all microservice inter-service clients
- **Keywords:** downstream timeout, cascade failure, circuit breaker, httpx, ReadTimeout, 504 Gateway Timeout, payments service

## Symptoms
- Elevated HTTP 504 Gateway Timeout or HTTP 502 Bad Gateway observed on upstream services (`orders`).
- Distributed Traces: Jaeger trace root span `/orders` shows child span `POST /payments/charge` exceeding timeout deadline (> 5000ms).
- Logs: Client-side timeout errors in upstream service logs: `httpx.TimeoutException`, `ReadTimeout`, or `connection reset by peer`.
- Metrics: Downstream error rate metric `downstream_requests_failed_total{service="orders",target="payments"}` spikes.

## Required Observability Signals
- **Metrics:** `downstream_requests_duration_seconds{quantile="0.99"}`, `downstream_requests_failed_total`, `circuit_breaker_state`
- **Logs:** Loki query `{service="orders"} |= "TimeoutException"` or `{service="orders"} |= "payments"`
- **Traces:** Jaeger trace query `service=orders` filtering for `error=true` and child span `target.service=payments`.

## Diagnostic Steps
1. Query Jaeger traces for `service=orders` with `tags.error=true` to isolate slow or failing spans.
2. Check `payments` service health metrics, CPU utilization, thread pool usage, and logs for internal exceptions.
3. Check network latency and packet drop rates between upstream and downstream containers.
4. Verify whether recent deployments or configuration updates in `payments` or the API gateway introduced regression.

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Downstream Service Resource Starvation or Internal Lockup**
  - *Evidence Needed:* `payments` service CPU/memory is at 100%, or thread pool is exhausted waiting on its own dependencies.
- **Hypothesis 2: Missing or Overly Generous Client Timeout Causing Upstream Worker Starvation**
  - *Evidence Needed:* Upstream `orders` worker threads accumulate in blocked state waiting 30+ seconds for downstream responses, causing upstream thread pool depletion.
- **Hypothesis 3: Network Interconnect Failure or DNS Resolution Latency**
  - *Evidence Needed:* Connection establishment phase takes >3000ms in traces while downstream service shows zero incoming request logs.

## Contradictory Evidence & Alternative Explanations
- If downstream `payments` service reports normal 200 OK responses with sub-50ms latency in its own access logs, inspect intermediary reverse proxies, service mesh sidecars, or load balancers for dropped connections.
- If upstream errors are HTTP 400 Bad Request or HTTP 422 Unprocessable Entity, the issue is schema contract incompatibility rather than timeout.

## Safe Mitigation & Rollback Guidance
- **Immediate Mitigation:** Trip circuit breaker to OPEN state or enable cached/graceful degradation fallback to reject/queue downstream calls immediately without tying up worker threads.
- **Scale Downstream:** Scale `payments` service container replica count (`docker compose up --scale payments=3 -d`).
- **Restart Degraded Container:** Restart degraded `sherlog-payments` service container to clear deadlocked event loops.
- **Adjust Timeout Configuration & Idempotent Retries:** Reduce downstream client timeout to fail fast (e.g., reduce from 30s to 3s with retry exponential backoff). For `POST /payments/charge` retries, require every retry attempt to strictly reuse the exact same idempotency key as the original request, including when `orders` times out before receiving a response, to guarantee no duplicate charges occur.

## Verification Steps & Escalation Criteria
- **Verification:** Upstream HTTP 504 errors drop to zero, downstream P99 latency returns within SLA (< 200ms), and circuit breaker closes to CLOSED state.
- **Escalation Criteria:** If downstream dependency is a 3rd party external provider (e.g. Stripe, Twilio) that is globally down, activate offline payment queue processing and notify Operations Lead (P1).
