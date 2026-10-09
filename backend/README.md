# Sherlog Backend — Phase 1: Incident Ingestion

This is the core FastAPI backend for **Sherlog**, an AI-powered incident investigation and response platform.

---

## Overview (Phase 1)

Phase 1 establishes the incident ingestion pipeline:
- **FastAPI application shell** with modular routers and CORS support.
- **Strongly-typed configuration** via environment variables (`Pydantic Settings`), preventing hardcoded secrets.
- **Health check endpoint**: `GET /health` and `GET /api/health`.
- **Validated incident ingestion endpoint**: `POST /api/incidents`.
- **Strict Pydantic payload validation**:
  - Enforces mandatory fields (`title`, `service`, `severity`, `summary`).
  - Restricts severity to allowed enums (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
  - Rejects blank/whitespace-only inputs and out-of-bound string lengths.
  - Automatically assigns unique sequential tracking IDs (`INC-00001`, `INC-00002`...).
- **Retrieval endpoints**:
  - `GET /api/incidents` (list all ingested incidents).
  - `GET /api/incidents/{incident_id}` (fetch specific incident by ID, with 404 handling).
- **Isolated repository pattern**: Uses an in-memory repository for Phase 1 without pretending PostgreSQL or Redis queueing are active before they are built.

---

## Project Structure

```text
backend/
├── app/
│   ├── __init__.py
│   ├── config.py              # Environment configuration via Pydantic Settings
│   ├── main.py                # FastAPI app initialization, middleware, routes
│   ├── api/
│   │   ├── __init__.py        # Router aggregation
│   │   ├── health.py          # GET /health
│   │   └── incidents.py       # POST /api/incidents, GET /api/incidents
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── incident.py        # Pydantic validation models (IncidentCreate, IncidentResponse)
│   └── storage/
│       ├── __init__.py
│       └── memory.py          # In-memory thread-safe incident repository
├── tests/
│   ├── conftest.py            # TestClient fixture and repo state reset
│   ├── test_health.py         # Automated tests for health endpoints
│   ├── test_incidents.py      # Automated tests for validation & ingestion
│   ├── test_fault_registry.py # Fault injector registry tests
│   └── test_services_contracts.py # Demo SaaS contract tests
└── README.md                  # This file
```

---

## How to Run the Backend

### 1. Requirements

Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

### 2. Start the Server

Run the server with Uvicorn:
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at:
- Base API: `http://localhost:8080`
- Interactive API Docs (Swagger): `http://localhost:8080/docs`
- Alternative Docs (ReDoc): `http://localhost:8080/redoc`

---

## How to Run the Automated Tests

Run the complete backend test suite using `pytest`:
```bash
pytest backend/tests -v
```

To run only the Phase 1 ingestion tests:
```bash
pytest backend/tests/test_incidents.py backend/tests/test_health.py -v
```

---

## Manual API Testing Guide

### 1. Health Check
```bash
curl -X GET http://localhost:8080/health
```
**Expected Response (`200 OK`):**
```json
{
  "status": "ok",
  "app": "Sherlog Incident Backend",
  "environment": "development"
}
```

### 2. Ingest Valid Incident
```bash
curl -X POST http://localhost:8080/api/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Database connection pool exhaustion",
    "service": "orders",
    "severity": "CRITICAL",
    "status": "OPEN",
    "summary": "Orders service connection pool saturated; checkout queries timing out after 2.0s.",
    "affected_endpoints": ["POST /orders/checkout"],
    "metadata": {
      "cluster": "prod-us-east-1",
      "pool_size": 5
    }
  }'
```
**Expected Response (`201 Created`):**
```json
{
  "id": "INC-00001",
  "title": "Database connection pool exhaustion",
  "service": "orders",
  "severity": "CRITICAL",
  "status": "OPEN",
  "summary": "Orders service connection pool saturated; checkout queries timing out after 2.0s.",
  "source": "alertmanager",
  "affected_endpoints": ["POST /orders/checkout"],
  "metadata": {
    "cluster": "prod-us-east-1",
    "pool_size": 5
  },
  "fingerprint": null,
  "created_at": "2026-10-09T09:24:37.196510Z"
}
```

### 3. Reject Invalid Incident (Invalid Severity)
```bash
curl -X POST http://localhost:8080/api/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Database connection pool exhaustion",
    "service": "orders",
    "severity": "UNKNOWN_SEVERITY",
    "summary": "Orders service connection pool saturated."
  }'
```
**Expected Response (`422 Unprocessable Entity`):**
```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["body", "severity"],
      "msg": "Input should be 'CRITICAL', 'HIGH', 'MEDIUM' or 'LOW'"
    }
  ]
}
```

### 4. Fetch Ingested Incident by ID
```bash
curl -X GET http://localhost:8080/api/incidents/INC-00001
```

### 5. List All Incidents
```bash
curl -X GET http://localhost:8080/api/incidents
```

---

## Phase Status Summary

- **Genuinely Working**:
  - FastAPI app startup, routing, CORS.
  - Health check endpoints (`/health`, `/api/health`).
  - Incident ingestion endpoint (`POST /api/incidents`) with HTTP 201 Created.
  - Strict Pydantic schema validation rejecting invalid payloads (missing fields, blank whitespace, invalid enums, length bounds).
  - Single incident retrieval (`GET /api/incidents/{id}`) with HTTP 404 for missing IDs.
  - Incident listing (`GET /api/incidents`).
  - Thread-safe repository storing records with sequential `INC-XXXXX` IDs and UTC timestamps.
  - Automated test suite (18/18 tests passing).
- **Deferred to Next Phases**:
  - PostgreSQL persistence (Phase 2).
  - Redis Streams queueing and dead-letter queue (Phase 2).
  - AI Investigation Agent loop and tool execution (Phase 3).
  - RAG operational runbook search (Phase 3).
