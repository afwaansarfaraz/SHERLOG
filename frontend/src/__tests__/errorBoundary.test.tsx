import React from "react"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ErrorBoundary } from "../components/common/ErrorBoundary"

const ProblemChild: React.FC<{ shouldCrash?: boolean }> = ({ shouldCrash }) => {
  if (shouldCrash) {
    throw new Error("Simulated rendering explosion in widget")
  }
  return <div>Healthy Widget Content</div>
}

describe("Sherlog React ErrorBoundary", () => {
  // Silence console.error during expected boundary exceptions
  const originalError = console.error
  beforeEach(() => {
    console.error = vi.fn()
  })
  afterEach(() => {
    console.error = originalError
  })

  it("renders healthy children normally when no exception is thrown", () => {
    render(
      <ErrorBoundary moduleName="Test Module">
        <ProblemChild shouldCrash={false} />
      </ErrorBoundary>
    )
    expect(screen.getByText("Healthy Widget Content")).toBeInTheDocument()
  })

  it("catches child crash and displays isolated widget fallback with retry button", () => {
    render(
      <ErrorBoundary moduleName="Metrics Chart Widget">
        <ProblemChild shouldCrash={true} />
      </ErrorBoundary>
    )

    expect(screen.queryByText("Healthy Widget Content")).not.toBeInTheDocument()
    expect(
      screen.getByText(/Metrics Chart Widget Temporarily Unavailable/i)
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Retry Component/i })).toBeInTheDocument()
  })

  it("allows resetting the error boundary state via Retry button", () => {
    let crash = true
    const DynamicChild = () => {
      if (crash) throw new Error("Boom")
      return <div>Recovered Component Content</div>
    }

    const { rerender } = render(
      <ErrorBoundary moduleName="Dynamic Widget">
        <DynamicChild />
      </ErrorBoundary>
    )

    expect(screen.getByText(/Dynamic Widget Temporarily Unavailable/i)).toBeInTheDocument()

    // Fix problem and click retry
    crash = false
    fireEvent.click(screen.getByRole("button", { name: /Retry Component/i }))
    rerender(
      <ErrorBoundary moduleName="Dynamic Widget">
        <DynamicChild />
      </ErrorBoundary>
    )

    expect(screen.getByText("Recovered Component Content")).toBeInTheDocument()
  })

  it("renders full-screen safety layout when isRoot={true}", () => {
    render(
      <ErrorBoundary isRoot={true} moduleName="Sherlog Root Application">
        <ProblemChild shouldCrash={true} />
      </ErrorBoundary>
    )

    expect(
      screen.getByText(/APPLICATION CRITICAL SAFETY BOUNDARY/i)
    ).toBeInTheDocument()
    expect(screen.getByText(/Sherlog Session Interrupted/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Reload Sherlog/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Go to Overview/i })).toBeInTheDocument()
  })
})
