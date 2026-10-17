import React from "react"
import {
  AlertTriangle,
  Server,
  Settings,
  ArrowLeft,
} from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import { Badge } from "../common/Badge"
import { Button } from "../common/Button"
import { KnowledgeBase } from "./KnowledgeBase"
import { AuditLogsView } from "./AuditLogsView"
import { SettingsView } from "./SettingsView"
import { EvaluationsView } from "./EvaluationsView"
import { mockIncidents } from "../../mocks/incidents"
import { mockServices } from "../../mocks/services"
import type { NavItemKey } from "../shell/Sidebar"

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
            {mockIncidents.length} recorded incidents
          </span>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>
              <AlertTriangle className="w-4 h-4 text-vermilion" />
              <span>Incident Queue &amp; History</span>
            </CardTitle>
          </CardHeader>
          <div className="divide-y divide-ash/60">
            {mockIncidents.map((inc) => (
              <div
                key={inc.id}
                onClick={() => onSelectIncident?.(inc.id)}
                className="py-3 px-2.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5 hover:bg-ink/50 transition-colors cursor-pointer rounded"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-dust shrink-0">{inc.id}</span>
                    <span className="text-sm font-medium text-bone hover:text-amber transition-colors">
                      {inc.title}
                    </span>
                    <Badge variant={inc.status === "INVESTIGATING" ? "investigating" : "resolved"}>
                      {inc.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-dust mt-1 leading-relaxed">{inc.summary}</p>
                </div>
                <div className="font-mono text-xs text-dust shrink-0 text-left sm:text-right pt-1 sm:pt-0 border-t sm:border-t-0 border-ash/40">
                  <div className="text-bone/80 font-medium">{inc.service}</div>
                  <div className="text-[10px] text-dust/70">{inc.openedAt}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    )
  }

  if (tab === "services") {
    return (
      <div className="space-y-5 max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={onBackToOverview}>
              <ArrowLeft className="w-4 h-4 mr-1" /> Overview
            </Button>
            <h2 className="text-xl font-semibold text-bone">Monitored Services</h2>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {mockServices.map((srv) => (
            <Card key={srv.id} className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Server className="w-4 h-4 text-dust" />
                  <span className="font-medium text-bone text-base">{srv.displayName}</span>
                </div>
                <Badge variant={srv.status === "HEALTHY" ? "healthy" : "degraded"}>
                  {srv.status}
                </Badge>
              </div>
              <div className="grid grid-cols-3 gap-2 font-mono text-xs pt-2 border-t border-ash/60">
                <div>
                  <span className="text-dust text-[10px] block">UPTIME</span>
                  <span className="text-bone">{srv.uptime}%</span>
                </div>
                <div>
                  <span className="text-dust text-[10px] block">P95 LATENCY</span>
                  <span className="text-bone">{srv.p95Latency}</span>
                </div>
                <div>
                  <span className="text-dust text-[10px] block">ERROR RATE</span>
                  <span className="text-bone">{srv.errorRate}</span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    )
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
