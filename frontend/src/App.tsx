import { useState, useEffect, useCallback } from "react"
import { Shell } from "./components/shell/Shell"
import { OverviewDashboard } from "./components/overview/OverviewDashboard"
import { GenericTabView } from "./components/views/GenericTabViews"
import { InvestigationWorkspace } from "./components/investigation/InvestigationWorkspace"
import { ErrorBoundary } from "./components/common/ErrorBoundary"
import { ToastProvider } from "./hooks/useToast"
import { ToastContainer } from "./components/common/Toast"
import { NetworkBanner } from "./components/common/NetworkBanner"
import { NotFoundPage } from "./components/errors/NotFoundPage"
import { InternalErrorPage } from "./components/errors/InternalErrorPage"
import { AccessDeniedPage } from "./components/errors/AccessDeniedPage"
import { ServiceUnavailablePage } from "./components/errors/ServiceUnavailablePage"
import { HardeningShowcase } from "./components/views/HardeningShowcase"
import type { NavItemKey } from "./components/shell/Sidebar"

const VALID_TABS: NavItemKey[] = [
  "overview",
  "incidents",
  "services",
  "knowledge",
  "evaluations",
  "audit-logs",
  "settings",
]

type RouteState =
  | { type: "tab"; tab: NavItemKey }
  | { type: "workspace"; incidentId: string }
  | { type: "preview" }
  | { type: "404"; path: string }
  | { type: "500"; message?: string }
  | { type: "403"; resource?: string }
  | { type: "503"; isMaintenance: boolean }

export function App() {
  const [routeState, setRouteState] = useState<RouteState>(() => parseHash(window.location.hash))
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null)

  // Parse location hash deterministically
  function parseHash(hash: string): RouteState {
    const cleanHash = hash.replace(/^#\/?/, "").trim()

    if (!cleanHash || cleanHash === "overview") {
      return { type: "tab", tab: "overview" }
    }

    if (VALID_TABS.includes(cleanHash as NavItemKey)) {
      return { type: "tab", tab: cleanHash as NavItemKey }
    }

    if (cleanHash.startsWith("workspace")) {
      const parts = cleanHash.split(":")
      const id = parts[1] || "INC00241"
      return { type: "workspace", incidentId: id }
    }

    // Developer-only showcase route (accessible via #dev/hardening or #preview in dev mode only)
    if (
      cleanHash === "dev/hardening" ||
      cleanHash === "dev" ||
      cleanHash === "preview" ||
      cleanHash === "showcase"
    ) {
      if (import.meta.env.DEV) {
        return { type: "preview" }
      }
      // In production builds, developer routes are strictly inaccessible and trigger 404
      return { type: "404", path: hash }
    }

    // Direct error test / preview routes
    if (cleanHash === "404" || cleanHash === "not-found") {
      return { type: "404", path: hash }
    }

    if (cleanHash === "500" || cleanHash === "internal-error") {
      return { type: "500", message: "Simulated internal server error in telemetry processor." }
    }

    if (cleanHash === "403" || cleanHash === "forbidden" || cleanHash === "access-denied") {
      return { type: "403", resource: "Remediation Auto-Approval Engine" }
    }

    if (cleanHash === "503" || cleanHash === "maintenance") {
      return { type: "503", isMaintenance: cleanHash === "maintenance" }
    }

    // Unknown hash route triggers 404
    return { type: "404", path: hash }
  }

  // Synchronize hash changes
  useEffect(() => {
    const handleHashChange = () => {
      setRouteState(parseHash(window.location.hash))
    }

    window.addEventListener("hashchange", handleHashChange)
    return () => window.removeEventListener("hashchange", handleHashChange)
  }, [])

  const navigateToTab = useCallback((tab: NavItemKey) => {
    window.location.hash = tab
    setRouteState({ type: "tab", tab })
  }, [])

  const navigateToWorkspace = useCallback((incidentId: string) => {
    window.location.hash = `workspace:${incidentId}`
    setRouteState({ type: "workspace", incidentId })
  }, [])

  const navigateToOverview = useCallback(() => {
    window.location.hash = "overview"
    setRouteState({ type: "tab", tab: "overview" })
  }, [])

  const handleSelectIncident = (id: string) => {
    setSelectedIncidentId(id)
  }

  const activeTab: NavItemKey = routeState.type === "tab" ? routeState.tab : "overview"

  return (
    <ErrorBoundary isRoot={true} moduleName="Sherlog Root Application">
      <ToastProvider>
        <div className="flex flex-col h-screen w-screen overflow-hidden bg-ink">
          {/* Global Network Resilience Banner */}
          <NetworkBanner />

          {/* Core Shell Layout */}
          <Shell
            activeTab={activeTab}
            onSelectTab={navigateToTab}
            onSelectIncident={handleSelectIncident}
          >
            {routeState.type === "404" ? (
              <NotFoundPage
                attemptedPath={routeState.path}
                onGoToDashboard={navigateToOverview}
                onGoBack={() => {
                  if (window.history.length > 1) {
                    window.history.back()
                  } else {
                    navigateToOverview()
                  }
                }}
              />
            ) : routeState.type === "500" ? (
              <InternalErrorPage
                message={routeState.message}
                onGoToDashboard={navigateToOverview}
                onReload={() => window.location.reload()}
              />
            ) : routeState.type === "403" ? (
              <AccessDeniedPage
                resourceName={routeState.resource}
                onGoToDashboard={navigateToOverview}
                onGoBack={() => {
                  if (window.history.length > 1) {
                    window.history.back()
                  } else {
                    navigateToOverview()
                  }
                }}
              />
            ) : routeState.type === "503" ? (
              <ServiceUnavailablePage
                isMaintenance={routeState.isMaintenance}
                onGoToDashboard={navigateToOverview}
                onRetry={() => {
                  navigateToOverview()
                }}
              />
            ) : routeState.type === "workspace" ? (
              <InvestigationWorkspace
                incidentId={routeState.incidentId}
                onBackToOverview={navigateToOverview}
              />
            ) : routeState.type === "preview" ? (
              import.meta.env.DEV ? (
                <HardeningShowcase />
              ) : (
                <NotFoundPage
                  attemptedPath="#dev/hardening"
                  onGoToDashboard={navigateToOverview}
                />
              )
            ) : routeState.tab === "overview" ? (
              <OverviewDashboard
                onNavigateToTab={(tab) => navigateToTab(tab as NavItemKey)}
                selectedIncidentId={selectedIncidentId}
                onClearSelectedIncident={() => setSelectedIncidentId(null)}
                onOpenInvestigationWorkspace={navigateToWorkspace}
              />
            ) : (
              <GenericTabView
                tab={routeState.tab}
                onBackToOverview={navigateToOverview}
                onSelectIncident={navigateToWorkspace}
              />
            )}
          </Shell>

          {/* Accessible Global Toast Notifications Container */}
          <ToastContainer />
        </div>
      </ToastProvider>
    </ErrorBoundary>
  )
}

export default App
