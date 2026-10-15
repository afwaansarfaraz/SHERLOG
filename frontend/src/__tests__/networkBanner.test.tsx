import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { NetworkBanner } from "../components/common/NetworkBanner"

describe("Sherlog NetworkBanner & Offline Resilience", () => {
  it("renders offline banner when in offline state", () => {
    render(<NetworkBanner overrideState="offline" />)
    expect(screen.getByRole("alert")).toBeInTheDocument()
    expect(screen.getByText(/No Internet Connection:/i)).toBeInTheDocument()
    expect(
      screen.getByText(/Cached dashboard and investigation workspace data remain viewable/i)
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Retry Connection/i })).toBeInTheDocument()
  })

  it("renders backend API unreachable when device has network but API fails", () => {
    render(<NetworkBanner overrideState="backend-unreachable" />)
    expect(screen.getByRole("alert")).toBeInTheDocument()
    expect(screen.getByText(/Backend API Service Unreachable:/i)).toBeInTheDocument()
    expect(
      screen.getByText(/internet connection is active, but the Sherlog API cluster cannot be reached/i)
    ).toBeInTheDocument()
  })

  it("renders scheduled maintenance state when maintenance mode is active", () => {
    render(<NetworkBanner overrideState="maintenance" />)
    expect(screen.getByRole("alert")).toBeInTheDocument()
    expect(screen.getByText(/Scheduled Sherlog API Maintenance:/i)).toBeInTheDocument()
  })

  it("minimizes to floating status pill when dismissed", () => {
    render(<NetworkBanner overrideState="offline" />)
    const dismissBtn = screen.getByRole("button", { name: /Dismiss network warning banner/i })
    fireEvent.click(dismissBtn)

    // Alert banner removed, replaced by compact pill
    expect(screen.queryByText(/No Internet Connection:/i)).not.toBeInTheDocument()
    expect(screen.getByText("Offline Mode")).toBeInTheDocument()
  })

  it("triggers onManualRetry callback when Retry button clicked", () => {
    const onRetry = vi.fn()
    render(<NetworkBanner overrideState="backend-unreachable" onManualRetry={onRetry} />)
    const retryBtn = screen.getByRole("button", { name: /Retry Connection/i })
    fireEvent.click(retryBtn)
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it("renders nothing when online without restored flash", () => {
    const { container } = render(<NetworkBanner overrideState="online" />)
    expect(container.firstChild).toBeNull()
  })
})
