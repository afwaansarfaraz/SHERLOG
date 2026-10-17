import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { RemediationDock } from "../components/investigation/RemediationDock"
import type { RemediationProposal, AuditLogEntry } from "../types"

describe("RemediationDock Component", () => {
  const baseProposal: RemediationProposal = {
    id: "REM-INC-00100",
    incidentId: "INC-00100",
    rootCauseTitle: "PostgreSQL Connection Pool Exhaustion",
    rootCauseDescription: "Orders connection pool saturated at 100%",
    actionTitle: "Increase Connection Pool Limits to 40",
    actionDescription: "Scale max pool connections to absorb traffic burst.",
    targetService: "orders",
    allowlistedAction: "scale_db_pool",
    configDiff: "pool_size: 20 -> 40",
    status: "AWAITING_APPROVAL",
  }

  it("renders proposal details and approval buttons when awaiting approval", () => {
    const onApprove = vi.fn()
    const onReject = vi.fn()
    const onOpenDiff = vi.fn()

    render(
      <RemediationDock
        remediation={baseProposal}
        approvalStatus="AWAITING_APPROVAL"
        onApprove={onApprove}
        onReject={onReject}
        onOpenDiff={onOpenDiff}
      />
    )

    expect(screen.getByText("PostgreSQL Connection Pool Exhaustion")).toBeInTheDocument()
    expect(screen.getByText("Increase Connection Pool Limits to 40")).toBeInTheDocument()
    expect(screen.getByTestId("status-awaiting-badge")).toHaveTextContent("AWAITING APPROVAL")
    expect(screen.getByRole("button", { name: /Approve/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Reject/i })).toBeInTheDocument()
  })

  it("calls onApprove when Approve button is clicked", () => {
    const onApprove = vi.fn()
    const onReject = vi.fn()
    const onOpenDiff = vi.fn()

    render(
      <RemediationDock
        remediation={baseProposal}
        approvalStatus="AWAITING_APPROVAL"
        onApprove={onApprove}
        onReject={onReject}
        onOpenDiff={onOpenDiff}
      />
    )

    const approveBtn = screen.getByRole("button", { name: /Approve/i })
    fireEvent.click(approveBtn)
    expect(onApprove).toHaveBeenCalledTimes(1)
  })

  it("opens rejection form and calls onReject with entered reason", () => {
    const onApprove = vi.fn()
    const onReject = vi.fn()
    const onOpenDiff = vi.fn()

    render(
      <RemediationDock
        remediation={baseProposal}
        approvalStatus="AWAITING_APPROVAL"
        onApprove={onApprove}
        onReject={onReject}
        onOpenDiff={onOpenDiff}
      />
    )

    const rejectBtn = screen.getByRole("button", { name: /Reject/i })
    fireEvent.click(rejectBtn)

    // Rejection reason form should now appear
    const input = screen.getByPlaceholderText(/Memory pressure too high/i)
    expect(input).toBeInTheDocument()

    fireEvent.change(input, { target: { value: "Pool scale would exceed DB RAM capacity" } })
    const confirmBtn = screen.getByRole("button", { name: /Confirm Rejection/i })
    fireEvent.click(confirmBtn)

    expect(onReject).toHaveBeenCalledWith("Pool scale would exceed DB RAM capacity")
  })

  it("renders APPROVED state and disables actions once approved", () => {
    const approvedProposal: RemediationProposal = {
      ...baseProposal,
      status: "APPROVED",
      approvedBy: "alice_sre",
      approvedAt: "2026-10-17T15:00:00Z",
    }

    render(
      <RemediationDock
        remediation={approvedProposal}
        approvalStatus="APPROVED"
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onOpenDiff={vi.fn()}
      />
    )

    expect(screen.getByTestId("status-approved-badge")).toHaveTextContent("APPROVED")
    expect(screen.getByText(/Approved by alice_sre/i)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^Approve$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^Reject$/i })).not.toBeInTheDocument()
  })

  it("renders REJECTED state with operator reason once rejected", () => {
    const rejectedProposal: RemediationProposal = {
      ...baseProposal,
      status: "REJECTED",
      approvedBy: "bob_lead",
      rejectionReason: "Requires DB index optimization instead",
    }

    render(
      <RemediationDock
        remediation={rejectedProposal}
        approvalStatus="REJECTED"
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onOpenDiff={vi.fn()}
      />
    )

    expect(screen.getByTestId("status-rejected-badge")).toHaveTextContent("REJECTED")
    expect(
      screen.getByText(/Rejected by bob_lead: "Requires DB index optimization instead"/i)
    ).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^Approve$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^Reject$/i })).not.toBeInTheDocument()
  })

  it("displays error alert when submitError is set", () => {
    render(
      <RemediationDock
        remediation={baseProposal}
        approvalStatus="AWAITING_APPROVAL"
        submitError="Backend database write timed out"
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onOpenDiff={vi.fn()}
      />
    )

    expect(screen.getByRole("alert")).toHaveTextContent("Action Failed: Backend database write timed out")
  })

  it("renders and toggles audit trail history", () => {
    const auditEntries: AuditLogEntry[] = [
      {
        id: "AUD-12345678",
        timestamp: "2026-10-17T15:05:00Z",
        action: "REMEDIATION_APPROVED",
        actor: "alice_sre",
        investigation_id: "INV-INC-00100",
        incident_id: "INC-00100",
        proposal_id: "REM-INC-00100",
        reason: "Verified capacity",
        details: "Remediation proposal approved",
      },
    ]

    render(
      <RemediationDock
        remediation={baseProposal}
        approvalStatus="AWAITING_APPROVAL"
        auditLog={auditEntries}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onOpenDiff={vi.fn()}
      />
    )

    const trailToggle = screen.getByText(/Audit Trail & Human Decisions \(1\)/i)
    expect(trailToggle).toBeInTheDocument()

    // Click to expand
    fireEvent.click(trailToggle)
    expect(screen.getByText("REMEDIATION_APPROVED")).toBeInTheDocument()
    expect(screen.getByText("alice_sre")).toBeInTheDocument()
  })
})
