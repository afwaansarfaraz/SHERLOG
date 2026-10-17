import React, { useState, useEffect, useCallback } from "react"
import {
  FileCheck2,
  Play,
  RefreshCw,
  ArrowLeft,
  CheckCircle2,
  Clock,
  BarChart3,
  ListFilter,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Sparkles,
  Layers,
  Cpu,
  BookOpen,
} from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import { Badge } from "../common/Badge"
import { Button } from "../common/Button"
import { useToast } from "../../hooks/useToast"
import { api, ApiClientError } from "../../lib/api"

interface ScenarioSummary {
  scenario_id: string
  name: string
  fault_id: string
  service: string
  description: string
  expected_root_cause: string
  expected_remediations: string[]
  evidence_count: number
  expect_insufficient_evidence: boolean
}

interface ScenarioResult {
  scenario_id: string
  name: string
  fault_id: string
  expected_root_cause: string
  predicted_root_cause: string | null
  ranked_hypotheses: string[]
  top_1_match: boolean
  top_3_match: boolean
  confidence: string
  score: number
  evidence_count: number
  supporting_evidence: string[]
  recommended_remediation: string | null
  passed: boolean
  failure_reason: string | null
  execution_time_ms: number
}

interface RunReport {
  run_id: string
  timestamp: string
  evaluator_name: string
  total_scenarios: number
  passed_scenarios: number
  failed_scenarios: number
  top_1_accuracy: number
  top_3_accuracy: number
  avg_latency_ms: number
  results: ScenarioResult[]
  failed_cases: ScenarioResult[]
}

interface RunSummaryItem {
  run_id: string
  timestamp: string
  evaluator_name: string
  total_scenarios: number
  passed_scenarios: number
  failed_scenarios: number
  top_1_accuracy: number
  top_3_accuracy: number
  avg_latency_ms: number
}

interface ComparativeMode {
  mode_name: string
  total_cases: number
  top_1_matches: number
  top_1_accuracy: number
  top_3_matches: number
  top_3_accuracy: number
  avg_latency_ms: number
  avg_tokens_used: number
  fallback_count: number
  fallback_rate: number
  avg_retrieval_relevance: number
}

interface EvaluationsViewProps {
  onBackToOverview: () => void
}

