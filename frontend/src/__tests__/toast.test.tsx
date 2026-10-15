import React from "react"
import { describe, it, expect } from "vitest"
import { render, screen, fireEvent, act } from "@testing-library/react"
import { ToastProvider, useToast } from "../hooks/useToast"
import { ToastContainer } from "../components/common/Toast"

const ToastTestTrigger: React.FC = () => {
  const { success, error, warning, info, clearAllToasts } = useToast()

  return (
    <div>
      <button onClick={() => success("Remediation applied successfully", "Remediation")}>
        Trigger Success
      </button>
      <button onClick={() => error("Failed to execute SQL query", "Database Error")}>
        Trigger Error
      </button>
      <button onClick={() => warning("DB pool approaching threshold", "Warning")}>
        Trigger Warning
      </button>
      <button onClick={() => info("Live activity stream connected", "Info")}>
        Trigger Info
      </button>
      <button onClick={() => clearAllToasts()}>Clear All</button>
    </div>
  )
}

describe("Sherlog Toast Notification System", () => {
  it("renders toast on action with appropriate variant", () => {
    render(
      <ToastProvider>
        <ToastTestTrigger />
        <ToastContainer />
      </ToastProvider>
    )

    fireEvent.click(screen.getByText("Trigger Success"))
    expect(screen.getByText("Remediation applied successfully")).toBeInTheDocument()
    expect(screen.getByText("Remediation")).toBeInTheDocument()
  })

  it("deduplicates identical toast messages within deduplication window", () => {
    render(
      <ToastProvider>
        <ToastTestTrigger />
        <ToastContainer />
      </ToastProvider>
    )

    // Fire duplicate error three times rapidly
    act(() => {
      fireEvent.click(screen.getByText("Trigger Error"))
      fireEvent.click(screen.getByText("Trigger Error"))
      fireEvent.click(screen.getByText("Trigger Error"))
    })

    // Should only show one card with count badge ×3
    const errorMessages = screen.getAllByText("Failed to execute SQL query")
    expect(errorMessages.length).toBe(1)
    expect(screen.getByText("×3")).toBeInTheDocument()
  })

  it("dismisses individual toast when dismiss button clicked", () => {
    render(
      <ToastProvider>
        <ToastTestTrigger />
        <ToastContainer />
      </ToastProvider>
    )

    fireEvent.click(screen.getByText("Trigger Warning"))
    expect(screen.getByText("DB pool approaching threshold")).toBeInTheDocument()

    const dismissBtn = screen.getByRole("button", { name: /Dismiss notification/i })
    fireEvent.click(dismissBtn)

    expect(screen.queryByText("DB pool approaching threshold")).not.toBeInTheDocument()
  })

  it("clears all toasts when clearAll is called", () => {
    render(
      <ToastProvider>
        <ToastTestTrigger />
        <ToastContainer />
      </ToastProvider>
    )

    fireEvent.click(screen.getByText("Trigger Info"))
    expect(screen.getByText("Live activity stream connected")).toBeInTheDocument()

    fireEvent.click(screen.getByText("Clear All"))
    expect(screen.queryByText("Live activity stream connected")).not.toBeInTheDocument()
  })
})
