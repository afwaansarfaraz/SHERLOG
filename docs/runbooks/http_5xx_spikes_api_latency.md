# Runbook: HTTP 5xx Spikes and API Latency Degradation
- **Runbook ID:** RB-006
- **Category:** HTTP 5xx spikes and API latency
- **Version:** 1.0.0
- **Applicable Services:** `api`, `orders`, `payments`, API Gateway
- **Keywords:** http 500, http 502, latency spike, p99 latency, unhandled exception, apm, reverse proxy, uvicorn, error rate

## Symptoms
- Alert firing: `HighHTTP5xxErrorRate` (> 5% of all incoming requests returning 5xx status codes over a 2-minute window).
- P95 / P99 API response latency exceeds 2500ms on core gateway routes.
- Front-end clients experiencing connection timeouts, blank views, or retry storms.
- Load balancer or reverse proxy logging HTTP 502 Bad Gateway or 503 Service Unavailable.

## Required Observability Signals
- **Metrics:** `http_requests_total{status=~"5.."}[1m]`, `http_request_duration_seconds{quantile="0.99"}`, `up{job="api"}`
- **Logs:** Loki query `{service="api"} |= "ERROR"` or `{service="api"} |= "Traceback"`
- **Traces:** Jaeger trace query `service=api` with status `error=true` showing the root span exception details.

## Diagnostic Steps
1. Filter Loki logs by `status >= 500` and group by error message / Python traceback.
2. Cross-reference HTTP error timestamps with recent deployment events, configuration pushes, or database migrations.
3. Check CPU, memory, and file descriptor limits on the application containers running the affected service.
4. Check whether errors originate inside the application code (HTTP 500) vs. in the gateway/reverse proxy (HTTP 502 / 503 / 504).

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Unhandled Runtime Exception from Malformed Request or Bad Release**
  - *Evidence Needed:* Identical Python exception traceback appearing in logs across multiple workers following a recent release tag.
- **Hypothesis 2: Upstream Worker Starvation or Process Crash Under Load**
  - *Evidence Needed:* Uvicorn / Gunicorn worker timeout errors (`Worker failed to boot`, `WORKER TIMEOUT`) and HTTP 502 returned by upstream reverse proxy.
- **Hypothesis 3: Synchronous Blocking I/O in Async Event Loop**
  - *Evidence Needed:* Event loop lag metrics spike to seconds while CPU utilization remains moderate; trace shows synchronous filesystem or external network calls inside async route handlers.

## Contradictory Evidence & Alternative Explanations
- If HTTP status codes are 401 Unauthorized or 403 Forbidden, the issue is authentication token expiry or IAM permission drift, not an operational outage.
- If HTTP 5xx errors occur exclusively from a single client IP address sending corrupted payloads, consider edge WAF filtering or schema validation adjustments rather than service-wide rollback.

## Safe Mitigation & Rollback Guidance
- **Immediate Rollback:** If triggered immediately following a deployment, execute canary rollback to the previous stable container image tag immediately.
- **Worker Scaling:** Increase worker count or replica pods to handle concurrency surges:
  ```bash
  docker compose up -d --scale api=3
  ```
- **Hot-Patch Unhandled Exception:** If error is caused by null pointer on optional payload field, deploy hotfix adding safe fallback handling or default dictionary access.
- **Restart Failing Workers:** Issue zero-downtime rolling restart of affected application instances.

## Verification Steps & Escalation Criteria
- **Verification:** Calculate the 5xx error fraction as `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` and confirm it drops below the 0.1% threshold (< 0.001), while verifying endpoint P95 latency is restored below 200ms.
- **Escalation Criteria:** If 5xx error rate remains >10% for longer than 15 minutes and root cause cannot be isolated in trace logs, escalate to Service Team Lead (P1).
