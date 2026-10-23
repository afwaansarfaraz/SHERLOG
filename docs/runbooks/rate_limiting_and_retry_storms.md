# Runbook: Rate Limiting and Retry Storms
- **Runbook ID:** RB-013
- **Category:** Rate limiting and retry storms
- **Version:** 1.0.0
- **Applicable Services:** `api`, `orders`, `payments`, external SaaS integrations
- **Keywords:** rate limit, 429 Too Many Requests, retry storm, thundering herd, exponential backoff, jitter, token bucket

## Symptoms
- Outbound API calls to external vendors or interservice microservices returning HTTP `429 Too Many Requests`.
- Request volume to downstream services exhibiting exponential amplification following a minor blip.
- Clients aggressively retrying failed requests in tight loops without delay, exhausting server connection pools and CPU.
- Headers present: `Retry-After: 60`, `X-RateLimit-Remaining: 0`.

## Required Observability Signals
- **Metrics:** `http_requests_total{status="429"}`, `client_retries_total`, `rate_limit_tokens_remaining`
- **Logs:** Loki query `{service="orders"} |= "429 Too Many Requests"` or `{service="orders"} |= "rate limit exceeded"`
- **Traces:** Traces showing cascading fan-out of 5-10 duplicate request spans originating from a single user action.

## Diagnostic Steps
1. Inspect the rate limiting headers returned by the failing endpoint:
   ```bash
   curl -i http://localhost:8000/orders
   ```
2. Check client retry configurations: verify if clients implement exponential backoff with full jitter, or if they retry immediately on fixed intervals.
3. Determine whether rate limiting is enforced by internal token bucket limiters (Redis-based) or by upstream third-party APIs.
4. Verify whether a single rogue tenant or scheduled batch cron is flooding the endpoint.

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Client Missing Exponential Backoff & Jitter (Retry Storm)**
  - *Evidence Needed:* Incoming traffic rate triples or quadruples immediately following a transient 500ms blip, with repetitive duplicate idempotency tokens.
- **Hypothesis 2: Misconfigured or Excessively Restrictive Rate Limit Threshold**
  - *Evidence Needed:* Legitimate regular user journeys hitting 429 errors during normal business hours without malicious intent.
- **Hypothesis 3: Rogue Script or Unauthenticated Scraper Consuming Global Token Bucket**
  - *Evidence Needed:* Single IP address or API key responsible for > 80% of total consumed rate limit tokens.

## Contradictory Evidence & Alternative Explanations
- If status codes are 503 or 504 without 429 headers, the service is overloaded or down, but not deliberately rate limiting.
- If only unauthenticated routes return 429, check if DDoS protection at Cloudflare/Fastly has been triggered.

## Safe Mitigation & Rollback Guidance
- **Enforce Full Jitter Backoff:** Update client retry logic to implement full jitter: if no `Retry-After` header is present, choose a uniform random sleep between 0 and the capped exponential backoff (`sleep = random(0, min(max_backoff, base * 2^attempt))`); when `Retry-After` is present, honor that duration as the minimum delay and add randomized jitter on top (`sleep = retry_after + random(0, jitter_window)`).
- **Enforce Idempotency & Circuit Breaking:** Reject retries when downstream is in degraded state to stop the storm.
- **Tune Internal Rate Limit Quotas:** First confirm that 429 errors originate from the internal rate limiter (rather than upstream external vendors) and that the deployed limiter reads `rate_limit:quota:<service>`. Verify downstream service capacity can handle higher throughput before raising limits:
  ```bash
  # Apply only for internal limiter when downstream capacity allows:
  redis-cli set rate_limit:quota:orders 5000
  ```
- **Block Rogue Consumer:** Apply temporary IP rate limiting or revoke API key of the rogue caller at the gateway level.

## Verification Steps & Escalation Criteria
- **Verification:** HTTP 429 rate drops to zero, duplicate request amplification ceases, and client success rate returns to >99.9%.
- **Escalation Criteria:** If a critical payment gateway or regulatory API has hard-blocked company IP addresses due to retry spam, escalate immediately to Executive Incident Commander (P0).
