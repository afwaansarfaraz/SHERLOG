# Runbook: Downstream Dependency Timeout & Cascade Failure

## Service Identification
- Primary Service: `orders`
- Downstream Dependency: `payments` (HTTP `/payments/charge`)

## Symptoms & Observability Signals
- HTTP Status: Elevated HTTP 504 Gateway Timeout or HTTP 502 Bad Gateway observed on orders service.
- Distributed Traces: Jaeger trace root span `/orders` shows child span `POST /payments/charge` exceeding timeout deadline (> 5000ms).
- Logs: Client-side timeout errors in orders service logs: `httpx.TimeoutException`, `ReadTimeout`, or `connection reset by peer`.
- Metrics: Downstream error rate metric `downstream_requests_failed_total{service="orders",target="payments"}` spike.

## Root Cause Analysis
1. Downstream `payments` microservice experiencing internal latency degradation, deadlocks, or lock contention.
2. Network connectivity degradation or packet loss between microservice containers.
3. Unbounded client timeout configuration allowing requests to hang indefinitely and block worker threads.

## Investigation Steps
1. Query Jaeger traces for `service=orders` with `tags.error=true` to isolate slow or failing spans.
2. Check `payments` service health metrics, CPU utilization, and logs for internal exceptions.
3. Verify recent deployments or configuration updates in `payments` or API gateway routing.

## Verified Remediation Actions
- Action: Scale `payments` service container replica count.
- Action: Restart degraded `payments` service container.
- Action: Adjust circuit breaker threshold and downstream timeout to fail fast with fallback.
