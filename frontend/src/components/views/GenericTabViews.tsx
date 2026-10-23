import React, { useCallback, useEffect, useRef, useState } from "react"
import {
  AlertTriangle,
  Settings,
  ArrowLeft,
  AlertCircle,
  Loader2,
  RefreshCw,
} from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import { Badge } from "../common/Badge"
import { Button } from "../common/Button"
import { KnowledgeBase } from "./KnowledgeBase"
import { AuditLogsView } from "./AuditLogsView"
import { SettingsView } from "./SettingsView"
import { EvaluationsView } from "./EvaluationsView"
import { ApplicationsView } from "./ApplicationsView"
import { api } from "../../lib/api"
import type { NavItemKey } from "../shell/Sidebar"

interface IncidentRecord {
  id: string
  title: string
  service: string
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
  status: "OPEN" | "INVESTIGATING" | "AWAITING_APPROVAL" | "RESOLVED"
  summary: string
  created_at: string
}

function statusBadgeVariant(status: IncidentRecord["status"]) {
  if (status === "INVESTIGATING") return "investigating" as const
  if (status === "AWAITING_APPROVAL") return "awaiting_approval" as const
  if (status === "RESOLVED") return "resolved" as const
  return "critical" as const
}

interface GenericTabViewProps {
  tab: NavItemKey
  onBackToOverview: () => void
  onSelectIncident?: (id: string) => void
}

export const GenericTabView: React.FC<GenericTabViewProps> = ({
  tab,
  onBackToOverview,
  onSelectIncident,
}) => {
  const [incidents, setIncidents] = useState<IncidentRecord[]>([])
  const [incidentsLoading, setIncidentsLoading] = useState(false)
  const [incidentsError, setIncidentsError] = useState<string | null>(null)
  const incidentsRequestId = useRef(0)

  const fetchIncidents = useCallback(async () => {
    const requestId = ++incidentsRequestId.current
    setIncidentsLoading(true)
    setIncidentsError(null)
    try {
      const records = await api.get<IncidentRecord[]>("/api/incidents")
      if (requestId === incidentsRequestId.current) setIncidents(records)
    } catch (err) {
      if (requestId === incidentsRequestId.current) {
        setIncidentsError(err instanceof Error ? err.message : "Failed to load incidents.")
        setIncidents([])
      }
    } finally {
      if (requestId === incidentsRequestId.current) setIncidentsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (tab === "incidents") void fetchIncidents()
  }, [fetchIncidents, tab])

  if (tab === "incidents") {
    return (
      <div className="space-y-5 max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={onBackToOverview}>
              <ArrowLeft className="w-4 h-4 mr-1" /> Overview
            </Button>
            <h2 className="text-xl font-semibold text-bone">All Incidents</h2>
          </div>
          <span className="font-mono text-xs text-dust">
            {incidentsLoading ? "Loading incidents…" : `${incidents.length} recorded incidents`}
          </span>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>
              <AlertTriangle className="w-4 h-4 text-vermilion" />
              <span>Incident Queue &amp; History</span>
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={fetchIncidents} disabled={incidentsLoading}>
              <RefreshCw className={`w-3.5 h-3.5 mr-1 ${incidentsLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </CardHeader>
          {incidentsError ? (
            <div role="alert" className="flex items-center gap-2 px-3 py-3 rounded bg-[#2E1618] border border-[#572124] text-vermilion text-xs">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{incidentsError}</span>
              <Button variant="ghost" size="sm" onClick={fetchIncidents} className="ml-auto">Retry</Button>
            </div>
          ) : incidentsLoading && incidents.length === 0 ? (
            <div role="status" className="p-8 flex flex-col items-center gap-3 text-dust text-xs">
              <Loader2 className="w-6 h-6 text-amber animate-spin" />
              Loading persisted incidents…
            </div>
          ) : incidents.length === 0 ? (
            <div role="status" className="p-8 text-center text-xs text-dust">
              No incidents have been ingested from the alert pipeline.
            </div>
          ) : (
            <div className="divide-y divide-ash/60">
              {incidents.map((inc) => (
                <button
                  key={inc.id}
                  type="button"
                  aria-label={`Open incident ${inc.id}: ${inc.title}`}
                  onClick={() => onSelectIncident?.(inc.id)}
                  className="w-full text-left py-3 px-2.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5 hover:bg-ink/50 transition-colors cursor-pointer rounded"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs text-dust shrink-0">{inc.id}</span>
                      <span className="text-sm font-medium text-bone hover:text-amber transition-colors">
                        {inc.title}
                      </span>
                      <Badge variant={statusBadgeVariant(inc.status)}>{inc.status}</Badge>
                      <Badge variant={inc.severity === "CRITICAL" || inc.severity === "HIGH" ? "critical" : "slate"}>
                        {inc.severity}
                      </Badge>
                    </div>
                    <p className="text-xs text-dust mt-1 leading-relaxed">{inc.summary}</p>
                  </div>
                  <div className="font-mono text-xs text-dust shrink-0 text-left sm:text-right pt-1 sm:pt-0 border-t sm:border-t-0 border-ash/40">
                    <div className="text-bone/80 font-medium">{inc.service}</div>
                    <div className="text-[10px] text-dust/70">
                      {new Date(inc.created_at).toLocaleString()}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>
      </div>
    )
  }

  if (tab === "services") {
    return <ApplicationsView onBackToOverview={onBackToOverview} />
  }

  if (tab === "knowledge") {
    return <KnowledgeBase onBackToOverview={onBackToOverview} />
  }

  if (tab === "audit-logs") {
    return (
      <AuditLogsView
        onBackToOverview={onBackToOverview}
        onSelectIncident={onSelectIncident}
      />
    )
  }

  if (tab === "settings") {
    return <SettingsView onBackToOverview={onBackToOverview} />
  }

  if (tab === "evaluations") {
    return <EvaluationsView onBackToOverview={onBackToOverview} />
  }

  return (
    <div className="space-y-5 max-w-7xl mx-auto">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBackToOverview}>
          <ArrowLeft className="w-4 h-4 mr-1" /> Overview
        </Button>
        <h2 className="text-xl font-semibold text-bone">{tab}</h2>
      </div>

      <Card className="p-8 text-center space-y-4">
        <div className="w-12 h-12 rounded-lg bg-ink border border-ash flex items-center justify-center text-amber mx-auto">
          <Settings className="w-6 h-6" />
        </div>
        <div className="max-w-md mx-auto">
          <h3 className="text-sm font-semibold text-bone">{tab}</h3>
          <p className="text-xs text-dust mt-1.5 leading-relaxed">Configuration workspace.</p>
        </div>
      </Card>
    </div>
  )
}
