import React from "react"
import { ShieldAlert, ArrowLeft, LayoutDashboard, Lock } from "lucide-react"
import { Button } from "../common/Button"
import { Card } from "../common/Card"

interface AccessDeniedPageProps {
  requiredPermission?: string
  resourceName?: string
  onGoToDashboard?: () => void
  onGoBack?: () => void
}

export const AccessDeniedPage: React.FC<AccessDeniedPageProps> = ({
  requiredPermission = "OPERATOR_ADMIN",
  resourceName = "this operation",
  onGoToDashboard = () => {
    window.location.hash = "overview"
  },
  onGoBack = () => {
    if (window.history.length > 1) {
      window.history.back()
    } else {
      window.location.hash = "overview"
    }
  },
}) => {
  return (
    <div className="min-h-[75vh] flex items-center justify-center p-4">
      <Card className="max-w-lg w-full p-8 text-center space-y-6 bg-soot border border-ash/90 shadow-2xl">
        {/* Lock/Shield Icon */}
        <div className="w-16 h-16 rounded-xl bg-[#281A14] border border-[#502F1C] flex items-center justify-center text-amber mx-auto shadow-inner">
          <Lock className="w-8 h-8" />
        </div>

        {/* Status & Title */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-[#2A1F16] text-amber border border-[#48371C]">
            <ShieldAlert className="w-3 h-3" />
            <span>HTTP 403 • ACCESS DENIED</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-semibold text-bone tracking-tight font-sans">
            Insufficient Permissions
          </h1>
          <p className="text-xs sm:text-sm text-dust max-w-sm mx-auto leading-relaxed">
            Your current operational role does not have authorization to perform {resourceName}.
          </p>
        </div>

        {/* Required Capability Notice */}
        <div className="p-3 rounded bg-ink border border-ash/70 font-mono text-xs text-left max-w-sm mx-auto space-y-1">
          <div className="text-dust/70 text-[10px] uppercase tracking-wider">Required Capability</div>
          <div className="text-amber font-medium">{requiredPermission}</div>
          <div className="text-dust text-[11px] pt-1 border-t border-ash/40">
            Contact your platform security officer to request capability elevation.
          </div>
        </div>

        {/* Safe Navigation Actions */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button variant="secondary" size="md" onClick={onGoBack} className="w-full sm:w-auto">
            <ArrowLeft className="w-4 h-4 mr-2" />
            <span>Go Back</span>
          </Button>

          <Button variant="default" size="md" onClick={onGoToDashboard} className="w-full sm:w-auto">
            <LayoutDashboard className="w-4 h-4 mr-2" />
            <span>Return to Dashboard</span>
          </Button>
        </div>

        <div className="text-[11px] font-mono text-dust/60 pt-2 border-t border-ash/40">
          Sherlog Role-Based Capability Enforcement
        </div>
      </Card>
    </div>
  )
}
