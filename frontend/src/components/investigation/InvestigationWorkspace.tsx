import React from "react"
import { InvestigationHeader } from "./InvestigationHeader"
import { InvestigationProgress } from "./InvestigationProgress"
import { HypothesesList } from "./HypothesesList"
import { EvidenceSummaryCards } from "./EvidenceSummaryCards"
import { EvidenceDetailView } from "./EvidenceDetailView"
import { LogsView } from "./LogsView"
import { MetricsView } from "./MetricsView"
import { TracesView } from "./TracesView"
import { LiveActivityStream } from "./LiveActivityStream"
import { RemediationDock } from "./RemediationDock"
import { ConfigDiffModal } from "./ConfigDiffModal"
import { Card } from "../common/Card"
import { ErrorBoundary } from "../common/ErrorBoundary"
import { useInvestigation } from "../../hooks/useInvestigation"
import type { InvestigationTab } from "../../types"

interface InvestigationWorkspaceProps {
  onBackToOverview: () => void
}

export const InvestigationWorkspace: React.FC<InvestigationWorkspaceProps> = ({
  onBackToOverview,
}) => {
  const {
    data,
    activeTab,
    setActiveTab,
    stepIndex,
    isPlaying,
    visibleSteps,
    dynamicHypotheses,
    visibleEvidence,
    selectedHypothesisId,
    setSelectedHypothesisId,
    expandedEvidenceIds,
    toggleEvidenceExpanded,
    approvalStatus,
    approveRemediation,
    rejectRemediation,
    isDiffModalOpen,
    setIsDiffModalOpen,
    resetSimulation,
    completeSimulation,
    togglePlaySimulation,
  } = useInvestigation()

  const tabs: { key: InvestigationTab; label: string }[] = [
    { key: "hypotheses", label: "Hypotheses" },
    { key: "evidence", label: "Evidence" },
    { key: "logs", label: "Logs" },
    { key: "metrics", label: "Metrics" },
    { key: "traces", label: "Traces" },
    { key: "agent-activity", label: "Agent Activity" },
  ]

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Header with Breadcrumb and Meta */}
      <ErrorBoundary moduleName="Investigation Header">
        <InvestigationHeader
          incidentId={data.incidentId}
          title={data.title}
          service={data.service}
          subtitle={data.summary}
          openedAt={data.openedAt}
          status={data.status}
          isPlaying={isPlaying}
          currentStep={stepIndex}
          totalSteps={data.steps.length}
          onBack={onBackToOverview}
          onTogglePlay={togglePlaySimulation}
          onReset={resetSimulation}
          onComplete={completeSimulation}
        />
      </ErrorBoundary>

      {/* 2. Main Investigation Canvas (3 Columns matching reference layout) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column (3 cols): Investigation Stepper */}
        <div className="lg:col-span-3 flex flex-col">
          <ErrorBoundary moduleName="Investigation Timeline">
            <InvestigationProgress steps={visibleSteps} currentStepIndex={stepIndex} />
          </ErrorBoundary>
        </div>

        {/* Center Column (5 or 6 cols): Tabs & Main Investigation Panels */}
        <div className="lg:col-span-5 flex flex-col space-y-4">
          <Card className="flex flex-col flex-1 p-4 sm:p-5">
            {/* Tabs Header */}
            <div className="flex items-center gap-1.5 p-1 bg-ink/70 border border-ash/70 rounded-md overflow-x-auto mb-4 scrollbar-none">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.key

                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`px-3 py-1 rounded text-xs font-medium whitespace-nowrap transition-colors select-none ${
                      isActive
                        ? "bg-soot text-bone border border-ash/80 shadow-sm"
                        : "text-dust hover:text-bone border border-transparent"
                    }`}
                  >
                    {tab.label}
                  </button>
                )
              })}
            </div>

            {/* Active Tab View */}
            <div className="flex-1">
              {activeTab === "hypotheses" && (
                <div className="space-y-5">
                  <ErrorBoundary moduleName="Hypotheses Ranking">
                    <HypothesesList
                      hypotheses={dynamicHypotheses}
                      selectedHypothesisId={selectedHypothesisId}
                      onSelectHypothesis={setSelectedHypothesisId}
                    />
                  </ErrorBoundary>

                  <ErrorBoundary moduleName="Evidence Summary">
                    <EvidenceSummaryCards onViewAllEvidence={() => setActiveTab("evidence")} />
                  </ErrorBoundary>
                </div>
              )}

              {activeTab === "evidence" && (
                <ErrorBoundary moduleName="Evidence Detail">
                  <EvidenceDetailView
                    evidence={visibleEvidence}
                    expandedIds={expandedEvidenceIds}
                    onToggleExpand={toggleEvidenceExpanded}
                  />
                </ErrorBoundary>
              )}

              {activeTab === "logs" && (
                <ErrorBoundary moduleName="Logs Viewer">
                  <LogsView logs={data.logs} />
                </ErrorBoundary>
              )}

              {activeTab === "metrics" && (
                <ErrorBoundary moduleName="Metrics Telemetry">
                  <MetricsView />
                </ErrorBoundary>
              )}

              {activeTab === "traces" && (
                <ErrorBoundary moduleName="Trace Waterfall">
                  <TracesView traces={data.traces} />
                </ErrorBoundary>
              )}

              {activeTab === "agent-activity" && (
                <ErrorBoundary moduleName="Agent Tool Activity">
                  <LiveActivityStream />
                </ErrorBoundary>
              )}
            </div>
          </Card>
        </div>

        {/* Right Column (4 cols): Live Agent Activity Stream matching reference image */}
        <div className="lg:col-span-4 flex flex-col space-y-4">
          <ErrorBoundary moduleName="Live Activity Feed">
            <LiveActivityStream />
          </ErrorBoundary>
        </div>
      </div>

      {/* 3. Bottom Dock: Proposed Root Cause & Remediation Approval */}
      <ErrorBoundary moduleName="Remediation Approval Dock">
        <RemediationDock
          remediation={data.remediation}
          approvalStatus={approvalStatus}
          onApprove={approveRemediation}
          onReject={rejectRemediation}
          onOpenDiff={() => setIsDiffModalOpen(true)}
        />
      </ErrorBoundary>

      {/* 4. Configuration Diff Modal */}
      <ConfigDiffModal
        isOpen={isDiffModalOpen}
        onClose={() => setIsDiffModalOpen(false)}
        diff={data.remediation.configDiff}
        serviceName={data.service}
      />
    </div>
  )
}
