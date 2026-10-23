# Runbook: Memory Leaks and Out-Of-Memory (OOM) Events
- **Runbook ID:** RB-009
- **Category:** Memory leaks and out-of-memory events
- **Version:** 1.0.0
- **Applicable Services:** `api`, `orders`, `worker`, all containerized services
- **Keywords:** memory leak, oom killer, cgroups, heap memory, garbage collection, exit code 137, rss memory, tr Diamond

## Symptoms
- Monotonically increasing Resident Set Size (RSS) memory over hours or days without returning to baseline after traffic dips.
- Frequent container restarts with exit code `137` (SIGKILL signal). Note that while exit code 137 is produced when the Linux kernel OOM killer terminates a process, manual kills (`docker kill`, `kill -9`), container stop timeouts, or Docker daemon restarts also produce exit code 137; kernel or container OOM evidence (`OOMKilled: true` or `dmesg` OOM logs) is required before confirming an OOM event.
- High memory swap activity causing severe response latency degradation across all service routes.
- Garbage collection pauses (GC stop-the-world) stretching into hundreds of milliseconds.

## Required Observability Signals
- **Metrics:** `container_memory_working_set_bytes`, `container_memory_rss`, `process_resident_memory_bytes`, `go_memstats_alloc_bytes` / `python_gc_collections_total`
- **Logs:** Loki query `{service="api"} |= "MemoryError"` or host system logs `{container="sherlog-api"} |= "oom-killer"`
- **Traces:** Requests timing out or hanging during payload serialization / large file buffering in memory.

## Diagnostic Steps
1. Plot memory consumption over the last 24-72 hours in Prometheus/Grafana: verify if the curve is a "sawtooth" pattern (normal GC) or a continuous upward ramp (memory leak).
2. Inspect the Docker/Kubernetes container memory limits:
   ```bash
   docker stats --no-stream
   ```
3. Take a heap snapshot or inspect process object allocations (e.g., using `tracemalloc` in Python or `pprof` in Go).
4. Review recent code changes for unbounded collections, module-level global caches without TTL/eviction, or circular references with `__del__`.

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Unbounded In-Memory Cache or Global Dictionary Growth**
  - *Evidence Needed:* Heap profile shows millions of dictionary/list entries accumulating in a singleton or global variable without size limits or TTL.
- **Hypothesis 2: Unclosed File Descriptors, Network Sockets, or DB Connections**
  - *Evidence Needed:* `lsof -p <pid>` reveals thousands of leaked open file descriptors or socket buffers consuming kernel buffers and process memory.
- **Hypothesis 3: Large In-Memory File Buffering or Huge JSON Parsing**
  - *Evidence Needed:* Memory spike correlates precisely with batch report generation, PDF rendering, or unpaginated bulk database fetches.

## Contradictory Evidence & Alternative Explanations
- If memory usage is high but flushes immediately when traffic ceases or garbage collection runs, the application is not leaking memory; it is appropriately utilizing available memory buffers.
- If memory limit is set unrealistically low (e.g. 64MB for a multi-worker Python API), the issue is under-provisioning rather than a memory leak.

## Safe Mitigation & Rollback Guidance
- **Immediate Mitigation:** Perform a rolling restart of the service containers to reclaim leaked memory and stabilize production.
- **Temporarily Raise Limits:** Double container memory limits in `docker-compose.yml` or Kubernetes deployment manifests to extend uptime while diagnosing root cause.
- **Implement LRU/TTL Limits:** Replace raw Python dictionaries used for caching with `cachetools.TTLCache(maxsize=1000, ttl=300)`.
- **Stream Large Payloads:** Stream bulk file downloads or exports using chunks/generators rather than reading entire files into memory.

## Verification Steps & Escalation Criteria
- **Verification:** Post-restart memory stabilizes at a flat plateau under continuous synthetic load testing, with zero container OOM terminations over a 24-hour observation window.
- **Escalation Criteria:** If heap inspection identifies a leak inside a third-party C/Rust compiled dependency or driver, escalate to Senior Platform Architect (P2).
