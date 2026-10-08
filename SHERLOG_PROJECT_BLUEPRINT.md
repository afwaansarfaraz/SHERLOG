# SHERLOG --- Project Blueprint

## AI Incident Investigation & Response Platform

This document is the master Day-0 specification for Sherlog.

Use it as the source of truth while setting up the repository. Keep it
practical. Do not over-polish the documentation before implementation
begins.

------------------------------------------------------------------------

# 1. Project Goal

Sherlog is an AI-powered incident investigation and response platform.

It simulates a production SaaS environment, intentionally introduces
known faults, detects incidents through observability systems,
investigates them using an AI agent, identifies and verifies likely root
causes, and proposes safe remediation.

The core loop is:

Fault → Detection → Investigation → Evidence → Root Cause → Remediation
Proposal → Human Approval → Audit

The project is designed to demonstrate production-oriented AI
engineering rather than a generic RAG chatbot.

------------------------------------------------------------------------

# 2. Final Architecture

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

------------------------------------------------------------------------

# 3. Agent Loop

The agent must operate as a controlled state machine.

1.  Load or resume the current checkpoint.
2.  Check step/token/cost/time budgets.
3.  Generate or update hypotheses.
4.  Select the next investigation tool.
5.  Execute the typed read-only tool.
6.  Treat the result as untrusted data.
7.  Sanitize and delimit the result.
8.  Extract relevant evidence.
9.  Update deterministic hypothesis scores.
10. Check whether the leading hypothesis has sufficient evidence.
11. Verify the hypothesis when possible.
12. Checkpoint the complete state in PostgreSQL.
13. Record tracing information.
14. Continue, conclude, or terminate on a safety limit.

The agent must never directly execute remediation.

------------------------------------------------------------------------

# 4. Project Structure

