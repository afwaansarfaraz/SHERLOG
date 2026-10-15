import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { MetricsView } from "../components/investigation/MetricsView"
import { LogsView } from "../components/investigation/LogsView"
import { TracesView } from "../components/investigation/TracesView"
import type { InvestigationLogEntry, TraceSpan } from "../types"

describe("Observability Telemetry Panels Hardening", () => {
  describe("MetricsView (Prometheus)", () => {
    it("renders loading skeleton when isLoading is true", () => {
      render(<MetricsView isLoading={true} />)
      expect(screen.getByLabelText(/Loading telemetry metrics/i)).toBeInTheDocument()
    })

    it("renders isolated error state on Prometheus failure without crashing", () => {
      const onRetry = vi.fn()
      render(
        <MetricsView
          error="Prometheus cluster endpoint /api/v1/query returned 502"
          onRetry={onRetry}
        />
      )
      expect(
        screen.getByText(/Prometheus Telemetry Provider Unavailable/i)
      ).toBeInTheDocument()
      expect(
        screen.getByText(/Prometheus cluster endpoint \/api\/v1\/query returned 502/i)
      ).toBeInTheDocument()

      const retryBtn = screen.getByRole("button", { name: /Retry Prometheus Query/i })
      fireEvent.click(retryBtn)
      expect(onRetry).toHaveBeenCalledTimes(1)
    })

    it("renders semantic empty state when no metrics returned", () => {
      render(<MetricsView isEmpty={true} />)
      expect(screen.getByText(/No Prometheus Metrics in Time Window/i)).toBeInTheDocument()
    })

    it("displays partial telemetry warning when some scrapes fail", () => {
      render(<MetricsView isPartial={true} />)
      expect(screen.getByText(/Partial Telemetry:/i)).toBeInTheDocument()
    })
  })

  describe("LogsView (Loki)", () => {
    const mockLogs: InvestigationLogEntry[] = [
      {
        id: "log-1",
        timestamp: "19:42:08.102",
        level: "ERROR",
        service: "orders",
        message: "HikariPool-1 - Connection is not available, request timed out after 30000ms.",
        traceId: "8f4a210bc931e4",
      },
    ]

    it("renders loading skeleton when isLoading is true", () => {
      render(<LogsView logs={[]} isLoading={true} />)
      expect(screen.getByLabelText(/Loading logs/i)).toBeInTheDocument()
    })

    it("renders isolated error state on Loki failure with retry trigger", () => {
      const onRetry = vi.fn()
      render(<LogsView logs={[]} error="Loki connection timeout" onRetry={onRetry} />)
      expect(screen.getByText(/Loki Log Telemetry Engine Unavailable/i)).toBeInTheDocument()

      const retryBtn = screen.getByRole("button", { name: /Retry Log Stream/i })
      fireEvent.click(retryBtn)
      expect(onRetry).toHaveBeenCalledTimes(1)
    })

    it("filters logs by search input and shows empty search state when none match", () => {
      render(<LogsView logs={mockLogs} />)
      expect(screen.getByText(/HikariPool-1/i)).toBeInTheDocument()

      const searchInput = screen.getByPlaceholderText(/Filter logs\.\.\./i)
      fireEvent.change(searchInput, { target: { value: "non-existent-search-term" } })

      expect(screen.queryByText(/HikariPool-1/i)).not.toBeInTheDocument()
      expect(screen.getByText(/No Matching Records Found/i)).toBeInTheDocument()
    })
  })

  describe("TracesView (Jaeger)", () => {
    const mockTraces: TraceSpan[] = [
      {
        id: "span-1",
        name: "POST /api/v1/orders/checkout",
        service: "api-gateway",
        startOffsetMs: 0,
        durationMs: 1240,
        statusCode: "ERROR",
        attributes: { "http.status_code": 500 },
      },
    ]

    it("renders loading skeleton when isLoading is true", () => {
      render(<TracesView traces={[]} isLoading={true} />)
      expect(screen.getByLabelText(/Loading traces/i)).toBeInTheDocument()
    })

    it("renders isolated error state on Jaeger failure with retry trigger", () => {
      const onRetry = vi.fn()
      render(<TracesView traces={[]} error="Jaeger gRPC disconnected" onRetry={onRetry} />)
      expect(
        screen.getByText(/Jaeger Distributed Trace Provider Unavailable/i)
      ).toBeInTheDocument()

      const retryBtn = screen.getByRole("button", { name: /Retry Jaeger Trace/i })
      fireEvent.click(retryBtn)
      expect(onRetry).toHaveBeenCalledTimes(1)
    })

    it("renders trace waterfall spans accurately", () => {
      render(<TracesView traces={mockTraces} />)
      expect(screen.getByText("POST /api/v1/orders/checkout")).toBeInTheDocument()
      expect(screen.getByText("1240ms")).toBeInTheDocument()
    })
  })
})
