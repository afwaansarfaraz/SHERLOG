# Runbook: Insufficient Telemetry and Inconclusive Incidents
- **Runbook ID:** RB-014
- **Category:** Insufficient telemetry and inconclusive incidents
- **Version:** 1.0.0
- **Applicable Services:** All applications, OpenTelemetry Collector, Prometheus, Loki, Jaeger
- **Keywords:** telemetry gap, missing traces, blind spot, uninstrumented, inconclusive incident, otel collector dropped, sampling rate

## Symptoms
- Incident triggered by user complaint or synthetic blackbox alert, but Sherlog AI investigation reports "Inconclusive: Insufficient Evidence".
- Jaeger traces are missing root spans, missing database child spans, or showing broken trace propagation context (missing `traceparent` headers).
- Prometheus metrics show flat lines or gaps (`NaN`) during critical failure windows.
- Loki log volume drops to zero for an active service, or logs lack correlation IDs (`trace_id`, `span_id`, `service_name`).

## Required Observability Signals
- **Metrics:** `otelcol_receiver_accepted_spans`, `otelcol_exporter_sent_spans`, `otelcol_exporter_enqueue_failed_spans`, `prometheus_target_scrape_pool_targets`
- **Logs:** Loki query `{service="otel-collector"} |= "dropped"` or `{service=~".*"} |= "traceparent"`
- **Traces:** Health check spans present, but critical business transaction pathways show zero recorded traces.

## Diagnostic Steps
1. Verify the telemetry collection pipeline health:
   ```bash
   curl -s http://localhost:8888/metrics | grep otelcol_receiver_accepted_spans
   curl -s http://localhost:9090/api/v1/targets | grep DOWN
   ```
2. Check OpenTelemetry Collector exporter queue and drop counters to see if telemetry was dropped due to backpressure:
   `otelcol_exporter_enqueue_failed_spans > 0`
3. Inspect trace sampling configuration (e.g. `OTEL_TRACES_SAMPLER=parentbased_traceidratio` set to 0.01 instead of 1.0 in testing).
4. Verify HTTP client and server middleware instrumentation: check if W3C TraceContext propagation headers (`traceparent`, `tracestate`) are being stripped by reverse proxies or missing in outgoing client calls.

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: OpenTelemetry Collector Queue Overflow or Collector Crash**
  - *Evidence Needed:* Collector logs contain `Exporting failed: queue is full` or container restarted during traffic burst.
- **Hypothesis 2: Aggressive Head-Based Sampling Dropping Rare Error Traces**
  - *Evidence Needed:* Sampling rate is set to < 5%, causing 95% of slow or failed traces to be discarded before reaching Jaeger.
- **Hypothesis 3: Missing Context Propagation Across Thread Boundaries or Async Tasks**
  - *Evidence Needed:* Logs and spans have empty or disconnected `trace_id`, creating orphaned spans that cannot be correlated to the root incident.

## Contradictory Evidence & Alternative Explanations
- If Prometheus and Loki show full telemetry with error logs and metric spikes, telemetry is NOT insufficient; the incident investigation prompt or similarity threshold may need tuning.
- If an application is brand new and has not yet completed OTel SDK registration, it is in UNCONFIGURED state rather than pipeline failure.

## Safe Mitigation & Rollback Guidance
- **Enable Tail-Based Sampling:** Configure OTel collector to retain 100% of traces containing `http.status_code >= 500` or duration > 1000ms.
- **Increase Collector Buffer Sizes:** Raise `sending_queue.queue_size` under exporter configuration in `otel-collector-config.yaml` to prevent dropping spans under burst load:
  ```yaml
  exporters:
    otlp:
      endpoint: "jaeger:4317"
      sending_queue:
        enabled: true
        queue_size: 5000
  processors:
    batch:
      send_batch_size: 1024
      timeout: 1s
  ```
- **Inject Correlation Middleware:** Add OpenTelemetry automatic ASGI/WSGI middleware to propagate `trace_id` into all structured log formatters.
- **Temporary Dynamic Trace Boost:** Temporarily set `OTEL_TRACES_SAMPLER=always_on` on the target service during active debugging sessions.

## Verification Steps & Escalation Criteria
- **Verification:** Collector dropped span count returns to zero, test requests generate end-to-end continuous spans in Jaeger with correlated logs in Loki, and Sherlog investigations reach conclusive root-cause determinations.
- **Escalation Criteria:** If critical compliance logging or audit trail telemetry is lost, alert Observability Engineering Lead and Security Officer (P1).
