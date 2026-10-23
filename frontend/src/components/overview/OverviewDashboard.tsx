import React, { useState, useEffect } from "react"
import { KpiGrid } from "./KpiGrid"
import { IncidentTriageTable } from "./IncidentTriageTable"
import { SystemHealthCard } from "./SystemHealthCard"
import { ServiceMetricsChart } from "./ServiceMetricsChart"
import { EvaluationSummaryCard } from "./EvaluationSummaryCard"
import { RecentActivityFeed } from "./RecentActivityFeed"
import { IncidentDetailModal } from "./IncidentDetailModal"
import { ErrorBoundary } from "../common/ErrorBoundary"
import { Plus } from "lucide-react"
import { Button } from "../common/Button"
import { ConnectApplicationModal } from "../applications/ConnectApplicationModal"
import { mockIncidents } from "../../mocks/incidents"
import { mockServices } from "../../mocks/services"
import { mockRecentActivities } from "../../mocks/activities"

interface OverviewDashboardProps {
  onNavigateToTab?: (tab: string) => void
  selectedIncidentId?: string | null
  onClearSelectedIncident?: () => void
  onOpenInvestigationWorkspace?: (id: string) => void
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({
  onNavigateToTab,
  selectedIncidentId,
  onClearSelectedIncident,
  onOpenInvestigationWorkspace,
}) => {
  const [localIncidentId, setLocalIncidentId] = useState<string | null>(null)
  const [currentDateTime, setCurrentDateTime] = useState("")
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false)
  const [hasRegisteredApp, setHasRegisteredApp] = useState(false)

  const activeIncidentId = selectedIncidentId || localIncidentId
  const activeModalIncident = activeIncidentId
    ? (mockIncidents.find((i) => i.id === activeIncidentId) ?? null)
    : null

  useEffect(() => {
    // Format timestamp like "Tue, 27 Aug 2024 19:42:08" matching reference image
    const updateTime = () => {
      const now = new Date()
      const formatted =
        now.toLocaleDateString("en-GB", {
          weekday: "short",
          day: "numeric",
          month: "short",
          year: "numeric",
        }) +
        " " +
        now.toLocaleTimeString("en-GB", { hour12: false })
      setCurrentDateTime(formatted)
    }

    updateTime()
    const interval = setInterval(updateTime, 1000)
    return () => clearInterval(interval)
  }, [])

  const handleSelectIncident = (id: string) => {
    setLocalIncidentId(id)
  }

  const handleCloseModal = () => {
    setLocalIncidentId(null)
    if (onClearSelectedIncident) onClearSelectedIncident()
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Greeting & Real-time Clock Header matching reference */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-bone tracking-tight">
            Good evening, Afwaan
          </h1>
          <p className="text-xs sm:text-sm text-dust mt-0.5">
            Here&apos;s what&apos;s happening with your systems.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="font-mono text-xs sm:text-sm text-dust font-medium text-right hidden md:block">
            {currentDateTime || "Tue, 27 Aug 2024 19:42:08"}
          </div>
          <Button
            variant="default"
            size="sm"
            onClick={() => {
              setHasRegisteredApp(false)
              setIsConnectModalOpen(true)
            }}
            className="flex items-center gap-1.5 shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Connect Application</span>
          </Button>
        </div>
      </div>

      {/* KPI Cards Row (4 cards) */}
      <ErrorBoundary moduleName="KPI Metrics">
        <KpiGrid
          activeIncidentsCount={mockIncidents.filter((i) => i.status === "INVESTIGATING").length}
          servicesCount={mockServices.length}
          overallUptime={99.8}
          investigations24hCount={12}
          onIncidentKpiClick={() => onNavigateToTab?.("incidents")}
          onServicesKpiClick={() => onNavigateToTab?.("services")}
        />
      </ErrorBoundary>

      {/* Main Dashboard Layout Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): Active Incidents Triage & System Health */}
        <div className="lg:col-span-7 space-y-6 flex flex-col">
          <ErrorBoundary moduleName="Incident Triage Table">
            <IncidentTriageTable
              incidents={mockIncidents}
              onSelectIncident={handleSelectIncident}
              onViewAll={() => onNavigateToTab?.("incidents")}
            />
          </ErrorBoundary>

          <ErrorBoundary moduleName="System Health">
            <SystemHealthCard
              services={mockServices}
              onViewDetails={() => onNavigateToTab?.("services")}
            />
          </ErrorBoundary>
        </div>

        {/* Right Column (5 cols): Service Metrics Chart, Evaluation Results, and Activity Feed */}
        <div className="lg:col-span-5 space-y-6 flex flex-col">
          <ErrorBoundary moduleName="Service Metrics Chart">
            <ServiceMetricsChart />
          </ErrorBoundary>

          <div className="grid grid-cols-1 gap-6">
            <ErrorBoundary moduleName="Evaluation Results">
              <EvaluationSummaryCard onViewAll={() => onNavigateToTab?.("evaluations")} />
            </ErrorBoundary>

            <ErrorBoundary moduleName="Recent Activity Feed">
              <RecentActivityFeed
                activities={mockRecentActivities}
                onSelectIncident={handleSelectIncident}
                onViewAll={() => onNavigateToTab?.("audit-logs")}
              />
            </ErrorBoundary>
          </div>
        </div>
      </div>

      {/* Incident Detail Modal */}
      <IncidentDetailModal
        incident={activeModalIncident}
        onClose={handleCloseModal}
        onNavigateToIncidentsTab={() => onNavigateToTab?.("incidents")}
        onOpenWorkspace={onOpenInvestigationWorkspace}
      />

      {/* Connect Application Modal */}
      <ConnectApplicationModal
        isOpen={isConnectModalOpen}
        onClose={() => {
          setIsConnectModalOpen(false)
          if (hasRegisteredApp && onNavigateToTab) {
            setHasRegisteredApp(false)
            onNavigateToTab("services")
          }
        }}
        onSuccess={() => {
          setHasRegisteredApp(true)
        }}
      />
    </div>
  )
}