export const EvaluationsView: React.FC<EvaluationsViewProps> = ({ onBackToOverview }) => {
  const { success: toastSuccess, error: toastError } = useToast()
  const [activeSubTab, setActiveSubTab] = useState<"results" | "comparative" | "scenarios">("results")
  const [runs, setRuns] = useState<RunSummaryItem[]>([])
  const [selectedRunId, setSelectedRunId] = useState<string>("")
  const [currentRun, setCurrentRun] = useState<RunReport | null>(null)
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([])
  const [comparativeData, setComparativeData] = useState<Record<string, ComparativeMode> | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isRunningBenchmark, setIsRunningBenchmark] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null)

  // Fetch list of historical runs and scenarios on mount
  const loadInitialData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const [runsList, scenariosList] = await Promise.all([
        api.get<RunSummaryItem[]>("/api/evaluations/runs"),
        api.get<ScenarioSummary[]>("/api/evaluations/scenarios"),
      ])
      setRuns(runsList || [])
      setScenarios(scenariosList || [])

      if (runsList && runsList.length > 0) {
        const latestId = runsList[0].run_id
        setSelectedRunId(latestId)
        const report = await api.get<RunReport>(`/api/evaluations/runs/${latestId}`)
        setCurrentRun(report)
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message)
      } else {
        setError("Failed loading evaluation benchmark runs.")
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadInitialData()
  }, [loadInitialData])

  // Fetch selected run details
  const handleSelectRun = async (runId: string) => {
    setSelectedRunId(runId)
    try {
      const report = await api.get<RunReport>(`/api/evaluations/runs/${runId}`)
      setCurrentRun(report)
    } catch (err) {
      toastError(
        "Run Load Error",
        err instanceof Error ? err.message : "Failed to load selected benchmark report."
      )
    }
  }

  // Load comparative evaluation data when switching to that tab
  const handleSwitchTab = async (tab: "results" | "comparative" | "scenarios") => {
    setActiveSubTab(tab)
    if (tab === "comparative" && !comparativeData) {
      try {
        const data = await api.get<Record<string, ComparativeMode>>("/api/evaluations/comparative")
        setComparativeData(data)
      } catch (err) {
        console.warn("Failed loading comparative eval:", err)
      }
    }
  }

  // Trigger real benchmark evaluation run
  const handleTriggerRun = async () => {
    try {
      setIsRunningBenchmark(true)
      setError(null)
      const report = await api.post<RunReport>("/api/evaluations/run", {
        evaluator_name: "Rule-Based Deterministic Baseline",
        save_results: true,
      })

      setCurrentRun(report)
      setSelectedRunId(report.run_id)

      // Refresh runs list
      const updatedRuns = await api.get<RunSummaryItem[]>("/api/evaluations/runs")
      setRuns(updatedRuns)

      toastSuccess(
        "Benchmark Completed",
        `Evaluated ${report.total_scenarios} scenarios. Top-1 Accuracy: ${report.top_1_accuracy}%.`
      )
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Benchmark execution failed."
      setError(msg)
      toastError("Benchmark Run Failed", msg)
    } finally {
      setIsRunningBenchmark(false)
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      {/* Header & Main Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBackToOverview}>
            <ArrowLeft className="w-4 h-4 mr-1" /> Overview
          </Button>
          <div>
            <h2 className="text-xl font-semibold text-bone flex items-center gap-2">
              <FileCheck2 className="w-5 h-5 text-amber" />
              Evaluation Benchmark Suite
            </h2>
            <p className="text-xs text-dust mt-0.5">
              Deterministic evaluation harness executing 10 ground-truth fault scenarios with rule-based and AI agent verification.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {runs.length > 0 && (
            <select
              value={selectedRunId}
              onChange={(e) => handleSelectRun(e.target.value)}
              className="text-xs bg-obsidian border border-ash/70 rounded px-2.5 py-1.5 text-bone font-mono focus:outline-none focus:border-amber"
            >
              {runs.map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {r.run_id} ({r.top_1_accuracy}% Top-1)
                </option>
              ))}
            </select>
          )}

          <Button
            variant="default"
            size="sm"
            onClick={handleTriggerRun}
            disabled={isRunningBenchmark}
            className="flex items-center gap-1.5 shrink-0"
          >
            {isRunningBenchmark ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                Executing Run...
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" />
                Run Benchmark
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <Card className="p-4 bg-vermilion/10 border-vermilion/40 text-vermilion space-y-1">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Benchmark Suite Error</span>
          </div>
          <p className="text-xs text-bone/90">{error}</p>
        </Card>
      )}

      {/* Sub-Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-ash/60 pb-1">
        <button
          type="button"
          onClick={() => handleSwitchTab("results")}
          className={`px-3 py-1.5 text-xs font-medium rounded-t transition-colors ${
            activeSubTab === "results"
              ? "text-amber border-b-2 border-amber bg-obsidian/40"
              : "text-dust hover:text-bone"
          }`}
        >
          Run Results &amp; Diagnostics
        </button>
        <button
          type="button"
          onClick={() => handleSwitchTab("comparative")}
          className={`px-3 py-1.5 text-xs font-medium rounded-t transition-colors ${
            activeSubTab === "comparative"
              ? "text-amber border-b-2 border-amber bg-obsidian/40"
              : "text-dust hover:text-bone"
          }`}
        >
          Comparative Evaluation (3 Modes)
        </button>
        <button
          type="button"
          onClick={() => handleSwitchTab("scenarios")}
          className={`px-3 py-1.5 text-xs font-medium rounded-t transition-colors ${
            activeSubTab === "scenarios"
              ? "text-amber border-b-2 border-amber bg-obsidian/40"
              : "text-dust hover:text-bone"
          }`}
        >
          Benchmark Scenarios Catalog ({scenarios.length})
        </button>
      </div>

      {isLoading ? (
        <div className="p-10 text-center space-y-3">
          <RefreshCw className="w-6 h-6 text-amber animate-spin mx-auto" />
          <p className="text-xs font-mono text-dust">Loading evaluation benchmarks...</p>
        </div>
      ) : activeSubTab === "results" && currentRun ? (
        <div className="space-y-6">
          {/* KPI Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card className="p-3.5 bg-obsidian/60">
              <span className="text-[11px] font-mono text-dust block uppercase tracking-wider">
                Top-1 Accuracy
              </span>
              <span className="text-2xl font-bold font-mono text-verdigris mt-1 block">
                {currentRun.top_1_accuracy}%
              </span>
              <span className="text-[10px] text-dust/70 flex items-center gap-1 mt-0.5">
                <CheckCircle2 className="w-3 h-3 text-verdigris" />
                {currentRun.passed_scenarios} / {currentRun.total_scenarios} passed
              </span>
            </Card>

            <Card className="p-3.5 bg-obsidian/60">
              <span className="text-[11px] font-mono text-dust block uppercase tracking-wider">
                Top-3 Recall
              </span>
              <span className="text-2xl font-bold font-mono text-jade mt-1 block">
                {currentRun.top_3_accuracy}%
              </span>
              <span className="text-[10px] text-dust/70 flex items-center gap-1 mt-0.5">
                <BarChart3 className="w-3 h-3 text-jade" /> In ranked top 3
              </span>
            </Card>

            <Card className="p-3.5 bg-obsidian/60">
              <span className="text-[11px] font-mono text-dust block uppercase tracking-wider">
                Average Diagnosis Latency
              </span>
              <span className="text-2xl font-bold font-mono text-amber mt-1 block">
                {currentRun.avg_latency_ms} ms
              </span>
              <span className="text-[10px] text-dust/70 flex items-center gap-1 mt-0.5">
                <Clock className="w-3 h-3 text-amber" /> Fast deterministic execution
              </span>
            </Card>

            <Card className="p-3.5 bg-obsidian/60">
              <span className="text-[11px] font-mono text-dust block uppercase tracking-wider">
                Evaluator Engine
              </span>
              <span className="text-sm font-semibold font-mono text-bone mt-1 block truncate">
                {currentRun.evaluator_name}
              </span>
              <span className="text-[10px] text-dust/70 flex items-center gap-1 mt-0.5 truncate">
                Run: {currentRun.run_id}
              </span>
            </Card>
          </div>

          {/* Scenario Results Table */}
          <Card className="overflow-hidden">
            <CardHeader className="border-b border-ash/60 bg-obsidian/40 py-3">
              <div className="flex items-center justify-between">
                <CardTitle>
                  <BarChart3 className="w-4 h-4 text-amber" />
                  <span>Scenario-Level Evaluation Results ({currentRun.results.length})</span>
                </CardTitle>
                <span className="font-mono text-xs text-dust">
                  Executed at {new Date(currentRun.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </CardHeader>

            <div className="divide-y divide-ash/60">
              {currentRun.results.map((res) => {
                const isExpanded = expandedRowId === res.scenario_id

                return (
                  <div
                    key={res.scenario_id}
                    className="p-3.5 hover:bg-ink/40 transition-colors cursor-pointer"
                    onClick={() => setExpandedRowId(isExpanded ? null : res.scenario_id)}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5">
                      <div className="flex items-center gap-2.5 min-w-0 flex-1">
                        <button
                          type="button"
                          className="text-dust hover:text-bone transition-colors"
                          aria-label={isExpanded ? "Collapse" : "Expand"}
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 shrink-0" />
                          ) : (
                            <ChevronRight className="w-4 h-4 shrink-0" />
                          )}
                        </button>

                        <span className="font-mono text-xs text-dust shrink-0 font-semibold">
                          {res.scenario_id}
                        </span>

                        <Badge variant={res.passed ? "healthy" : "critical"} withDot className="shrink-0 font-mono text-[11px]">
                          {res.passed ? "PASS" : "FAIL"}
                        </Badge>

                        <div className="min-w-0">
                          <span className="text-xs font-medium text-bone hover:text-amber transition-colors">
                            {res.name}
                          </span>
                          <span className="text-[11px] text-dust/70 ml-2 font-mono">
                            [{res.fault_id}]
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 shrink-0 font-mono text-xs text-dust">
                        <div>
                          Predicted:{" "}
                          <span className={res.passed ? "text-verdigris" : "text-vermilion"}>
                            {res.predicted_root_cause || "INSUFFICIENT_EVIDENCE"}
                          </span>
                        </div>
                        <div className="text-[11px] text-dust/70">
                          {res.execution_time_ms} ms
                        </div>
                      </div>
                    </div>

                    {/* Expandable Scenario Details */}
                    {isExpanded && (
                      <div className="mt-3.5 pt-3.5 border-t border-ash/40 pl-6 space-y-2 text-xs font-mono">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-dust">
                          <div>
                            <span className="text-bone/70 block text-[10px] uppercase">Expected Ground Truth</span>
                            <span className="text-bone">{res.expected_root_cause}</span>
                          </div>
                          <div>
                            <span className="text-bone/70 block text-[10px] uppercase">Confidence Score</span>
                            <span className="text-bone">
                              {res.confidence} ({res.score} pts)
                            </span>
                          </div>
                        </div>

                        {res.recommended_remediation && (
                          <div className="p-2.5 rounded bg-obsidian border border-ash/60">
                            <span className="text-[10px] uppercase text-jade font-bold block mb-0.5">
                              Recommended Remediation
                            </span>
                            <span className="text-bone">{res.recommended_remediation}</span>
                          </div>
                        )}

                        {res.supporting_evidence && res.supporting_evidence.length > 0 && (
                          <div className="p-2.5 rounded bg-obsidian border border-ash/60 space-y-1">
                            <span className="text-[10px] uppercase text-amber font-bold block">
                              Supporting Observability Evidence ({res.supporting_evidence.length})
                            </span>
                            <ul className="list-disc list-inside space-y-0.5 text-dust text-[11px]">
                              {res.supporting_evidence.map((ev, idx) => (
                                <li key={idx} className="truncate">{ev}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {res.failure_reason && (
                          <div className="p-2.5 rounded bg-vermilion/10 border border-vermilion/40 text-vermilion">
                            <span className="text-[10px] uppercase font-bold block mb-0.5">Failure Reason</span>
                            <span>{res.failure_reason}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </Card>
        </div>
      ) : activeSubTab === "comparative" ? (
        <Card className="p-6 space-y-6">
          <CardHeader className="p-0 pb-3 border-b border-ash/60">
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber" />
              <span>Comparative Benchmark Evaluation: Baseline vs LLM vs LLM+RAG</span>
            </CardTitle>
            <p className="text-xs text-dust mt-1">
              Empirical multi-mode comparison across 5 core representative failure scenarios from Week 2 evaluation.
            </p>
          </CardHeader>

          {comparativeData ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono text-left">
                <thead className="bg-obsidian/70 text-dust uppercase text-[10px] border-b border-ash/60">
                  <tr>
                    <th className="py-2.5 px-3">Evaluation Mode</th>
                    <th className="py-2.5 px-3">Top-1 Accuracy</th>
                    <th className="py-2.5 px-3">Top-3 Recall</th>
                    <th className="py-2.5 px-3">Avg Latency</th>
                    <th className="py-2.5 px-3">Avg Tokens</th>
                    <th className="py-2.5 px-3">Fallback Rate</th>
                    <th className="py-2.5 px-3">Retrieval Relevance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ash/40">
                  {Object.entries(comparativeData).map(([key, mode]) => (
                    <tr key={key} className="hover:bg-ink/40">
                      <td className="py-3 px-3 font-semibold text-bone flex items-center gap-2">
                        {key === "baseline" ? (
                          <Layers className="w-4 h-4 text-dust" />
                        ) : key === "llm_no_rag" ? (
                          <Cpu className="w-4 h-4 text-jade" />
                        ) : (
                          <BookOpen className="w-4 h-4 text-amber" />
                        )}
                        {mode.mode_name}
                      </td>
                      <td className="py-3 px-3 text-verdigris font-bold">
                        {mode.top_1_accuracy}%
                      </td>
                      <td className="py-3 px-3 text-jade">
                        {mode.top_3_accuracy}%
                      </td>
                      <td className="py-3 px-3 text-bone">
                        {mode.avg_latency_ms} ms
                      </td>
                      <td className="py-3 px-3 text-dust">
                        {mode.avg_tokens_used.toLocaleString()}
                      </td>
                      <td className="py-3 px-3 text-dust">
                        {mode.fallback_rate}%
                      </td>
                      <td className="py-3 px-3 text-amber font-semibold">
                        {mode.avg_retrieval_relevance > 0
                          ? `${(mode.avg_retrieval_relevance * 100).toFixed(1)}%`
                          : "N/A"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-dust">
              Loading comparative evaluation baseline...
            </div>
          )}
        </Card>
      ) : (
        /* Scenarios Catalog */
        <Card className="overflow-hidden">
          <CardHeader className="border-b border-ash/60 bg-obsidian/40 py-3">
            <CardTitle className="flex items-center gap-2">
              <ListFilter className="w-4 h-4 text-amber" />
              <span>Ground-Truth Benchmark Scenarios ({scenarios.length})</span>
            </CardTitle>
          </CardHeader>
          <div className="divide-y divide-ash/60">
            {scenarios.map((scn) => (
              <div key={scn.scenario_id} className="p-4 space-y-2 hover:bg-ink/40 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-amber">
                      {scn.scenario_id}
                    </span>
                    <span className="text-sm font-semibold text-bone">
                      {scn.name}
                    </span>
                    <Badge variant="slate" className="font-mono text-[10px]">
                      {scn.service}
                    </Badge>
                  </div>
                  <span className="font-mono text-xs text-dust">
                    {scn.evidence_count} evidence items
                  </span>
                </div>
                <p className="text-xs text-dust font-sans leading-relaxed">
                  {scn.description}
                </p>
                <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-dust/80 pt-1 border-t border-ash/30">
                  <div>
                    Fault: <span className="text-bone">{scn.fault_id}</span>
                  </div>
                  <div>
                    Ground Truth: <span className="text-verdigris">{scn.expected_root_cause}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