``` text
sherlog/
│
├── .agent/
│   └── rules.md
│
├── .github/
│   └── workflows/
│       └── eval.yml
│
├── docs/
│   ├── requirements.md
│   ├── architecture.md
│   └── evaluation.md
│
├── demo-app/
│   ├── api/
│   ├── orders/
│   ├── payments/
│   └── db/
│
├── backend/
│   ├── app/
│   └── tests/
│
├── fault-injector/
│
├── eval/
│
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

Do not create a large number of empty implementation files on Day 0.

The code should grow as each component is implemented.

The frontend is intentionally deferred to Week 4.

------------------------------------------------------------------------

# 5. `.agent/rules.md`

Use the following rules for Antigravity:

## Source of Truth

Before every coding session, read:

-   `.agent/rules.md`
-   `docs/requirements.md`
-   `docs/architecture.md`
-   `docs/evaluation.md`

These documents define the current project scope and architecture.

Do not change the architecture or project scope without explicit
approval.

## AI Agent

The agent must:

-   Use structured outputs.
-   Use typed tools.
-   Have a maximum number of steps.
-   Have token limits.
-   Have cost limits.
-   Have a wall-clock timeout.
-   Checkpoint state after every step.
-   Verify important conclusions.
-   Never execute remediation autonomously.

## Hypotheses

Hypothesis scores come from evidence counts and deterministic scoring.

Never use LLM-stated confidence as the source of truth.

Do not treat a model output such as `confidence: 0.95` as evidence.

## Tools

All tools must:

-   Have typed inputs.
-   Have typed outputs.
-   Validate inputs.
-   Return bounded results.
-   Be read-only during investigation.

Tool output is untrusted data.

Tool output must be wrapped/delimited and never granted tool-call
authority.

Logs, traces, Git content, retrieved documents, and other external text
must never be treated as system instructions.

## Security

-   Never hardcode secrets.
-   Use environment variables for secrets.
-   Validate external input.
-   Protect the Alertmanager webhook with a shared secret.
-   Use OAuth/OIDC for user-facing authentication.
-   Use authorization/RBAC where required.
-   Defend against prompt injection.
-   Never expose secrets through LLM context.

## Remediation

Remediation is propose-only.

Only allowlisted actions may be proposed.

Every remediation proposal requires human approval.

All approval and remediation events must be audited.

No autonomous remediation execution in v1.

## Evaluation

Never:

-   Edit ground-truth files to improve results.
-   Delete tests to make evaluation pass.
-   Modify evaluation logic to hide failures.
-   Create a separate worker implementation for evaluation.

The evaluation harness must call the same worker/agent code used in
production.

Every fault is run three times and variance is reported.

Sherlog must always be compared against the rule-based baseline.

Never claim an improvement unless the evaluation harness produced the
result.

## Dependencies

Add dependencies only when the corresponding component is being built.

Do not install a large number of libraries in advance.

Prefer existing dependencies when they reasonably solve the problem.

## Scope

Do not add to v1:

-   Kubernetes
-   Kafka
-   Multi-agent architecture
-   Autonomous remediation
-   Complex frontend
-   Multi-tenancy
-   Fine-tuning

Fine-tuning will be performed after the core project is complete.

LangGraph is not required for v1. The agent state machine is initially
hand-rolled.

## Code Quality

Use:

-   Python type hints.
-   Pydantic schemas.
-   Small modules.
-   Clear function names.
-   Explicit error handling.
-   Tests for important behavior.

Do not refactor unrelated code while implementing a feature.

Do not introduce unnecessary abstractions.

## Architecture Changes

If an implementation requires an architecture change:

1.  Stop.
2.  Explain why.
3.  Update `docs/architecture.md`.
4.  Get approval.
5.  Implement the approved change.

## AI Coding Agent

Do not generate the entire project blindly.

Implement one milestone at a time.

Before changing code:

1.  Read the relevant existing files.
2.  Understand the current implementation.
3.  Make the smallest required change.
4.  Run relevant tests.
5.  Report what changed.

Never silently replace working architecture with another approach.

------------------------------------------------------------------------

# 6. Functional Requirements

Sherlog must:

1.  Detect simulated production incidents.
2.  Receive incidents through FastAPI.
3.  Queue incidents through Redis Streams.
4.  Process incidents asynchronously.
5.  Investigate incidents using an AI agent.
6.  Query metrics, logs, and traces.
7.  Inspect recent deployments and Git diffs.
8.  Search operational knowledge using RAG.
9.  Track competing hypotheses.
10. Score hypotheses using evidence.
11. Verify the leading root cause.
12. Produce a ranked root-cause result.
13. Produce an allowlisted remediation proposal.
14. Require human approval.
15. Record an audit trail.
16. Resume interrupted investigations.
17. Enforce token, cost, step, and time budgets.
18. Defend against malicious tool output and prompt injection.
19. Provide a minimal incident investigation UI.
20. Evaluate itself against 20 known fault scenarios.

------------------------------------------------------------------------

# 7. Technology Stack

## Backend

-   Python
-   FastAPI
-   Pydantic
-   PostgreSQL
-   SQLAlchemy
-   Redis

## AI

-   Strong LLM for reasoning
-   Cheap LLM for summarization/routing where appropriate
-   Structured outputs
-   Tool calling
-   Embeddings
-   RAG
-   pgvector
-   Model routing
-   AI evaluation

## Agent

-   Hand-rolled state machine
-   Typed tools
-   Checkpointing
-   Budget guards
-   Verification
-   Evidence-based hypothesis ranking

## Observability

-   Prometheus
-   Loki
-   OpenTelemetry
-   Alertmanager
-   Langfuse or equivalent LLM tracing

## Security

-   OAuth 2.0 / OIDC
-   JWT where applicable
-   RBAC
-   Shared-secret webhook authentication
-   Environment-based secrets
-   Input validation
-   Prompt-injection defense
-   Tool permission boundaries
-   Allowlisted remediation
-   Human approval
-   Audit logging
-   Rate limiting where required

## Frontend

-   React
-   SSE
-   Minimal incident timeline

## Infrastructure

-   Docker
-   Docker Compose
-   GitHub Actions
-   Cloud deployment

Kubernetes is intentionally excluded from v1.

------------------------------------------------------------------------

# 8. Investigation Tools

The agent will eventually have typed read-only tools for:

``` text
query_metrics(promql, window)
search_logs(service, pattern, window)
get_traces(service, window)
recent_deploys()
git_diff(sha)
search_runbooks(query)
```

Tool results must be:

-   Bounded.
-   Structured.
-   Sanitized.
-   Treated as untrusted data.

Raw log dumps should not be inserted blindly into the model context.

------------------------------------------------------------------------

# 9. RAG

RAG is a supporting capability, not the purpose of Sherlog.

The knowledge base can contain:

-   Runbooks.
-   Troubleshooting guides.
-   Service documentation.
-   Past incidents.
-   Architecture notes.

Flow:

``` text
Incident
   ↓
