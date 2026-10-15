import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { NotFoundPage } from "../components/errors/NotFoundPage"
import { InternalErrorPage } from "../components/errors/InternalErrorPage"
import { AccessDeniedPage } from "../components/errors/AccessDeniedPage"
import { ServiceUnavailablePage } from "../components/errors/ServiceUnavailablePage"

describe("Sherlog Hardened Error Pages", () => {
  describe("404 — NotFoundPage", () => {
    it("renders 404 status badge, title, and attempted path", () => {
      render(<NotFoundPage attemptedPath="#/non-existent-incident" />)
      expect(screen.getByText(/HTTP 404 • NOT FOUND/i)).toBeInTheDocument()
      expect(screen.getByText(/Investigation Artifact Not Found/i)).toBeInTheDocument()
      expect(screen.getByText("#/non-existent-incident")).toBeInTheDocument()
    })

    it("triggers Go to Dashboard and Go Back callbacks", () => {
      const onDashboard = vi.fn()
      const onBack = vi.fn()
      render(<NotFoundPage onGoToDashboard={onDashboard} onGoBack={onBack} />)

      fireEvent.click(screen.getByRole("button", { name: /Go to Dashboard/i }))
      expect(onDashboard).toHaveBeenCalledTimes(1)

      fireEvent.click(screen.getByRole("button", { name: /Go Back/i }))
      expect(onBack).toHaveBeenCalledTimes(1)
    })
  })

  describe("500 — InternalErrorPage", () => {
    it("renders safe correlation ID and does not expose raw stack traces", () => {
      render(
        <InternalErrorPage
          errorId="ERR-500-TESTID"
          message="Internal server error in telemetry processor"
        />
      )
      expect(screen.getByText(/HTTP 500 • INTERNAL SERVER ERROR/i)).toBeInTheDocument()
      expect(screen.getByText("ERR-500-TESTID")).toBeInTheDocument()
      expect(
        screen.getByText("Internal server error in telemetry processor")
      ).toBeInTheDocument()
      // Never render raw stack traces
      expect(screen.queryByText(/at Object\./i)).not.toBeInTheDocument()
    })

    it("triggers reload and dashboard navigation buttons", () => {
      const onReload = vi.fn()
      const onDashboard = vi.fn()
      render(<InternalErrorPage onReload={onReload} onGoToDashboard={onDashboard} />)

      fireEvent.click(screen.getByRole("button", { name: /Reload Application/i }))
      expect(onReload).toHaveBeenCalledTimes(1)

      fireEvent.click(screen.getByRole("button", { name: /Go to Dashboard/i }))
      expect(onDashboard).toHaveBeenCalledTimes(1)
    })
  })

  describe("403 — AccessDeniedPage", () => {
    it("renders permission requirements without fake authentication forms", () => {
      render(
        <AccessDeniedPage
          requiredPermission="REMEDIATION_ADMIN"
          resourceName="configuration override"
        />
      )
      expect(screen.getByText(/HTTP 403 • ACCESS DENIED/i)).toBeInTheDocument()
      expect(screen.getByText(/Insufficient Permissions/i)).toBeInTheDocument()
      expect(screen.getByText("REMEDIATION_ADMIN")).toBeInTheDocument()
      // Asserts that no fake password/login input fields were invented
      expect(screen.queryByRole("textbox", { name: /password/i })).not.toBeInTheDocument()
    })

    it("provides Return to Dashboard action", () => {
      const onDashboard = vi.fn()
      render(<AccessDeniedPage onGoToDashboard={onDashboard} />)
      fireEvent.click(screen.getByRole("button", { name: /Return to Dashboard/i }))
      expect(onDashboard).toHaveBeenCalledTimes(1)
    })
  })

  describe("503 — ServiceUnavailablePage", () => {
    it("distinguishes scheduled maintenance mode from unexpected outage", () => {
      const { rerender } = render(
        <ServiceUnavailablePage isMaintenance={true} serviceName="Sherlog API" />
      )
      expect(screen.getByText(/HTTP 503 • SCHEDULED MAINTENANCE/i)).toBeInTheDocument()
      expect(screen.getByText(/Sherlog API Under Maintenance/i)).toBeInTheDocument()

      rerender(<ServiceUnavailablePage isMaintenance={false} serviceName="Prometheus Scraper" />)
      expect(screen.getByText(/HTTP 503 • SERVICE UNAVAILABLE/i)).toBeInTheDocument()
      expect(screen.getByText(/Prometheus Scraper Temporarily Unavailable/i)).toBeInTheDocument()
    })

    it("handles retry action with loading state", async () => {
      const onRetry = vi.fn().mockResolvedValue(undefined)
      render(<ServiceUnavailablePage onRetry={onRetry} />)

      const retryBtn = screen.getByRole("button", { name: /Retry Connection/i })
      fireEvent.click(retryBtn)
      expect(onRetry).toHaveBeenCalledTimes(1)
    })
  })
})
