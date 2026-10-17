import type {
  IncidentInvestigationData,
  InvestigationStep,
  Hypothesis,
  EvidenceItem,
  InvestigationLogEntry,
  TraceSpan,
  RemediationProposal,
} from "../types"

export const mockInvestigationSteps: InvestigationStep[] = [
  {
    id: "step-1",
    title: "Alert received",
    timestamp: "19:42:03",
    status: "completed",
    details: "High latency alert triggered by Alertmanager (HTTP p95 > 1.0s on orders service).",
    toolName: "webhook_ingest",
  },
  {
    id: "step-2",
    title: "Analyzing metrics",
    timestamp: "19:42:04",
    status: "completed",
    details: "Querying PromQL metrics for response latency and active DB connections.",
    toolName: "query_metrics",
  },
  {
    id: "step-3",
    title: "Searching logs",
    timestamp: "19:42:05",
    status: "completed",
    details:
      "Filtered Loki logs for service='orders' and pattern='timeout|pool|error'. Found 12 matching events.",
    toolName: "search_logs",
  },
  {
    id: "step-4",
    title: "Checking deployments",
    timestamp: "19:42:07",
    status: "completed",
    details:
      "Queried deployment log. No recent code rollout in the last 2 hours. Config unchanged.",
    toolName: "check_deployments",
  },
  {
    id: "step-5",
    title: "Verifying hypothesis",
    timestamp: "19:42:08",
    status: "completed",
    details:
      "Trace waterfall verification confirmed 90% of total span latency occurs in db.pool.acquire.",
    toolName: "get_traces",
  },
  {
    id: "step-6",
    title: "Generating conclusion",
    timestamp: "19:42:09",
    status: "completed",
    details:
      "Root cause validated with deterministic evidence score of 82%. Proposing safe pool resize.",
    toolName: "propose_remediation",
  },
]

export const mockHypotheses: Hypothesis[] = [
  {
    id: "h1",
    rank: 1,
    title: "Database connection pool exhaustion",
    description: "High connection utilization and increased DB latency causing request queuing.",
    score: 82,
    likelihood: "LIKELY",
    supportingEvidenceCount: 4,
    contradictingEvidenceCount: 0,
    verified: true,
    verificationReason:
      "Confirmed: 20/20 database pool connections occupied. p95 pool acquire latency 1,120ms.",
  },
  {
    id: "h2",
    rank: 2,
    title: "Traffic spike",
    description: "Sudden increase in incoming HTTP requests exceeding cluster ingress bandwidth.",
    score: 41,
    likelihood: "POSSIBLE",
    supportingEvidenceCount: 1,
    contradictingEvidenceCount: 2,
    verified: false,
    verificationReason: "Request rate elevated by only 8% (within normal standard deviation).",
  },
  {
    id: "h3",
    rank: 3,
    title: "Payment service dependency",
    description: "Increased response latency from downstream payment authorization gateway.",
    score: 18,
    likelihood: "LESS_LIKELY",
    supportingEvidenceCount: 0,
    contradictingEvidenceCount: 3,
    verified: false,
    verificationReason: "Payment service latency p95 is healthy at 88ms (well within 200ms SLA).",
  },
]

