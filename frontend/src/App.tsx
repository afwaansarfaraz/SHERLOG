import { useState } from "react"
import { Shell } from "./components/shell/Shell"
import { OverviewDashboard } from "./components/overview/OverviewDashboard"
import { GenericTabView } from "./components/views/GenericTabViews"
import { ErrorBoundary } from "./components/common/ErrorBoundary"
import type { NavItemKey } from "./components/shell/Sidebar"

export function App() {
  const [activeTab, setActiveTab] = useState<NavItemKey>("overview")
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null)

  const handleSelectIncident = (id: string) => {
    setSelectedIncidentId(id)
  }

  const handleNavigateToTab = (tab: string) => {
    setActiveTab(tab as NavItemKey)
  }

  return (
    <ErrorBoundary moduleName="Sherlog Root Application">
      <Shell
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onSelectIncident={handleSelectIncident}
      >
        {activeTab === "overview" ? (
          <OverviewDashboard
            onNavigateToTab={handleNavigateToTab}
            selectedIncidentId={selectedIncidentId}
            onClearSelectedIncident={() => setSelectedIncidentId(null)}
          />
        ) : (
          <GenericTabView
            tab={activeTab}
            onBackToOverview={() => setActiveTab("overview")}
            onSelectIncident={handleSelectIncident}
          />
        )}
      </Shell>
    </ErrorBoundary>
  )
}

export default App
