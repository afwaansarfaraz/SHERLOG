import { useState } from "react"
import { Shell } from "./components/shell/Shell"
import { OverviewDashboard } from "./components/overview/OverviewDashboard"
import { GenericTabView } from "./components/views/GenericTabViews"
import { InvestigationWorkspace } from "./components/investigation/InvestigationWorkspace"
import { ErrorBoundary } from "./components/common/ErrorBoundary"
import type { NavItemKey } from "./components/shell/Sidebar"

export function App() {
  const [activeTab, setActiveTab] = useState<NavItemKey>("overview")
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null)
  const [activeIncidentWorkspace, setActiveIncidentWorkspace] = useState<string | null>(null)

  const handleSelectIncident = (id: string) => {
    setSelectedIncidentId(id)
  }

  const handleOpenWorkspace = (id: string) => {
    setSelectedIncidentId(null)
    setActiveIncidentWorkspace(id)
  }

  const handleNavigateToTab = (tab: string) => {
    setActiveIncidentWorkspace(null)
    setActiveTab(tab as NavItemKey)
  }

  return (
    <ErrorBoundary moduleName="Sherlog Root Application">
      <Shell
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setActiveIncidentWorkspace(null)
          setActiveTab(tab)
        }}
        onSelectIncident={handleSelectIncident}
      >
        {activeIncidentWorkspace ? (
          <InvestigationWorkspace onBackToOverview={() => setActiveIncidentWorkspace(null)} />
        ) : activeTab === "overview" ? (
          <OverviewDashboard
            onNavigateToTab={handleNavigateToTab}
            selectedIncidentId={selectedIncidentId}
            onClearSelectedIncident={() => setSelectedIncidentId(null)}
            onOpenInvestigationWorkspace={handleOpenWorkspace}
          />
        ) : (
          <GenericTabView
            tab={activeTab}
            onBackToOverview={() => {
              setActiveIncidentWorkspace(null)
              setActiveTab("overview")
            }}
            onSelectIncident={handleOpenWorkspace}
          />
        )}
      </Shell>
    </ErrorBoundary>
  )
}

export default App
