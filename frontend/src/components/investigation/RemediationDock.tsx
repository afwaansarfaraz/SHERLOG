import React from "react"
import { CheckCircle2, Wrench, Code2, Check, X, ShieldAlert } from "lucide-react"
import { Card } from "../common/Card"
import { Button } from "../common/Button"
import type { RemediationProposal, RemediationApprovalStatus } from "../../types"

interface RemediationDockProps {
  remediation: RemediationProposal
  approvalStatus: RemediationApprovalStatus
  onApprove: () => void
  onReject: () => void
  onOpenDiff: () => void
}

export const RemediationDock: React.FC<RemediationDockProps> = ({
  remediation,
  approvalStatus,
  onApprove,
  onReject,
  onOpenDiff,
}) => {
  const isApproved = approvalStatus === "APPROVED"
  const isRejected = approvalStatus === "REJECTED"

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      {/* Left Card (6 cols): Proposed Root Cause */}
      <Card className="lg:col-span-6 p-4 sm:p-5 flex items-start gap-4 bg-soot border border-ash/90">
        <div className="w-9 h-9 rounded-full bg-[#162722] border border-[#234A3E] flex items-center justify-center text-verdigris shrink-0 mt-0.5">
          <CheckCircle2 className="w-5 h-5" />
        </div>

        <div className="space-y-1.5 flex-1 min-w-0">
          <div className="text-[11px] font-mono uppercase tracking-wider text-dust">
            Proposed Root Cause
          </div>
          <h3 className="text-sm sm:text-base font-semibold text-bone">
            {remediation.rootCauseTitle}
          </h3>
          <p className="text-xs text-dust leading-relaxed">{remediation.rootCauseDescription}</p>
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
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#162722] text-verdigris border border-[#234A3E] font-medium">
                APPROVED
              </span>
            )}

            {isRejected && (
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#2B1518] text-oxblood border border-[#522127] font-medium">
                REJECTED
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
                <span>Approved by Afwaan</span>
              </div>
            ) : isRejected ? (
              <div className="text-xs font-mono text-oxblood flex items-center gap-1.5">
                <X className="w-4 h-4" />
                <span>Rejected — Awaiting revised proposal</span>
              </div>
            ) : (
              <>
                <Button variant="verdigris" size="sm" onClick={onApprove}>
                  <Check className="w-3.5 h-3.5 mr-1" />
                  <span>Approve</span>
                </Button>

                <Button variant="oxblood" size="sm" onClick={onReject}>
                  <X className="w-3.5 h-3.5 mr-1" />
                  <span>Reject</span>
                </Button>
              </>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}
