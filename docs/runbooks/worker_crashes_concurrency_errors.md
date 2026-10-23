# Runbook: Worker Crashes and Concurrency Misconfiguration
- **Runbook ID:** RB-008
- **Category:** Worker crashes and concurrency misconfiguration
- **Version:** 1.0.0
- **Applicable Services:** `worker`, `api`, `orders`, multi-process/thread services
- **Keywords:** worker crash, segfault, concurrency, GIL, race condition, crash loop, SIGKILL, exit code 137, thread pool

## Symptoms
- Worker containers entering `CrashLoopBackOff` or restarting repeatedly every few minutes.
- Process exit code `137` (SIGKILL / OOM killer) or exit code `139` (SIGSEGV / segmentation fault).
- Intermittent race conditions resulting in duplicate processing, corrupted state, or lost jobs.
- Sudden drops in healthy instance count in service discovery / load balancer target groups.

## Required Observability Signals
- **Metrics:** `process_resident_memory_bytes`, `container_restarts_total`, `thread_count`, `active_workers_gauge`
- **Logs:** Loki query `{service="worker"} |= "SIGSEGV"` or `{service="worker"} |= "Killed"` or container exit reasons via `docker inspect`
- **Traces:** Traces showing abrupt termination without closing span tags or HTTP 502 returned to clients.

## Diagnostic Steps
1. Inspect container exit status and logs immediately prior to restart:
   ```bash
   docker inspect --format='{{.State.ExitCode}} - {{.State.Error}}' sherlog-worker
   docker logs --tail 100 sherlog-worker
   ```
2. Check for race conditions in shared memory or global state: verify if shared dictionaries, database sessions, or network sockets are accessed across threads without locks.
3. Review concurrency configuration (e.g. `WORKERS=16` on a 1-vCPU container leading to thread thrashing and scheduler latency).
4. Verify whether C-extensions (e.g., tokenizers, native crypto, image processing libraries) are triggering segmentation faults.

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Concurrency Over-Allocation Causing Thread Starvation and CPU Thrashing**
  - *Evidence Needed:* High thread count (> 200) on constrained container, high context-switch rate, and latency spikes without corresponding throughput gains.
- **Hypothesis 2: Unsafe Thread Sharing of Non-Thread-Safe Database Sessions**
  - *Evidence Needed:* SQLAlchemy errors reporting `InvalidRequestError: This Session's transaction has been rolled back due to previous exception` or cross-thread session reuse.
- **Hypothesis 3: Kernel OOM Killer Invocation Due to Memory Spike**
  - *Evidence Needed:* Exit code 137, `dmesg -T` showing `Out of memory: Killed process`, and memory graph showing sharp vertical rise before collapse.

## Contradictory Evidence & Alternative Explanations
- If the container exited with code 0, it was gracefully shut down by a scheduler scale-in event or manual deployment, not a crash.
- If worker processes fail health checks but do not restart, check if the health check timeout is too strict or health check endpoint is blocked by a synchronous task.

## Safe Mitigation & Rollback Guidance
- **Tune Concurrency Setting:** Confirm the deployed execution model (asyncio event loop, thread pool, or multi-process queue). Note that `2 * CPU_CORES + 1` is strictly a starting heuristic for synchronous WSGI/Gunicorn servers, not a universal rule for asynchronous services (like FastAPI/Uvicorn) or background worker queues. Tune worker and thread counts based on measured CPU saturation, memory limits, and whether the workload is I/O-bound or CPU-bound.
- **Enforce Thread-Local Storage:** Ensure database sessions and API clients are created scoped per task/thread rather than globally.
- **Increase Container Resource Limits:** Raise memory limit to give workers sufficient headroom during peak load spikes.
- **Rollback Faulty Native Dependency:** If crash began after bumping a native library version, downgrade to the previously verified binary.

## Verification Steps & Escalation Criteria
- **Verification:** Container uptime stabilizes > 1 hour without unexpected restarts, restart count metric plateaus, and zero SIGSEGV/SIGKILL entries appear in logs.
- **Escalation Criteria:** If segmentation faults persist despite clean dependencies and memory limits, notify Core Platform Engineering (P1).
