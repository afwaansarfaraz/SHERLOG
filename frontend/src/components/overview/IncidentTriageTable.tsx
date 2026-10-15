import React from "react"
import { AlertTriangle, CheckCircle2, ArrowRight } from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import { Badge } from "../common/Badge"
import { EmptyState } from "../common/EmptyState"
import type { Incident } from "../../types"

interface IncidentTriageTableProps {
  incidents: Incident[]
  onSelectIncident?: (id: string) => void
  onViewAll?: () => void
}

export const IncidentTriageTable: React.FC<IncidentTriageTableProps> = ({
  incidents,
  onSelectIncident,
  onViewAll,
}) => {
  return (
    <Card className="flex flex-col h-full">
      <CardHeader>
        <CardTitle>
          <AlertTriangle className="w-4 h-4 text-vermilion" />
          <span>Active Incidents</span>
        </CardTitle>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="text-xs text-dust hover:text-bone font-medium flex items-center gap-1 transition-colors group"
          >
            <span>View all</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </button>
        )}
      </CardHeader>

      <div className="space-y-2.5 flex-1">
        {incidents.length === 0 ? (
          <EmptyState
            variant="no-incidents"
            className="py-6 border-0 bg-transparent"
          />
        ) : (
          incidents.slice(0, 3).map((incident) => {
            const isInvestigating = incident.status === "INVESTIGATING"

            return (
              <div
                key={incident.id}
                onClick={() => onSelectIncident?.(incident.id)}
                className="flex items-center justify-between p-3 rounded-md bg-ink/50 border border-ash/70 hover:border-[#4A4237] hover:bg-ink/80 transition-all cursor-pointer group"
              >
                {/* Left: Icon, Title & Service */}
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className={`w-7 h-7 rounded flex items-center justify-center shrink-0 border ${
                      isInvestigating
                        ? "bg-[#291714] border-[#4A241E] text-vermilion"
                        : "bg-[#162722] border-[#234A3E] text-verdigris"
                    }`}
                  >
                    {isInvestigating ? (
                      <AlertTriangle className="w-3.5 h-3.5" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    )}
                  </div>

                  <div className="truncate">
                    <div className="text-xs font-medium text-bone group-hover:text-amber transition-colors truncate">
                      {incident.title}
                    </div>
                    <div className="text-[11px] text-dust font-sans truncate">{incident.service}</div>
                  </div>
                </div>

                {/* Right: ID, Status Badge & Time */}
                <div className="flex items-center gap-3 shrink-0 ml-2">
                  <span className="font-mono text-[11px] text-dust hidden sm:inline-block">
                    {incident.id}
                  </span>

                  <div className="text-right">
                    <Badge variant={isInvestigating ? "investigating" : "resolved"}>
                      {incident.status}
                    </Badge>
                    <div className="text-[10px] font-mono text-dust mt-0.5">{incident.openedAt}</div>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </Card>
  )
}