Agent query
   ↓
Embedding
   ↓
pgvector
   ↓
Relevant operational knowledge
   ↓
Agent evidence
```

------------------------------------------------------------------------

# 10. Hypothesis Ranking

Sherlog should maintain multiple hypotheses.

Example:

``` text
H1: Database pool exhaustion
H2: Slow database query
H3: Payment dependency timeout
```

Each hypothesis tracks:

-   Supporting evidence.
-   Contradicting evidence.
-   Evidence score.
-   Relevant tools/evidence.

The score is deterministic.

The LLM can propose hypotheses, but it cannot simply declare its own
confidence as the ranking mechanism.

------------------------------------------------------------------------

# 11. Remediation

The system is propose-only in v1.

Example:

``` text
Root Cause:
Database connection pool exhaustion

Proposal:
Increase orders-service DB pool from 20 to 40

Status:
Awaiting approval
```

Only predefined/allowlisted actions can be proposed.

The user must approve before any remediation action is executed.

Every proposal and approval must be recorded in the audit log.

------------------------------------------------------------------------

# 12. Persistence

PostgreSQL stores at minimum:

-   Incidents.
-   Agent state.
-   Agent checkpoints.
-   Hypotheses.
-   Evidence.
-   Tool calls.
-   Root-cause results.
-   Remediation proposals.
-   Approval events.
-   Audit events.

Checkpoint state after every agent step.

This allows a worker to resume after a crash.

------------------------------------------------------------------------

# 13. Redis

Redis Streams are used for:

-   Incident queueing.
-   Consumer groups.
-   Retry.
-   Dead-letter queue.

Redis may later also support:

-   Rate limiting.
-   Caching.
-   Temporary state.

Do not add these features until they are needed.

------------------------------------------------------------------------

# 14. Observability and AI Tracing

Every LLM and tool call should record:

-   Model/tool name.
-   Tokens.
-   Latency.
-   Cost.
-   Success/failure.
-   Agent step.

The goal is to answer:

> How much did this investigation cost, how long did it take, and what
> did the agent do?

------------------------------------------------------------------------

# 15. Evaluation

## Benchmark

20 fault scenarios.

Each fault runs 3 times.

Minimum total runs: 60.

Faults should have variations so the system cannot simply memorize one
exact pattern.

## Ground Truth

Example:

``` yaml
fault_id: DB_POOL_EXHAUSTION_01
service: orders
root_cause: database_connection_pool_exhaustion

valid_remediations:
  - increase_pool_size
  - restart_service
```

Ground truth must never be modified to improve results.

## Baseline

Build a deterministic rule-based baseline before evaluating the AI
agent.

The baseline may use:

-   Metric thresholds.
-   Known log patterns.
-   Keyword matching.
-   Deterministic service rules.

Report the baseline next to the agent.

## Metrics

Root-cause:

-   Top-1 accuracy.
-   Top-3 accuracy.

Detection:

-   Detection rate.
-   False-positive rate.

Efficiency:

-   Steps per incident.
-   Tokens per incident.
-   Cost per incident.

Performance:

-   Time-to-diagnosis p50.
-   Time-to-diagnosis p95.

Security:

-   Injection-block rate.

Reliability:

-   Resume success.

Statistics:

-   Mean.
-   Variance across the 3 runs.

## Calibration

Where probability/confidence estimates are exposed, evaluate calibration
separately.

Do not use LLM self-reported confidence as the evidence-ranking
mechanism.

## Ablation

Measure:

1.  Rule-based baseline.
2.  Agent.
3.  Agent + log summarization.
4.  Agent + verification.
5.  Agent + routing.

------------------------------------------------------------------------

# 16. CI Evaluation

GitHub Actions will eventually run:

-   Tests.
-   A representative subset of the evaluation benchmark.
-   Regression checks.

The CI evaluation must use the same production worker/agent code.

The pipeline should fail when performance falls beyond the configured
regression threshold.

LLM calls should be cached/mocked where appropriate for deterministic CI
behavior.

------------------------------------------------------------------------

# 17. Environment Variables

Initial `.env.example`:

``` env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/sherlog
REDIS_URL=redis://redis:6379/0

