import React from "react"
import { InvestigationHeader } from "./InvestigationHeader"
import { InvestigationProgress } from "./InvestigationProgress"
import { HypothesesList } from "./HypothesesList"
import { EvidenceSummaryCards } from "./EvidenceSummaryCards"
import { EvidenceDetailView } from "./EvidenceDetailView"
import { KnowledgeSourcesUsed } from "./KnowledgeSourcesUsed"
import { LogsView } from "./LogsView"
import { MetricsView } from "./MetricsView"
import { TracesView } from "./TracesView"
import { LiveActivityStream } from "./LiveActivityStream"
import { RemediationDock } from "./RemediationDock"
import { ConfigDiffModal } from "./ConfigDiffModal"
import { Card } from "../common/Card"
import { ErrorBoundary } from "../common/ErrorBoundary"
import { useInvestigation } from "../../hooks/useInvestigation"
import { useToast } from "../../hooks/useToast"
import type { InvestigationTab } from "../../types"

interface InvestigationWorkspaceProps {
  incidentId?: string
  onBackToOverview: () => void
}

export const InvestigationWorkspace: React.FC<InvestigationWorkspaceProps> = ({
  incidentId,
  onBackToOverview,
}) => {
  const { success: toastSuccess, error: toastError } = useToast()

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
    isSubmitting,
    submitError,
    auditLog,
    isDiffModalOpen,
    setIsDiffModalOpen,
    resetSimulation,
    completeSimulation,
    togglePlaySimulation,
  } = useInvestigation(incidentId)

  const handleApprove = async (reason?: string) => {
    try {
      await approveRemediation(reason)
      toastSuccess("Remediation proposal approved and audit record persisted.")
    } catch (err: any) {
      toastError(err?.message || "Failed to approve remediation proposal.")
    }
  }

  const handleReject = async (reason?: string) => {
    try {
      await rejectRemediation(reason)
      toastSuccess("Remediation proposal rejected and audit record persisted.")
    } catch (err: any) {
      toastError(err?.message || "Failed to reject remediation proposal.")
    }
  }

  const tabs: { key: InvestigationTab; label: string }[] = [
    { key: "hypotheses", label: "Hypotheses" },
    { key: "evidence", label: "Evidence" },
    { key: "logs", label: "Logs" },
    { key: "metrics", label: "Metrics" },
    { key: "traces", label: "Traces" },
    { key: "agent-activity", label: "Activity" },
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
        {/* Left Column (4 cols on lg, 3 cols on xl): Investigation Stepper */}
        <div className="lg:col-span-4 xl:col-span-3 flex flex-col">
          <ErrorBoundary moduleName="Investigation Timeline">
            <InvestigationProgress steps={visibleSteps} currentStepIndex={stepIndex} />
          </ErrorBoundary>
        </div>

        {/* Center Column (8 cols on lg, 6 cols on xl): Tabs & Main Investigation Panels */}
        <div className="lg:col-span-8 xl:col-span-6 flex flex-col space-y-4 min-w-0">
          <Card className="flex flex-col flex-1 p-4 sm:p-5">
            {/* Tabs Header */}
            <div className="flex items-center gap-1 sm:gap-1.5 p-1 bg-ink/70 border border-ash/70 rounded-md overflow-x-auto mb-4 scrollbar-none">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.key

                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`shrink-0 px-2.5 sm:px-3 py-1 rounded text-xs font-medium whitespace-nowrap transition-colors select-none ${
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

                  {/* Section: Knowledge Sources Used */}
                  <ErrorBoundary moduleName="Knowledge Sources Used">
                    <KnowledgeSourcesUsed
                      sources={data.retrievedSources}
                      retrievalStatus={data.retrievalStatus}
                      incidentService={data.service}
                    />
                  </ErrorBoundary>

                  <ErrorBoundary moduleName="Evidence Summary">
                    <EvidenceSummaryCards onViewAllEvidence={() => setActiveTab("evidence")} />
                  </ErrorBoundary>
                </div>
              )}

              {activeTab === "evidence" && (
                <div className="space-y-5">
                  <ErrorBoundary moduleName="Evidence Detail">
                    <EvidenceDetailView
                      evidence={visibleEvidence}
                      expandedIds={expandedEvidenceIds}
                      onToggleExpand={toggleEvidenceExpanded}
                    />
                  </ErrorBoundary>

                  <ErrorBoundary moduleName="Knowledge Sources Used">
                    <KnowledgeSourcesUsed
                      sources={data.retrievedSources}
                      retrievalStatus={data.retrievalStatus}
                      incidentService={data.service}
                    />
                  </ErrorBoundary>
                </div>
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

        {/* Right Column (12 cols on lg, 3 cols on xl): Live Agent Activity Stream */}
        <div className="lg:col-span-12 xl:col-span-3 flex flex-col space-y-4 min-w-0">
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
          isSubmitting={isSubmitting}
          submitError={submitError}
          auditLog={auditLog}
          onApprove={handleApprove}
          onReject={handleReject}
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
