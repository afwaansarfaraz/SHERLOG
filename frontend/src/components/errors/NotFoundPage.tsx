import React from "react"
import { SearchX, ArrowLeft, LayoutDashboard, Shield } from "lucide-react"
import { Button } from "../common/Button"
import { Card } from "../common/Card"

interface NotFoundPageProps {
  attemptedPath?: string
  onGoToDashboard?: () => void
  onGoBack?: () => void
}

export const NotFoundPage: React.FC<NotFoundPageProps> = ({
  attemptedPath,
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
        {/* Brand Icon Header */}
        <div className="w-16 h-16 rounded-xl bg-ink border border-ash/80 flex items-center justify-center text-amber mx-auto shadow-inner">
          <SearchX className="w-8 h-8" />
        </div>

        {/* Status & Title */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-[#261F16] text-amber border border-[#48371C]">
            <Shield className="w-3 h-3" />
            <span>HTTP 404 • NOT FOUND</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-semibold text-bone tracking-tight font-sans">
            Investigation Artifact Not Found
          </h1>
          <p className="text-xs sm:text-sm text-dust max-w-sm mx-auto leading-relaxed">
            The requested route, incident ID, or telemetry view does not exist or may have been archived.
          </p>
        </div>

        {/* Attempted path display if available */}
        {attemptedPath && (
          <div className="p-2.5 rounded bg-ink border border-ash/60 font-mono text-xs text-dust truncate max-w-sm mx-auto">
            <span className="text-dust/70">Target: </span>
            <span className="text-bone">{attemptedPath}</span>
          </div>
        )}

        {/* Action Controls */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button variant="secondary" size="md" onClick={onGoBack} className="w-full sm:w-auto">
            <ArrowLeft className="w-4 h-4 mr-2" />
            <span>Go Back</span>
          </Button>

          <Button variant="default" size="md" onClick={onGoToDashboard} className="w-full sm:w-auto">
            <LayoutDashboard className="w-4 h-4 mr-2" />
            <span>Go to Dashboard</span>
          </Button>
        </div>

        <div className="text-[11px] font-mono text-dust/60 pt-2 border-t border-ash/40">
          Sherlog AI Incident Investigation System
        </div>
      </Card>
    </div>
  )
}
