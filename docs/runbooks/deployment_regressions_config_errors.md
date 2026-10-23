# Runbook: Deployment Regressions and Configuration Errors
- **Runbook ID:** RB-011
- **Category:** Deployment regressions and configuration errors
- **Version:** 1.0.0
- **Applicable Services:** All services (`api`, `orders`, `payments`, gateway)
- **Keywords:** deployment regression, bad release, config drift, env var missing, migration error, rollback, git sha, bad deployment

## Symptoms
- Immediate spike in error rates, crash loops, or degraded latency coinciding within 5 minutes of a new deployment or configuration sync.
- Services failing startup health probes due to missing environment variables, invalid configuration syntax, or failed database migrations.
- Version mismatch between frontend static bundles and backend API contracts leading to client-side 400 Bad Request errors.
- Git deployment commit metadata showing recent pipeline execution prior to incident trigger.

## Required Observability Signals
- **Metrics:** `sherlog_app_info{version=~".*"}`, `deployment_timestamp_seconds`, `http_requests_total{status="500"}`, `container_start_time_seconds`
- **Logs:** Loki query `{service=~".*"} |= "KeyError"` or `{service=~".*"} |= "ConfigurationError"` or `{service=~".*"} |= "alembic"`
- **Traces:** Traces showing new code pathways failing with unhandled type errors or configuration exceptions.

## Diagnostic Steps
1. Identify the exact commit SHA and image tag deployed most recently across all services:
   ```bash
   git log -n 3 --oneline
   docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
   ```
2. Compare environment variables and config maps against the previous known-good baseline configuration to detect config drift.
3. Check database migration history to verify if a pending Alembic migration was skipped, failed halfway, or introduced schema locks:
   ```bash
   alembic current
   alembic history --verbose -r-3:head
   ```
4. Verify if any required feature flag, API key, or credential was omitted from the deployment secrets manager.

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Missing or Malformed Required Environment Variable**
  - *Evidence Needed:* Startup error log reports `KeyError: 'REDIS_URL'` or `pydantic.ValidationError` on configuration loading.
- **Hypothesis 2: Backward-Incompatible Schema Migration**
  - *Evidence Needed:* SQL error `column "x" does not exist` or `relation "y" does not exist` occurring immediately after release.
- **Hypothesis 3: Buggy Code Regression in New Release Commit**
  - *Evidence Needed:* Exception traceback directly references a source code file or function that was introduced or modified in the most recent pull request.

## Contradictory Evidence & Alternative Explanations
- If the incident began several hours after deployment during a known traffic spike, the issue is capacity or external dependency failure rather than release regression.
- If only one specific user or tenant encounters errors while all others succeed, inspect tenant-specific corrupted data or custom permissions.

## Safe Mitigation & Rollback Guidance
- **Targeted Service Rollback:** Roll back the affected service to the verified previous stable tag approved for the target deployment without bringing down the entire platform:
  ```bash
  # Check out verified previous stable release tag approved for target deployment:
  git checkout tags/<PREVIOUS_STABLE_TAG>
  # Rebuild and restart only the affected service (avoid project-wide downtime):
  docker compose up -d --no-deps <affected_service>
  ```
- **Database Migration Rollback / Forward Fix:** Before running any downgrade, verify that the revision's `downgrade()` implementation preserves required production data and supports the rolled-back application version. If the downgrade drops columns/tables with production data or is unverified, execute an emergency forward fix or tested point-in-time recovery procedure:
  ```bash
  # Run ONLY after confirming downgrade() preserves required data:
  alembic downgrade -1
  ```
- **Hot-Add Missing Config:** If the failure is purely a missing environment variable, inject the variable into the `.env` configuration and restart the container without code modification.

## Verification Steps & Escalation Criteria
- **Verification:** Confirm all containers report healthy status (`docker ps`), error rates drop back to pre-deployment baseline (<0.05%), and end-to-end smoke tests pass.
- **Escalation Criteria:** If a database migration dropped or altered data irrecoverably, freeze writes, notify the Disaster Recovery Team, and restore from point-in-time recovery backup (P0).
