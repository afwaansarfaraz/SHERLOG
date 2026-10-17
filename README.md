# Sherlog 🔍

> **AI Incident Investigation & Response Platform**

Sherlog is an AI-powered incident investigation and response platform. It simulates a production SaaS environment, intentionally introduces known faults, detects incidents through observability systems, investigates them using an AI agent, identifies and verifies likely root causes, and proposes safe, human-reviewed remediation.

```text
Fault → Detection → Investigation → Evidence → Root Cause → Remediation Proposal → Human Approval → Audit
```

---

## 🏗️ Architecture

```text
Fault Injector
      ↓
Demo SaaS (API, Orders, Payments, DB)
      ↓
Prometheus / Loki / OpenTelemetry
      ↓
Alertmanager
      ↓
FastAPI (shared secret authentication)
      ↓
Redis Streams (Consumer groups, retry, DLQ)
      ↓
Incident Worker
      ↓
Cheap Router (rules / cheap LLM)
      ↓
Agent Loop (State machine + typed read-only tools + PostgreSQL checkpointing + budget guard)
      ↓
Ranked Root Causes & Allowlisted Remediation Proposal
      ↓
Human Approval → Audit Log → SSE → Minimal Investigation UI
```

---

## 📁 Repository Structure

```text
sherlog/
├── .agent/
│   └── rules.md              # AI agent rules & design constraints
├── .github/
│   └── workflows/
│       └── eval.yml          # CI evaluation and test workflow
├── docs/
│   ├── requirements.md       # Functional & system requirements
│   ├── architecture.md       # Detailed technical architecture
│   └── evaluation.md         # Benchmark, metrics & baseline specifications
├── demo-app/                 # Demo microservices (API, Orders, Payments, DB)
│   ├── api/
│   ├── orders/
│   ├── payments/
│   └── db/
├── backend/                  # FastAPI ingestion, incident worker, agent engine
│   ├── app/
│   └── tests/
├── fault-injector/           # 20 fault injection scenarios
├── eval/                     # Evaluation benchmark harness & baseline
├── docker-compose.yml        # Day-0 infrastructure (PostgreSQL & Redis)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore
├── SHERLOG_PROJECT_BLUEPRINT.md # Master project blueprint
└── README.md
```

---

## 🚀 Getting Started (Day 0)

### 1. Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### 2. Configure Environment

Copy the example environment configuration:

```bash
cp .env.example .env
```

### 3. Start Core Infrastructure

Day 0 starts with the foundational persistence and message broker infrastructure (PostgreSQL and Redis):

```bash
docker compose up -d
```

Verify services:
```bash
docker compose ps
```

### 4. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run Database Migrations

Apply Alembic migrations to initialize all tables (including investigations, knowledge base chunks, and audit logs):

```bash
alembic upgrade head
```

### 6. Start the Sherlog Platform Backend

The Sherlog AI investigation platform backend runs on port `8080`:

```bash
# Windows PowerShell
.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 --reload

# Linux/macOS
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 --reload
```

> **Note:** Port `8080` is the Sherlog Platform API. Port `8000` is reserved for the Demo SaaS API gateway (`sherlog-api`).

### 7. Start the Frontend Workspace

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open your browser at `http://localhost:5173`.

---

## 🧭 Project Roadmap

- **Phase 0 (Day 0)**: Foundation & Day-0 repository setup *(Current)*
- **Week 1**: Demo SaaS environment, fault injector (20 faults), Prometheus/Loki observability, Alertmanager webhook, and deterministic rule-based baseline.
- **Week 2**: AI investigation agent (typed tools, PostgreSQL checkpointing, hypothesis tracking, RAG with pgvector).
- **Week 3**: Hardening, budget guards, prompt-injection defense, remediation allowlisting, human-in-the-loop approvals, and audit logging.
- **Week 4**: Langfuse observability, minimal React UI with SSE, evaluation benchmark reporting, CI regression gate, and deployment.

---

## 📜 Development Guidelines

Before each coding session, refer to the source-of-truth documents:
- [`.agent/rules.md`](.agent/rules.md)
- [`docs/requirements.md`](docs/requirements.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/evaluation.md`](docs/evaluation.md)