LLM_API_KEY=

WEBHOOK_SECRET=
API_KEY=

MAX_STEPS=8
MAX_TOKENS=12000
MAX_SECONDS=120

LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=
```

Do not commit `.env`.

OAuth credentials are added when the OAuth/OIDC layer is implemented.

------------------------------------------------------------------------

# 18. Initial Python Dependencies

Start small.

``` text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
sqlalchemy
psycopg[binary]
redis
httpx
prometheus-client
opentelemetry-api
opentelemetry-sdk
```

Add other dependencies only when their corresponding component is built.

------------------------------------------------------------------------

# 19. Docker

Initial Docker Compose should begin with the infrastructure needed
immediately:

-   PostgreSQL
-   Redis

Gradually add:

-   Demo services.
-   Prometheus.
-   Loki.
-   Alertmanager.
-   Backend.
-   Worker.
-   Other required services.

Do not build the entire Docker environment before the corresponding
application components exist.

------------------------------------------------------------------------

# 20. Build Plan

## Phase 0 --- Foundation

Target: 2--3 hours.

Create:

-   Repository.
-   Folder structure.
-   `.agent/rules.md`.
-   `docs/requirements.md`.
-   `docs/architecture.md`.
-   `docs/evaluation.md`.
-   `requirements.txt`.
-   `.env.example`.
-   `.gitignore`.
-   `README.md`.
-   `docker-compose.yml`.
-   `.github/workflows/eval.yml`.

Then commit.

Suggested commit:

``` text
chore: initialize Sherlog architecture
```

Do not polish the documentation.

------------------------------------------------------------------------

# Week 1 --- Environment + Evaluation + Baseline

Goal:

> Build a system to break and a measuring stick before adding AI.

### Step 1

Build the Demo SaaS:

-   API service.
-   Orders service.
-   Payments service.
-   Database.

### Step 2

Build the fault injector.

Target:

20 known fault scenarios.

Examples:

-   Bad deployment.
-   Database connection pool exhaustion.
-   Memory leak.
-   Slow query.
-   Database lock.
-   Traffic spike.
-   Dependency timeout.
-   Configuration error.

Use variants so exact pattern memorization is difficult.

### Step 3

Add:

-   Prometheus.
-   Loki.
-   OpenTelemetry.
-   Alertmanager.

### Step 4

Build:

Alertmanager → FastAPI webhook.

Protect it with a shared secret.

### Step 5

Build the deterministic rule-based baseline.

### Step 6

Build the evaluation harness.

Run:

20 faults × 3 runs.

At the end of Week 1, you should have measurable baseline results.

No AI agent yet.

------------------------------------------------------------------------

# Week 2 --- AI Investigation

Goal:

> Build an agent that can beat the baseline.

### Build

-   Redis Streams.
-   Incident worker.
-   Cheap router.
-   Strong LLM agent.
-   Typed investigation tools.
-   Log summarization.
-   RAG.
-   pgvector.
-   Hypothesis tracking.
-   Verification.

Agent loop:

``` text
Observe
→ Hypothesize
→ Select Tool
→ Collect Evidence
→ Update Hypotheses
→ Verify
→ Conclude
```

Limit the agent to a fixed maximum number of steps.

Measure:

-   Root-cause accuracy.
-   Tool-selection accuracy.
-   Steps.
-   Tokens.
-   Cost.
-   Latency.

------------------------------------------------------------------------

# Week 3 --- Hardening

Goal:

> Make Sherlog safe, resumable, bounded, and production-oriented.

Build:

-   PostgreSQL checkpointing.
-   Budget guard.
-   Prompt-injection defense.
-   Untrusted-output sanitizer.
-   Evidence-based hypothesis scoring.
-   Verification.
-   Retry handling.
-   Dead-letter queue.
-   Worker crash recovery.
-   Remediation allowlist.
-   Human approval.
-   Audit logs.
-   OAuth/OIDC.
-   RBAC.
-   Rate limiting where needed.

Test:

-   Malicious log injection.
-   Worker crash during investigation.
-   Repeated tool calls.
-   Budget exhaustion.
-   Invalid input.
-   Unauthorized approval attempts.

------------------------------------------------------------------------

# Week 4 --- Observability + UI + CI + Deployment

Goal:

> Turn Sherlog into a demonstrable portfolio project.

Build:

-   Langfuse/AI tracing.
-   Minimal React UI.
-   SSE incident timeline.
-   Hypothesis/evidence display.
-   Remediation approval button.
-   Postmortem generator.
-   GitHub Actions evaluation gate.
-   Docker deployment.
-   Cloud deployment.
-   README.
-   Architecture diagram.
-   Benchmark report.
-   Failure analysis.
-   Demo video.

------------------------------------------------------------------------

# 21. Fine-Tuning --- After v1

Do not block Sherlog v1 on fine-tuning.

After the complete project works:

``` text
Rules Router
     VS