export const mockEvidenceItems: EvidenceItem[] = [
  {
    id: "ev-1",
    hypothesisId: "h1",
    type: "metric",
    title: "DB Connections at 100% saturation",
    polarity: "supporting",
    delta: "+340% vs normal",
    source: "Prometheus (orders_db_pool_active)",
    timestamp: "19:42:04",
    summary:
      "Active connections reached 20/20 max configured limit. Zero idle connections available in pool.",
    rawSnippet:
      "orders_db_pool_active{service='orders'} = 20\norders_db_pool_max{service='orders'} = 20\nutilization = 1.0 (100%)",
    weight: 35,
  },
  {
    id: "ev-2",
    hypothesisId: "h1",
    type: "metric",
    title: "Orders API p95 response time spike",
    polarity: "supporting",
    delta: "+820% vs normal",
    source: "Prometheus (http_request_duration_seconds)",
    timestamp: "19:42:04",
    summary: "HTTP p95 response latency escalated from 145ms baseline to 1,240ms.",
    rawSnippet:
      "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service='orders'}[5m])) by (le)) = 1.24s",
    weight: 30,
  },
  {
    id: "ev-3",
    hypothesisId: "h1",
    type: "log",
    title: "Connection pool timeout errors",
    polarity: "supporting",
    delta: "12 occurrences / min",
    source: "Loki (orders-service-logs)",
    timestamp: "19:42:05",
    summary:
      "Multiple error logs showing 'ConnectionPoolTimeoutException: Timed out waiting for connection from pool'.",
    rawSnippet:
      "[ERROR] 19:42:01.304 [pool-worker-4] DatabaseConnectionPool: Acquisition timeout after 30000ms. Active: 20, Idle: 0, Pending: 44",
    weight: 25,
  },
  {
    id: "ev-4",
    hypothesisId: "h1",
    type: "trace",
    title: "Trace waterfall bottle-neck in pool.acquire",
    polarity: "supporting",
    delta: "90.3% of span time",
    source: "OpenTelemetry (trace_id: 8f4a210bc931e4)",
    timestamp: "19:42:08",
    summary:
      "Span analysis demonstrates 1,120ms of the total 1,240ms duration spent in 'db.pool.acquire' state.",
    rawSnippet:
      "Span: db.pool.acquire\nDuration: 1120ms\nStatus: Error\nEvent: pool_exhaustion_wait",
    weight: 20,
  },
  {
    id: "ev-5",
    hypothesisId: "h2",
    type: "metric",
    title: "HTTP ingress request throughput",
    polarity: "contradicting",
    delta: "+8% (normal variance)",
    source: "Prometheus (http_requests_total)",
    timestamp: "19:42:04",
    summary:
      "Total request rate was 590 req/s, which is well below the 1,200 req/s surge threshold.",
    rawSnippet:
      "sum(rate(http_requests_total{service='orders'}[5m])) = 590 req/s\nBaseline: 545 req/s (±12%)",
    weight: -20,
  },
  {
    id: "ev-6",
    hypothesisId: "h3",
    type: "trace",
    title: "Downstream payment latency check",
    polarity: "contradicting",
    delta: "88ms (healthy)",
    source: "OpenTelemetry (span: payment.authorize)",
    timestamp: "19:42:08",
    summary:
      "Downstream payment gateway responded in 88ms, disproving downstream bottleneck hypothesis.",
    rawSnippet:
      "Span: payment.authorize\nTarget: payments-service\nDuration: 88ms\nHTTP Status: 200 OK",
    weight: -25,
  },
  {
    id: "ev-7",
    hypothesisId: "h1",
    type: "deploy",
    title: "Recent deploy inspection",
    polarity: "neutral",
    delta: "Last deployed 2h ago",
    source: "Git / CI Deploy Log",
    timestamp: "19:42:07",
    summary: "No recent deployments or configuration changes coincided with the incident onset.",
    rawSnippet:
      "Last Commit: 3b194ca 'refactor(orders): streamline line items'\nDeployed: 17:40:12 UTC (2 hours prior)",
    weight: 0,
  },
]

export const mockInvestigationLogs: InvestigationLogEntry[] = [
  {
    id: "log-1",
    timestamp: "19:42:01.304",
    level: "ERROR",
    service: "orders",
    message:
      "ConnectionPoolTimeoutException: Timed out waiting for connection from pool after 30000ms. Active: 20, Max: 20, Pending: 44",
    traceId: "8f4a210bc931e4",
  },
  {
    id: "log-2",
    timestamp: "19:42:01.892",
    level: "ERROR",
    service: "orders",
    message:
      "Failed to persist order ORD-99381. Transaction rollback due to DB connection timeout.",
    traceId: "8f4a210bc931e4",
  },
  {
    id: "log-3",
    timestamp: "19:42:02.115",
    level: "WARN",
    service: "orders",
    message:
      "CircuitBreaker [OrdersDatabase] state changed to HALF-OPEN due to repeated connection failures.",
  },
  {
    id: "log-4",
    timestamp: "19:42:02.441",
    level: "ERROR",
    service: "orders",
    message:
      "HTTP 500 InternalServerError returned for POST /orders/checkout [caller: api-gateway].",
    traceId: "8f4a210bc931e5",
  },
  {
    id: "log-5",
    timestamp: "19:42:03.010",
    level: "WARN",
    service: "orders",
    message: "Queue buffer threshold exceeded: 52 requests awaiting database worker threads.",
  },
  {
    id: "log-6",
    timestamp: "19:42:03.550",
    level: "INFO",
    service: "orders",
    message: "Health check probe /healthz returned 200 OK (process alive, memory 64% used).",
  },
  {
    id: "log-7",
    timestamp: "19:42:04.120",
    level: "ERROR",
    service: "orders",
    message:
      "ConnectionPoolTimeoutException: Database query worker pool starved of connection tokens.",
    traceId: "8f4a210bc931e6",
  },
]

