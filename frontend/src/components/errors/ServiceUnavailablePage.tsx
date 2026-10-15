import React, { useState } from "react"
import { ServerCrash, RefreshCw, LayoutDashboard, Clock, Wrench } from "lucide-react"
import { Button } from "../common/Button"
import { Card } from "../common/Card"

interface ServiceUnavailablePageProps {
  isMaintenance?: boolean
  serviceName?: string
  estimatedResolutionTime?: string
  onRetry?: () => Promise<void> | void
  onGoToDashboard?: () => void
}

export const ServiceUnavailablePage: React.FC<ServiceUnavailablePageProps> = ({
  isMaintenance = false,
  serviceName = "Sherlog Core API",
  estimatedResolutionTime,
  onRetry,
  onGoToDashboard = () => {
    window.location.hash = "overview"
  },
}) => {
  const [retrying, setRetrying] = useState(false)

  const handleRetry = async () => {
    if (!onRetry) {
      window.location.reload()
      return
    }
    setRetrying(true)
    try {
      await onRetry()
    } finally {
      setRetrying(false)
    }
  }

  const Icon = isMaintenance ? Wrench : ServerCrash
  const badgeText = isMaintenance ? "HTTP 503 • SCHEDULED MAINTENANCE" : "HTTP 503 • SERVICE UNAVAILABLE"
  const titleText = isMaintenance ? `${serviceName} Under Maintenance` : `${serviceName} Temporarily Unavailable`

  return (
    <div className="min-h-[75vh] flex items-center justify-center p-4">
      <Card className="max-w-lg w-full p-8 text-center space-y-6 bg-soot border border-ash/90 shadow-2xl">
        {/* State Icon */}
        <div className="w-16 h-16 rounded-xl bg-[#271E14] border border-[#4F391A] flex items-center justify-center text-amber mx-auto shadow-inner">
          <Icon className="w-8 h-8" />
        </div>

        {/* Status & Title */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-[#261E14] text-amber border border-[#4A371A]">
            <span>{badgeText}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-semibold text-bone tracking-tight font-sans">
            {titleText}
          </h1>
          <p className="text-xs sm:text-sm text-dust max-w-sm mx-auto leading-relaxed">
            {isMaintenance
              ? "Planned infrastructure maintenance is currently in progress. Workspaces and telemetry streams will resume once complete."
              : `${serviceName} is not accepting connections at this time. Other isolated modules and cached workspace data remain unaffected.`}
          </p>
        </div>

        {/* Maintenance / ETA Callout if present */}
        {estimatedResolutionTime && (
          <div className="p-3 rounded bg-ink border border-ash/70 font-mono text-xs flex items-center justify-center gap-2 text-dust max-w-sm mx-auto">
            <Clock className="w-3.5 h-3.5 text-amber" />
            <span>Estimated recovery: {estimatedResolutionTime}</span>
          </div>
        )}

        {/* Actions */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button
            variant="default"
            size="md"
            onClick={handleRetry}
            disabled={retrying}
            className="w-full sm:w-auto"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${retrying ? "animate-spin" : ""}`} />
            <span>{retrying ? "Rechecking Status..." : "Retry Connection"}</span>
          </Button>

          <Button
            variant="secondary"
            size="md"
            onClick={onGoToDashboard}
            className="w-full sm:w-auto"
          >
            <LayoutDashboard className="w-4 h-4 mr-2" />
            <span>Go to Dashboard</span>
          </Button>
        </div>

        <div className="text-[11px] font-mono text-dust/60 pt-2 border-t border-ash/40">
          Individual upstream service isolation active. Platform root is operational.
        </div>
      </Card>
    </div>
  )
}