Cheap LLM Router
     VS
Fine-Tuned Router
```

The fine-tuned model can classify:

-   Incident type.
-   Priority.
-   Initial investigation category.
-   Initial tool/path recommendation.

Measure:

-   Accuracy.
-   Latency.
-   Cost.
-   Routing quality.

Fine-tuning is an experiment after the core system, not a dependency of
the core architecture.

------------------------------------------------------------------------

# 22. Explicitly Deferred

Do not add these to v1:

-   Kubernetes.
-   Kafka.
-   Multi-agent systems.
-   Autonomous remediation.
-   Multi-tenancy.
-   Complex frontend.
-   Fine-tuning in the critical path.
-   LangGraph in the initial implementation.

These can be learned separately or considered after the core system is
complete.

------------------------------------------------------------------------

# 23. Development Rule

AI coding agents can drift.

At the beginning of every session, instruct the coding agent to re-read:

``` text
.agent/rules.md
docs/requirements.md
docs/architecture.md
docs/evaluation.md
```

Treat these files as the source of truth.

Implement Sherlog incrementally.

Do not ask the coding agent to build the entire project in one prompt.

Build one milestone, test it, understand it, commit it, then continue.

------------------------------------------------------------------------

# 24. Definition of Done

Sherlog v1 is complete when:

-   The demo SaaS runs.
-   Faults can be injected.
-   Monitoring detects them.
-   Alerts reach FastAPI.
-   Incidents enter Redis Streams.
-   Workers process incidents.
-   The AI agent investigates using typed tools.
-   RAG provides operational knowledge.
-   Hypotheses are evidence-ranked.
-   The agent verifies conclusions.
-   State checkpoints allow recovery.
-   Budgets prevent runaway execution.
-   Tool output is treated as untrusted.
-   Remediation is allowlisted and propose-only.
-   Human approval is required.
-   Actions are audited.
-   OAuth/OIDC protects the user-facing API.
-   The system has a minimal UI.
-   The benchmark runs 20 faults × 3 runs.
-   A rule-based baseline exists.
-   Agent performance is measured against the baseline.
-   CI detects evaluation regressions.
-   AI tokens, latency, and cost are observable.
-   The project is deployed.
-   The README explains architecture, evaluation, results, and
    limitations.

------------------------------------------------------------------------

# 25. Core Principle

Do not optimize for the number of technologies used.

Optimize for:

``` text
Real Problem
     ↓
Correct Architecture
     ↓
Measurable AI
     ↓
Safety
     ↓
Evaluation
     ↓
Production Engineering
```

Every technology in Sherlog must have a reason to exist.
