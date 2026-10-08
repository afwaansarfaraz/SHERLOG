# Sherlog — Requirements

## 1. Project Goal

Sherlog is an AI-powered incident investigation and response platform.
It simulates a production SaaS environment, intentionally introduces known faults, detects incidents through observability systems, investigates them using an AI agent, identifies and verifies likely root causes, and proposes safe remediation.

The core loop is:
```
Fault → Detection → Investigation → Evidence → Root Cause → Remediation Proposal → Human Approval → Audit
```

The platform demonstrates production-oriented AI engineering rather than a generic RAG chatbot.

---

## 2. Functional Requirements

1. **Detection**: Detect simulated production incidents from monitoring/observability systems.
2. **Ingestion**: Receive incidents and alerts through FastAPI (with shared-secret webhook authentication for Alertmanager).
3. **Queueing**: Queue incidents through Redis Streams with consumer groups, retry mechanism, and dead-letter queue (DLQ).
4. **Asynchronous Processing**: Process queued incidents asynchronously using dedicated incident workers.
5. **AI Investigation**: Investigate incidents using an AI agent running a bounded, stateful execution loop.
6. **Telemetry Inspection**: Query metrics (Prometheus PromQL), logs (Loki), and traces (OpenTelemetry).
7. **Deployment & VCS Inspection**: Inspect recent deployments and Git diffs.
8. **Operational Knowledge**: Search runbooks, troubleshooting docs, and past incident history using RAG.
9. **Hypothesis Tracking**: Maintain multiple competing hypotheses throughout an investigation.
10. **Evidence-Based Scoring**: Score hypotheses using deterministic evidence counters, not self-reported LLM confidence.
11. **Verification**: Explicitly verify the leading root-cause hypothesis before concluding when possible.
12. **Root-Cause Ranking**: Produce a ranked list of identified root causes backed by concrete evidence.
13. **Remediation Proposal**: Propose remediations strictly restricted to an allowlisted set of safe actions. Propose-only in v1.
14. **Human Approval**: Require explicit human approval before any remediation can be executed.
15. **Audit Logging**: Persist an immutable audit trail for every investigation, proposal, and approval event.
16. **Crash Resumption**: Checkpoint agent state after every step in PostgreSQL to allow resumption after crashes or restarts.
17. **Budget Guards**: Enforce hard limits on maximum steps, token consumption, financial cost, and wall-clock execution time.
18. **Prompt Injection & Untrusted Data Defense**: Treat all tool outputs (logs, traces, diffs, runbooks) as untrusted; wrap and delimit outputs to prevent tool-call hijacking.
19. **Investigation Interface**: Provide a minimal investigation UI with real-time SSE updates.
20. **Benchmarking**: Evaluate performance systematically against a benchmark of 20 known fault scenarios across multiple runs.

---

## 3. Explicitly Deferred (Out of Scope for v1)

The following items are intentionally excluded from v1:
- Kubernetes (Docker Compose is used for v1)
- Kafka (Redis Streams is used for v1)
- Multi-agent architectures (single bounded state machine agent in v1)
- Autonomous remediation execution (propose-only; human-in-the-loop required)
- Complex frontend dashboards (minimal React + SSE timeline in v1)
- Multi-tenancy
- LangGraph (state machine is initially hand-rolled)
- LLM fine-tuning in the critical path (post-v1 exploration only)

---

## 4. Definition of Done (v1)

Sherlog v1 is complete when:
- The demo SaaS runs reliably.
- Faults can be injected via the fault injector.
- Monitoring detects injected faults and alerts reach FastAPI.
- Incidents enter Redis Streams and are processed by workers.
- The AI agent investigates incidents using typed read-only tools.
- RAG provides operational knowledge and runbooks.
- Hypotheses are tracked and scored deterministically with evidence.
- The agent verifies conclusions and checkpoints state after every step.
- Budgets prevent runaway step, token, cost, and time consumption.
- Remediation is strictly allowlisted, propose-only, and requires human approval.
- An audit log tracks all proposals and approvals.
- OAuth/OIDC protects the user-facing API.
- The benchmark runs 20 faults × 3 runs (minimum 60 total runs).
- A deterministic rule-based baseline is implemented and evaluated.
- Agent performance is measured against the baseline.
- CI detects regressions against benchmark thresholds.
- AI token usage, latency, and cost are observable.
- The project runs via Docker and has comprehensive documentation.