export const mockTraceSpans: TraceSpan[] = [
  {
    id: "span-1",
    name: "POST /orders/checkout",
    service: "orders-service",
    durationMs: 1240,
    startOffsetMs: 0,
    statusCode: "ERROR",
    attributes: {
      "http.method": "POST",
      "http.status_code": 500,
      "http.route": "/orders/checkout",
      "user.id": "usr-8819",
    },
  },
  {
    id: "span-2",
    name: "db.pool.acquire",
    service: "orders-service",
    durationMs: 1120,
    startOffsetMs: 15,
    statusCode: "ERROR",
    attributes: {
      "pool.name": "orders-primary-pool",
      "pool.active": 20,
      "pool.max": 20,
      "error.type": "ConnectionPoolTimeout",
    },
  },
  {
    id: "span-3",
    name: "payment.authorize",
    service: "payments-service",
    durationMs: 88,
    startOffsetMs: 1140,
    statusCode: "OK",
    attributes: {
      "payment.provider": "stripe",
      "http.status_code": 200,
    },
  },
  {
    id: "span-4",
    name: "cache.get(orders:inventory)",
    service: "orders-service",
    durationMs: 12,
    startOffsetMs: 2,
    statusCode: "OK",
    attributes: {
      "cache.hit": "true",
    },
  },
]

export const mockRemediationProposal: RemediationProposal = {
  id: "rem-00241",
  incidentId: "INC-00241",
  rootCauseTitle: "Database connection pool exhaustion",
  rootCauseDescription:
    "The orders service is experiencing severe latency and request timeouts due to connection pool exhaustion. All 20 pool connections are locked or active, causing incoming orders to queue and exceed the 30s timeout.",
  actionTitle: "Increase database connection pool size",
  actionDescription:
    "Increase the connection pool from 20 to 40 connections and adjust acquisition timeout to 15s.",
  targetService: "orders",
  allowlistedAction: "increase_pool_size",
  configDiff: `--- a/services/orders/config.yaml
+++ b/services/orders/config.yaml
@@ -17,5 +17,5 @@
 database:
   host: db-primary.internal
   port: 5432
   pool:
-    max_connections: 20
-    timeout_ms: 30000
+    max_connections: 40
+    timeout_ms: 15000`,
  status: "AWAITING_APPROVAL",
}

export const mockRetrievedSources = [
  {
    doc_id: "upload:9f058f10ea53",
    chunk_id: "d782975a-6ae0-4fe9-9ef5-84c623b4346b",
    title: "Sherlog Demo Database Pool Exhaustion Runbook - Purpose & Triage",
    source: "runbooks/database_pool_exhaustion.md",
    service: "orders",
    excerpt: "## Triage & Investigation Steps\n1. Check active database connection pool gauge in Prometheus: `pg_stat_activity` vs configured pool limit.\n2. When connections reach 100% capacity, incoming queries queue and throw acquire timeouts (HTTP 500 / 504 on /orders/checkout).\n3. Remediate by increasing pool maximum connections or terminating idle sessions.",
    similarity_score: 0.81,
    rank: 1,
    included_in_context: true,
    why_relevant: "Matched orders service connection pool exhaustion symptoms, directly detailing connection saturation behavior and sizing remediation.",
  },
  {
    doc_id: "runbook:historical_incidents",
    chunk_id: "f3277a4c-f8bf-4864-a1dd-a938689b1bbe",
    title: "Historical Postmortem - INC-2026-001: Connection Pool Starvation",
    source: "postmortems/INC-2026-001.md",
    service: "orders",
    excerpt: "## Resolution & Action Items\nDuring flash sale traffic, 20 pool connections proved insufficient. The permanent fix scaled the pool to 40 connections with acquisition timeout reduced to 15s.",
    similarity_score: 0.79,
    rank: 2,
    included_in_context: true,
    why_relevant: "Identifies identical past incident on orders service where pool capacity caused severe checkout latency.",
  },
  {
    doc_id: "runbook:slow_query_tuning",
    chunk_id: "c84112e4-99b2-4d91-88d4-5399712a1f81",
    title: "Runbook: Slow Database Query Optimization",
    source: "runbooks/slow_queries.md",
    service: "orders",
    excerpt: "Index fragmentation or missing composite indices can cause long query duration. Check pg_stat_statements for top queries by total execution time.",
    similarity_score: 0.62,
    rank: 3,
    included_in_context: false,
    why_relevant: "Retrieved as secondary candidate regarding database latency, but deprioritized as evidence points to connection starvation rather than single slow queries.",
  },
]

export const mockInvestigationDataINC00241: IncidentInvestigationData = {
  incidentId: "INC-00241",
  title: "API latency spike",
  service: "Orders service",
  status: "INVESTIGATING",
  openedAt: "5 min ago",
  summary:
    "High API latency and increased response times on orders service. p95 response time degraded to 1.2s.",
  steps: mockInvestigationSteps,
  hypotheses: mockHypotheses,
  evidence: mockEvidenceItems,
  logs: mockInvestigationLogs,
  traces: mockTraceSpans,
  remediation: mockRemediationProposal,
  retrievedSources: mockRetrievedSources,
  retrievalStatus: "SUCCESS",
}
