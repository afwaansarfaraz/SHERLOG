import React, { StrictMode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { act, render, renderHook, screen, waitFor } from "@testing-library/react"
import { useInvestigation } from "../hooks/useInvestigation"
import { InvestigationWorkspace } from "../components/investigation/InvestigationWorkspace"
import { ToastProvider } from "../hooks/useToast"

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

describe("live incident investigation", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("triggers one real investigation in StrictMode and displays persisted telemetry values", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      if (init?.method === "POST") {
        return jsonResponse({
          incident_id: "INC-00999",
          investigation_id: "INV-INC-00999",
          service: "orders",
          status: "COMPLETED",
          summary: "Slow query evidence matched in the Orders service.",
          root_cause: "slow_database_query",
          hypotheses: [{
            id: "h1",
            rank: 1,
            title: "Slow database query",
            root_cause: "slow_database_query",
            score: 85,
            likelihood: "LIKELY",
            verified: true,
            causal_explanation: "A real query latency signal matched the alert.",
            supporting_evidence: ["prometheus:slow_queries_total"],
          }],
          evidence: [{
            id: "ev-1",
            type: "metric",
            title: "prometheus:Slow Query Count",
            source: "prometheus",
            summary: "Slow Query Count: 7 (observed: 7.0)",
            polarity: "neutral",
            timestamp: "2026-10-23T12:00:00Z",
          }],
          tool_executions: [{ tool: "PrometheusTool", query: "slow_queries_total{service='orders'}", status: "SUCCESS", duration_ms: 12 }],
          evidence_count: 1,
          retrieved_sources: [],
          retrieval_status: "NO_DOCUMENTS_FOUND",
          remediation: {
            id: "REM-INC-00999",
            incident_id: "INC-00999",
            root_cause_title: "Slow database query",
            root_cause_description: "Observed slow query count 7.",
            action_title: "Review query plan",
            action_description: "Human approval is required.",
            target_service: "orders",
            status: "AWAITING_APPROVAL",
          },
          started_at: "2026-10-23T12:00:00Z",
          is_simulated: false,
        }, 201)
      }
      return jsonResponse({ detail: "No investigation found" }, 404)
    })

    const wrapper = ({ children }: { children: React.ReactNode }) => <StrictMode>{children}</StrictMode>
    const { result } = renderHook(() => useInvestigation("INC-00999"), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1)
    expect(result.current.data.incidentId).toBe("INC-00999")
    expect(result.current.data.service).toBe("orders")
    expect(result.current.data.evidence[0]?.summary).toContain("observed: 7.0")
    expect(result.current.data.evidence[0]?.source).toBe("prometheus")
    expect(result.current.data.hypotheses[0]?.title).toBe("Slow database query")
    expect(result.current.dynamicHypotheses[0]).toMatchObject({
      score: 85,
      likelihood: "LIKELY",
      verified: true,
    })
    expect(result.current.visibleEvidence).toHaveLength(1)
    expect(result.current.investigationError).toBeNull()
  })

  it("does not substitute demo data for a persisted failed real investigation", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      incident_id: "INC-00998",
      investigation_id: "INV-INC-00998",
      service: "orders",
      status: "FAILED",
      summary: "Investigation failed while evaluating telemetry.",
      error_message: "state transition failed",
      evidence: [{
        id: "ev-1",
        type: "log",
        title: "log:orders",
        source: "log",
        summary: "Slow query fault active",
        polarity: "neutral",
        timestamp: "2026-10-23T12:00:00Z",
      }],
      tool_executions: [],
      remediation: null,
      is_simulated: false,
    }))

    const { result } = renderHook(() => useInvestigation("INC-00998"))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.data.incidentId).toBe("INC-00998")
    expect(result.current.data.title).toBe("Investigation failed while evaluating telemetry.")
    expect(result.current.data.hypotheses).toEqual([])
    expect(result.current.data.evidence[0]?.summary).toBe("Slow query fault active")
    expect(result.current.data.remediation.id).toBe("")
    expect(result.current.investigationError).toBe("state transition failed")
  })

  it("keeps an older retry response from replacing the newly selected incident", async () => {
    let finishRetry!: (response: Response) => void
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (init?.method === "POST") {
        return new Promise<Response>((resolve) => { finishRetry = resolve })
      }
      const incidentId = String(input).includes("INC-00997") ? "INC-00997" : "INC-00996"
      return jsonResponse({
        incident_id: incidentId,
        service: "orders",
        status: "COMPLETED",
        summary: `Persisted result for ${incidentId}`,
        hypotheses: [],
        evidence: [],
        tool_executions: [],
        remediation: null,
        is_simulated: false,
      })
    })

    const { result, rerender } = renderHook(
      ({ incidentId }) => useInvestigation(incidentId),
      { initialProps: { incidentId: "INC-00996" } },
    )
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    let retryPromise!: Promise<void>
    act(() => { retryPromise = result.current.retryInvestigation() })
    rerender({ incidentId: "INC-00997" })
    await waitFor(() => expect(result.current.data.incidentId).toBe("INC-00997"))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/investigations/INC-00997",
      expect.anything(),
    ))

    await act(async () => {
      finishRetry(jsonResponse({
        incident_id: "INC-00996",
        service: "orders",
        status: "COMPLETED",
        summary: "Stale retry result",
        hypotheses: [], evidence: [], tool_executions: [], remediation: null, is_simulated: false,
      }))
      await retryPromise
    })
    expect(result.current.data.incidentId).toBe("INC-00997")
    expect(result.current.data.summary).toBe("Persisted result for INC-00997")
  })

  it("offers retry for a non-terminal investigation and resumes without force", async () => {
    const investigating = {
      incident_id: "INC-00995",
      service: "orders",
      status: "INVESTIGATING",
      summary: "Investigation is still running.",
      hypotheses: [], evidence: [], tool_executions: [], remediation: null, is_simulated: false,
    }
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) =>
      jsonResponse(init?.method === "POST" ? investigating : investigating)
    )
    const { result } = renderHook(() => useInvestigation("INC-00995"))
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    await act(async () => { await result.current.retryInvestigation() })

    const postCall = fetchMock.mock.calls.find(([, init]) => init?.method === "POST")
    expect(postCall).toBeDefined()
    expect(JSON.parse(String(postCall?.[1]?.body))).toEqual({ incident_id: "INC-00995", force: false })
    expect(result.current.data.status).toBe("INVESTIGATING")
  })

  it("shows a retry action for a persisted non-terminal investigation", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      incident_id: "INC-00994",
      service: "orders",
      status: "INVESTIGATING",
      summary: "Investigation is still running.",
      hypotheses: [], evidence: [], tool_executions: [], remediation: null, is_simulated: false,
    }))

    render(
      <ToastProvider>
        <InvestigationWorkspace incidentId="INC-00994" onBackToOverview={vi.fn()} />
      </ToastProvider>,
    )
    expect(await screen.findByRole("button", { name: "Retry investigation" })).toBeInTheDocument()
  })
})
