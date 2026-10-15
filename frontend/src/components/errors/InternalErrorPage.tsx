import React, { useState } from "react"
import { AlertCircle, RefreshCw, LayoutDashboard, Copy, Check } from "lucide-react"
import { Button } from "../common/Button"
import { Card } from "../common/Card"

interface InternalErrorPageProps {
  errorId?: string
  message?: string
  onReload?: () => void
  onGoToDashboard?: () => void
}

export const InternalErrorPage: React.FC<InternalErrorPageProps> = ({
  errorId,
  message = "An unexpected server-side error occurred while processing this telemetry request.",
  onReload = () => window.location.reload(),
  onGoToDashboard = () => {
    window.location.hash = "overview"
  },
}) => {
  const [copied, setCopied] = useState(false)
  const [correlationId] = useState(
    () => errorId || "ERR-500-" + Math.random().toString(36).substring(2, 8).toUpperCase()
  )

  const copyErrorId = () => {
    navigator.clipboard?.writeText(correlationId)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-[75vh] flex items-center justify-center p-4">
      <Card className="max-w-lg w-full p-8 text-center space-y-6 bg-soot border border-ash/90 shadow-2xl">
        {/* Vermilion Alert Icon */}
        <div className="w-16 h-16 rounded-xl bg-[#2A1513] border border-[#52211C] flex items-center justify-center text-vermilion mx-auto shadow-inner">
          <AlertCircle className="w-8 h-8" />
        </div>

        {/* Status & Title */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-[#2E1815] text-vermilion border border-[#54251F]">
            <span>HTTP 500 • INTERNAL SERVER ERROR</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-semibold text-bone tracking-tight font-sans">
            Server Execution Failure
          </h1>
          <p className="text-xs sm:text-sm text-dust max-w-sm mx-auto leading-relaxed">
            {message}
          </p>
        </div>

        {/* Correlation ID Box — Safe reference without leaking traces */}
        <div className="p-3 rounded bg-ink border border-ash/70 font-mono text-xs flex items-center justify-between gap-3 text-left max-w-sm mx-auto">
          <div className="min-w-0">
            <span className="text-dust/75 block text-[10px] uppercase tracking-wider">
              Incident Correlation ID
            </span>
            <span className="text-bone font-medium truncate block">{correlationId}</span>
          </div>
          <button
            onClick={copyErrorId}
            className="p-1.5 rounded hover:bg-soot text-dust hover:text-bone border border-ash/60 shrink-0 transition-colors"
            title="Copy Correlation ID"
            aria-label="Copy incident correlation ID"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-verdigris" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
        </div>

        {/* Safe Recovery Actions */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button variant="secondary" size="md" onClick={onReload} className="w-full sm:w-auto">
            <RefreshCw className="w-4 h-4 mr-2" />
            <span>Reload Application</span>
          </Button>

          <Button variant="default" size="md" onClick={onGoToDashboard} className="w-full sm:w-auto">
            <LayoutDashboard className="w-4 h-4 mr-2" />
            <span>Go to Dashboard</span>
          </Button>
        </div>

        <div className="text-[11px] font-mono text-dust/60 pt-2 border-t border-ash/40">
          Trace captured securely in internal audit log. No sensitive data exposed.
        </div>
      </Card>
    </div>
  )
}
