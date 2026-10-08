# Sherlog — System Architecture

## 1. System Overview

Sherlog is an AI incident investigation and response platform designed around deterministic safety boundaries, rigorous observability, and human-in-the-loop remediation.

``` text
Fault Injector
      ↓
Demo SaaS
      ↓
Prometheus / Loki / OpenTelemetry
      ↓
Alertmanager
      ↓
FastAPI
  ├── Alertmanager → shared-secret authentication
  └── Dashboard/API → OAuth / OIDC
      ↓
Redis Streams
  ├── Consumer Groups
  ├── Retry
  └── Dead Letter Queue
      ↓
Incident Worker
      ↓
Cheap Router
(rules / cheap LLM)
      ↓
┌─────────────────────────────────────────────────────┐
│                   AGENT LOOP                        │
│                                                     │
│  1. Load / resume checkpoint from PostgreSQL        │
│  2. Budget guard                                    │
│  3. Strong LLM reasoning                            │
│  4. Select typed read-only tool                     │
│  5. Execute tool                                    │
│  6. Sanitize / delimit untrusted output             │
│  7. Process evidence                                │
│  8. Update deterministic hypothesis scores          │
│  9. Verify leading hypothesis                       │
│ 10. Checkpoint state to PostgreSQL                  │
│ 11. Trace tokens / latency / cost                   │
│ 12. Repeat or conclude                              │
└──────────────────────────┬──────────────────────────┘
                           ↓
                  Ranked Root Causes
                           ↓
              Allowlisted Remediation
                           ↓
                    Human Approval
                           ↓
                     Audit Log
                           ↓
                         SSE
                           ↓
                    Minimal UI
```

---

## 2. Technology Stack

- **Backend**: Python, FastAPI, Pydantic, Pydantic-Settings, SQLAlchemy, Redis, Psycopg
- **Persistence**: PostgreSQL (checkpointing, state, audit log) + pgvector (knowledge base embeddings)
- **Queueing**: Redis Streams (consumer groups, retry, dead-letter queue)
- **AI & Reasoning**:
  - Strong LLM for multi-step reasoning, hypothesis formulation, and verification
  - Cheap LLM / rules for triage and routing
  - Hand-rolled state machine (no external heavy graph framework in v1)
- **Observability**: Prometheus, Loki, OpenTelemetry, Alertmanager, Langfuse (LLM tracing)
- **Security**: OAuth 2.0 / OIDC, shared-secret webhook authentication, prompt injection defense, sandboxed tool boundaries
- **Frontend (Week 4)**: React, Server-Sent Events (SSE), minimal incident timeline
- **Infrastructure**: Docker, Docker Compose, GitHub Actions

---

## 3. Agent Execution Loop

The AI agent operates as a bounded state machine:

1. **Load Checkpoint**: Fetch or resume the active state checkpoint from PostgreSQL.
2. **Budget Guard**: Check step count, token consumption, cost limit, and wall-clock timeout. Terminate safely if budgets are exceeded.
3. **Reasoning & Planning**: Invoke strong LLM to analyze current evidence and formulate/update hypotheses.
4. **Tool Selection**: Select a typed, read-only investigation tool.
5. **Tool Execution**: Execute the tool with validated parameters.
6. **Untrusted Data Handling**: Sanitize and wrap tool outputs with security delimiters. Tool output is never granted tool-calling authority.
7. **Evidence Extraction**: Extract observations and relate them to active hypotheses.
8. **Deterministic Scoring**: Calculate hypothesis scores based on positive/negative evidence counts (LLM confidence statements are never treated as ground-truth scores).
9. **Verification**: When a leading hypothesis emerges with adequate evidence, execute verification checks.
10. **Checkpointing**: Persist complete state, hypotheses, evidence, and tool results to PostgreSQL.
11. **Telemetry & Tracing**: Record step latency, token count, and estimated cost to Langfuse/tracing store.
12. **Termination / Conclusion**: Conclude with ranked root causes and remediation proposal, or repeat until budget/convergence.

The agent never autonomously executes remediation.

---

## 4. Investigation Tools (Read-Only)

Investigation tools are strictly typed, bounded, and read-only:

- `query_metrics(promql: str, window: str) -> MetricResult`
- `search_logs(service: str, pattern: str, window: str) -> LogResult`
- `get_traces(service: str, window: str) -> TraceResult`
- `recent_deploys() -> DeployList`
- `git_diff(sha: str) -> DiffResult`
- `search_runbooks(query: str) -> RunbookResult`

Results are bounded to prevent context flooding and sanitized against prompt injections.

---

## 5. Hypothesis Tracking & Deterministic Ranking

The agent maintains multiple competing hypotheses (e.g., $H_1$: Database pool exhaustion, $H_2$: Slow query, $H_3$: Downstream dependency timeout).

Each hypothesis tracks:
- Supporting evidence items
- Contradicting evidence items
- Deterministic score (computed algorithmically from evidence count and reliability weights)
- Associated investigation tool outputs

---

## 6. Remediation & Safety Boundaries

- **Allowlisted Actions Only**: Remediation proposals must match strict pre-approved action definitions (e.g., scale replica count, restart service, adjust connection pool).
- **Propose-Only**: Remediations are output as proposals awaiting action.
- **Human Approval**: Remediations can only execute after explicit human authorization.
- **Audit Logging**: All proposals, review actions, and approvals are stored in an append-only audit table.

---

## 7. Storage & Queueing Architecture

- **PostgreSQL**: Stores incidents, agent state, step checkpoints, hypotheses, evidence, tool invocations, root causes, proposals, approvals, and audit records.
- **Redis Streams**: Handles incident ingestion queueing, worker consumer group distribution, retry scheduling, and DLQ dispatch.

---

## 8. Observability & AI Tracing

Every LLM inference and tool invocation records:
- Provider, model, and tool name
- Token counts (prompt, completion, total)
- Latency (ms)
- Financial cost calculation
- Step index and success/failure status
