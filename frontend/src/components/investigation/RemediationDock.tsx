import React, { useState } from "react"
import {
  CheckCircle2,
  Wrench,
  Code2,
  Check,
  X,
  ShieldAlert,
  Loader2,
  AlertCircle,
  History,
  ChevronDown,
  ChevronUp,
} from "lucide-react"
import { Card } from "../common/Card"
import { Button } from "../common/Button"
import type { RemediationProposal, RemediationApprovalStatus, AuditLogEntry } from "../../types"

interface RemediationDockProps {
  remediation: RemediationProposal
  approvalStatus: RemediationApprovalStatus
  isSubmitting?: boolean
  submitError?: string | null
  auditLog?: AuditLogEntry[]
  onApprove: (reason?: string) => void | Promise<unknown>
  onReject: (reason?: string) => void | Promise<unknown>
  onOpenDiff: () => void
}

export const RemediationDock: React.FC<RemediationDockProps> = ({
  remediation,
  approvalStatus,
  isSubmitting = false,
  submitError = null,
  auditLog = [],
  onApprove,
  onReject,
  onOpenDiff,
}) => {
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [rejectReason, setRejectReason] = useState("")
  const [showAuditTrail, setShowAuditTrail] = useState(false)

  const isApproved = approvalStatus === "APPROVED"
  const isRejected = approvalStatus === "REJECTED"
  const isAwaiting = approvalStatus === "AWAITING_APPROVAL"

  const handleConfirmReject = async () => {
    await onReject(rejectReason.trim() || undefined)
    setShowRejectForm(false)
    setRejectReason("")
  }

  const handleApprove = async () => {
    await onApprove()
  }

  return (
    <div className="space-y-3">
      {/* Error Banner if API submission fails */}
      {submitError && (
        <div
          role="alert"
          className="p-3 bg-[#2B1518] border border-[#522127] rounded text-oxblood text-xs flex items-center gap-2"
        >
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="font-medium">Action Failed: {submitError}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Card (6 cols): Proposed Root Cause */}
        <Card className="lg:col-span-6 p-4 sm:p-5 flex items-start gap-4 bg-soot border border-ash/90">
          <div className="w-9 h-9 rounded-full bg-[#162722] border border-[#234A3E] flex items-center justify-center text-verdigris shrink-0 mt-0.5">
            <CheckCircle2 className="w-5 h-5" />
          </div>

          <div className="space-y-1.5 flex-1 min-w-0">
            <div className="text-[11px] font-mono uppercase tracking-wider text-dust flex items-center justify-between">
              <span>Proposed Root Cause</span>
              {remediation.id && (
                <span className="text-[10px] text-dust font-mono">
                  Proposal: {remediation.id}
                </span>
              )}
            </div>
            <h3 className="text-sm sm:text-base font-semibold text-bone">
              {remediation.rootCauseTitle}
            </h3>
            <p className="text-xs text-dust leading-relaxed">
              {remediation.rootCauseDescription}
            </p>
          </div>
        </Card>

        {/* Right Card (6 cols): Proposed Remediation & Approval Controls */}
        <Card className="lg:col-span-6 p-4 sm:p-5 flex flex-col justify-between bg-soot border border-ash/90 space-y-3">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <div className="text-[11px] font-mono uppercase tracking-wider text-amber flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>Proposed Remediation (Manual Approval Required)</span>
              </div>

              {isApproved && (
                <span
                  data-testid="status-approved-badge"
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#162722] text-verdigris border border-[#234A3E] font-medium"
                >
                  APPROVED
                </span>
              )}

              {isRejected && (
                <span
                  data-testid="status-rejected-badge"
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#2B1518] text-oxblood border border-[#522127] font-medium"
                >
                  REJECTED
                </span>
              )}

              {isAwaiting && (
                <span
                  data-testid="status-awaiting-badge"
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#2B2315] text-amber border border-[#524127] font-medium"
                >
                  AWAITING APPROVAL
                </span>
              )}
            </div>

            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded bg-[#27211B] border border-ash flex items-center justify-center text-bone shrink-0 mt-0.5">
                <Wrench className="w-3.5 h-3.5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-bone">{remediation.actionTitle}</h4>
                <p className="text-xs text-dust mt-0.5">{remediation.actionDescription}</p>
              </div>
            </div>
          </div>

          {/* Inline Rejection Reason Form */}
          {showRejectForm && (
            <div className="p-3 bg-ink/90 border border-ash rounded-md space-y-2 mt-2">
              <label className="text-xs font-mono text-dust block">
                Rejection Reason (optional):
              </label>
              <input
                type="text"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g. Memory pressure too high for scaling..."
                className="w-full px-2.5 py-1.5 text-xs bg-soot border border-ash rounded text-bone placeholder-dust/60 focus:outline-none focus:border-amber"
                disabled={isSubmitting}
                autoFocus
              />
              <div className="flex items-center justify-end gap-2 pt-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowRejectForm(false)}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  variant="oxblood"
                  size="sm"
                  onClick={handleConfirmReject}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                  ) : (
                    <X className="w-3.5 h-3.5 mr-1" />
                  )}
                  <span>Confirm Rejection</span>
                </Button>
              </div>
            </div>
          )}

          {/* Action Controls & Diff Trigger */}
          <div className="pt-2 border-t border-ash/60 flex flex-wrap items-center justify-between gap-3">
            <button
              onClick={onOpenDiff}
              className="inline-flex items-center gap-1.5 text-xs text-dust hover:text-bone font-mono transition-colors cursor-pointer group"
            >
              <Code2 className="w-3.5 h-3.5 text-amber group-hover:text-bone" />
              <span>&lt;/&gt; View Configuration Diff</span>
            </button>

            <div className="flex items-center gap-2">
              {isApproved ? (
                <div className="text-xs font-mono text-verdigris flex items-center gap-1.5">
                  <Check className="w-4 h-4" />
                  <span>
                    Approved by {remediation.approvedBy || "Afwaan"}
                    {remediation.approvedAt
                      ? ` (${new Date(remediation.approvedAt).toLocaleTimeString()})`
                      : ""}
                  </span>
                </div>
              ) : isRejected ? (
                <div className="text-xs font-mono text-oxblood flex items-center gap-1.5">
                  <X className="w-4 h-4" />
                  <span>
                    Rejected by {remediation.approvedBy || "Operator"}
                    {remediation.rejectionReason
                      ? `: "${remediation.rejectionReason}"`
                      : " — Awaiting revised proposal"}
                  </span>
                </div>
              ) : !showRejectForm ? (
                <>
                  <Button
                    variant="verdigris"
                    size="sm"
                    onClick={handleApprove}
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                    ) : (
                      <Check className="w-3.5 h-3.5 mr-1" />
                    )}
                    <span>{isSubmitting ? "Submitting..." : "Approve"}</span>
                  </Button>

                  <Button
                    variant="oxblood"
                    size="sm"
                    onClick={() => setShowRejectForm(true)}
                    disabled={isSubmitting}
                  >
                    <X className="w-3.5 h-3.5 mr-1" />
                    <span>Reject</span>
                  </Button>
                </>
              ) : null}
            </div>
          </div>
        </Card>
      </div>

      {/* Audit Trail Section */}
      {auditLog && auditLog.length > 0 && (
        <Card className="p-3 bg-ink/60 border border-ash/80">
          <button
            onClick={() => setShowAuditTrail((prev) => !prev)}
            className="w-full flex items-center justify-between text-left text-xs font-mono text-dust hover:text-bone transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <History className="w-3.5 h-3.5 text-amber" />
              <span className="font-semibold uppercase tracking-wider text-bone">
                Audit Trail & Human Decisions ({auditLog.length})
              </span>
            </div>
            {showAuditTrail ? (
              <ChevronUp className="w-3.5 h-3.5 text-dust" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5 text-dust" />
            )}
          </button>

          {showAuditTrail && (
            <div className="mt-3 space-y-2 border-t border-ash/60 pt-2 font-mono text-xs">
              {auditLog.map((log) => (
                <div
                  key={log.id}
                  className="p-2 rounded bg-soot/80 border border-ash/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        log.action.includes("APPROVED")
                          ? "bg-[#162722] text-verdigris border border-[#234A3E]"
                          : "bg-[#2B1518] text-oxblood border border-[#522127]"
                      }`}
                    >
                      {log.action}
                    </span>
                    <span className="text-bone font-medium">{log.actor}</span>
                    <span className="text-dust text-[11px]">{log.details}</span>
                  </div>
                  <div className="text-[10px] text-dust shrink-0">
                    {new Date(log.timestamp).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
