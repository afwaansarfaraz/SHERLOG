import React from "react"
import { X, AlertTriangle, CheckCircle2, Shield, ArrowRight } from "lucide-react"
import { Badge } from "../common/Badge"
import { Button } from "../common/Button"
import type { Incident } from "../../types"

interface IncidentDetailModalProps {
  incident: Incident | null
  onClose: () => void
  onNavigateToIncidentsTab?: () => void
}

export const IncidentDetailModal: React.FC<IncidentDetailModalProps> = ({
  incident,
  onClose,
  onNavigateToIncidentsTab,
}) => {
  if (!incident) return null

  const isInvestigating = incident.status === "INVESTIGATING"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-lg bg-soot border border-ash rounded-lg shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-ash bg-ink/50">
          <div className="flex items-center gap-2.5">
            {isInvestigating ? (
              <AlertTriangle className="w-4 h-4 text-vermilion" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-verdigris" />
            )}
            <span className="font-mono text-xs font-semibold text-bone">{incident.id}</span>
            <Badge variant={isInvestigating ? "investigating" : "resolved"}>
              {incident.status}
            </Badge>
          </div>
          <button
            onClick={onClose}
            aria-label="Close incident modal"
            className="text-dust hover:text-bone p-1 rounded hover:bg-soot transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 text-xs font-sans">
          <div>
            <h3 className="text-base font-semibold text-bone">{incident.title}</h3>
            <p className="text-dust mt-0.5">
              Service: <span className="text-bone">{incident.service}</span> • Opened:{" "}
              {incident.openedAt}
            </p>
          </div>

          <div className="p-3 rounded bg-ink/60 border border-ash/70 text-bone/90 leading-relaxed">
            {incident.summary}
          </div>

          {incident.affectedEndpoints && incident.affectedEndpoints.length > 0 && (
            <div>
              <div className="text-[11px] font-mono uppercase text-dust mb-1.5">
                Affected Endpoints
              </div>
              <div className="flex flex-wrap gap-1.5 font-mono">
                {incident.affectedEndpoints.map((ep) => (
                  <span
                    key={ep}
                    className="px-2 py-0.5 rounded bg-ink border border-ash text-bone text-[11px]"
                  >
                    {ep}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center justify-between p-3 rounded bg-[#211C18] border border-ash text-[11px] font-mono text-dust">
            <span className="flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-amber" />
              <span>Assigned Operator</span>
            </span>
            <span className="text-bone font-medium">{incident.assignedTo}</span>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-ink/60 border-t border-ash flex items-center justify-between">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={() => {
              onClose()
              if (onNavigateToIncidentsTab) onNavigateToIncidentsTab()
            }}
          >
            <span>Open Investigation Workspace</span>
            <ArrowRight className="w-3.5 h-3.5 ml-1" />
          </Button>
        </div>
      </div>
    </div>
  )
}
