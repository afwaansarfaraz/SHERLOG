# Sherlog — Evaluation Framework

## 1. Evaluation Philosophy

Sherlog prioritizes rigorous, reproducible evaluation over qualitative impressions.
Evaluation must measure whether the AI agent reliably identifies root causes, how efficiently it uses tokens and steps, how resilient it is against prompt injection, and how it compares against a deterministic baseline.

### Core Rules

1. **Immutable Ground Truth**: Never edit ground-truth files to improve results.
2. **Production Code Consistency**: The evaluation harness must invoke the exact same worker and agent code used in production.
3. **No Cheating / Test Deletion**: Never delete tests or modify evaluation logic to mask failures.
4. **Baseline First**: Sherlog must always be measured and reported directly against the deterministic rule-based baseline.
5. **Statistical Rigor**: Every fault scenario is evaluated across 3 runs, reporting both mean and variance.

---

## 2. Benchmark Specification

- **Total Fault Scenarios**: 20 distinct fault scenarios across the demo microservices (API, Orders, Payments, DB).
- **Runs per Scenario**: 3 runs each.
- **Minimum Total Evaluations**: 60 runs.
- **Fault Variations**: Scenarios include parameter variations and noise to prevent rigid pattern memorization.

### Ground Truth Schema Example

```yaml
fault_id: DB_POOL_EXHAUSTION_01
service: orders
root_cause: database_connection_pool_exhaustion
valid_remediations:
  - increase_pool_size
  - restart_service
```

---

## 3. Deterministic Rule-Based Baseline

Before evaluating the AI agent, a deterministic baseline is constructed using:
- Metric threshold rules (PromQL alerts)
- Known error log signatures
- Keyword pattern matching
- Fixed service heuristics

The AI agent's value proposition is evaluated by its ability to outperform this baseline in accuracy, complex correlation, and novel variance handling.

---

## 4. Evaluation Metrics

### Root-Cause Accuracy
- **Top-1 Accuracy**: Percentage of incidents where the #1 ranked hypothesis matches ground truth.
- **Top-3 Accuracy**: Percentage of incidents where ground truth is within the top 3 ranked hypotheses.

### Detection
- **Detection Rate**: True positives detected by the monitoring/webhook pipeline.
- **False Positive Rate**: Alerts triggered without corresponding injected faults.

### Efficiency & Cost
- **Steps per Incident**: Total agent loop steps taken.
- **Tokens per Incident**: Total tokens (prompt + completion) consumed.
- **Cost per Incident**: Estimated financial cost per investigation.

### Performance & Latency
- **Time-to-Diagnosis (p50)**: Median duration from alert ingestion to final diagnosis.
- **Time-to-Diagnosis (p95)**: 95th percentile duration to diagnosis.

### Safety & Resilience
- **Injection-Block Rate**: Percentage of prompt-injection attempts in logs/runbooks safely neutralized.
- **Resume Success Rate**: Percentage of successful state-resumptions after simulated worker interruption.

### Statistical Reporting
- All metrics reported as `Mean ± Variance` across the 3 repeated runs.

---

## 5. Ablation Studies

To understand the contribution of each component, five distinct configurations are evaluated:
1. **Rule-Based Baseline**
2. **Core Agent** (basic state machine without summarization/verification)
3. **Core Agent + Log Summarization** (untrusted log summarizer filter)
4. **Core Agent + Verification** (active hypothesis verification step)
5. **Full System** (Agent + Summarization + Verification + Model Routing)

---

## 6. Continuous Integration (CI) Evaluation Gate

GitHub Actions runs:
- Unit and integration tests
- A representative subset of evaluation benchmark scenarios
- Regression threshold checks (fails build if accuracy drops or cost exceeds threshold)
- Mocked/cached LLM calls for deterministic and rapid CI execution
