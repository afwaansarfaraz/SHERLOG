import { useState, useEffect, useCallback } from "react"
import {
  mockInvestigationDataINC00241,
  mockInvestigationSteps,
  mockHypotheses,
  mockEvidenceItems,
} from "../mocks"
import { api } from "../lib/api"
import type {
  InvestigationTab,
  InvestigationStep,
  Hypothesis,
  EvidenceItem,
  RemediationApprovalStatus,
  IncidentInvestigationData,
  HypothesisLikelihood,
  EvidenceType,
  EvidencePolarity,
  RemediationProposal,
  AuditLogEntry,
} from "../types"

export function useInvestigation(targetIncidentId?: string) {
  const [data, setData] = useState<IncidentInvestigationData>(mockInvestigationDataINC00241)
  const [activeTab, setActiveTab] = useState<InvestigationTab>("hypotheses")
  const [stepIndex, setStepIndex] = useState<number>(mockInvestigationSteps.length) // Default fully completed view
  const [isPlaying, setIsPlaying] = useState<boolean>(false)
  const [approvalStatus, setApprovalStatus] =
    useState<RemediationApprovalStatus>("AWAITING_APPROVAL")
  const [isDiffModalOpen, setIsDiffModalOpen] = useState<boolean>(false)
  const [expandedEvidenceIds, setExpandedEvidenceIds] = useState<Set<string>>(
    new Set(["ev-1", "ev-2"])
  )
  const [selectedHypothesisId, setSelectedHypothesisId] = useState<string>("h1")
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([])
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // Load real investigation data when an incidentId is specified
  useEffect(() => {
    let isMounted = true

    async function fetchIncidentInvestigation() {
      // If no ID is specified, use default demo mock
      if (!targetIncidentId) {
        setData(mockInvestigationDataINC00241)
        setApprovalStatus(mockInvestigationDataINC00241.remediation.status)
        return
      }

      try {
        let res: any
        try {
          res = await api.get(`/api/v1/investigations/${targetIncidentId}`)
        } catch (fetchErr: any) {
          if (
            fetchErr?.status === 404 &&
            targetIncidentId !== "INC00241" &&
            targetIncidentId !== "INC-00241"
          ) {
            // Trigger investigation on demand if not already run
            res = await api.post("/api/v1/investigations/trigger", {
              incident_id: targetIncidentId,
              force: false,
            })
          } else if (
            targetIncidentId === "INC00241" ||
            targetIncidentId === "INC-00241"
          ) {
            // Demo fallback for mock incident
            setData(mockInvestigationDataINC00241)
            setApprovalStatus(mockInvestigationDataINC00241.remediation.status)
            return
          } else {
            throw fetchErr
          }
        }

        if (!isMounted || !res) return

        const mappedHypotheses: Hypothesis[] = (res.hypotheses || []).map(
          (h: any, idx: number) => ({
            id: h.id || `h${idx + 1}`,
            rank: h.rank || idx + 1,
            title: h.title || h.root_cause || "Hypothesis",
            description: h.causal_explanation || "",
            score: Math.round(h.score || 50),
            likelihood: (h.likelihood || "POSSIBLE") as HypothesisLikelihood,
            supportingEvidenceCount: (h.supporting_evidence || []).length,
            contradictingEvidenceCount: (h.contradicting_evidence || []).length,
            verified: idx === 0,
            verificationReason: h.causal_explanation,
          })
        )

        const mappedEvidence: EvidenceItem[] = (res.evidence || []).map(
          (e: any, idx: number) => ({
            id: e.id || `ev-${idx + 1}`,
            hypothesisId: "h1",
            type: (e.type || "metric") as EvidenceType,
            title: e.title || "Evidence Item",
            polarity: (e.polarity || "supporting") as EvidencePolarity,
            source: e.source || "investigation-pipeline",
            timestamp: e.timestamp || new Date().toISOString(),
            summary: e.summary || e.title,
            weight: 1,
          })
        )

        // Map remediation proposal from real backend response
        let updatedRemediation: RemediationProposal =
          mockInvestigationDataINC00241.remediation
        if (res.remediation) {
          updatedRemediation = {
            id: res.remediation.id || `REM-${targetIncidentId}`,
            incidentId: res.remediation.incident_id || targetIncidentId,
            rootCauseTitle:
              res.remediation.root_cause_title || res.root_cause || "Service Degradation",
            rootCauseDescription:
              res.remediation.root_cause_description || res.summary || "",
            actionTitle: res.remediation.action_title || "Remediate Incident",
            actionDescription: res.remediation.action_description || "",
            targetService: res.remediation.target_service || "orders",
            allowlistedAction: res.remediation.action_title || "remediation",
            configDiff: mockInvestigationDataINC00241.remediation.configDiff,
            status:
              (res.remediation.status as RemediationApprovalStatus) ||
              "AWAITING_APPROVAL",
            approvedBy: res.remediation.approved_by,
            approvedAt: res.remediation.approved_at,
            rejectionReason: res.remediation.rejection_reason,
          }
          setApprovalStatus(updatedRemediation.status)
        }

        setData((prev) => ({
          ...prev,
          incidentId: res.incident_id || targetIncidentId,
          title: res.summary ? res.summary.slice(0, 80) : prev.title,
          summary: res.summary || prev.summary,
          status: res.status === "COMPLETED" ? "RESOLVED" : "INVESTIGATING",
          hypotheses:
            mappedHypotheses.length > 0 ? mappedHypotheses : prev.hypotheses,
          evidence: mappedEvidence.length > 0 ? mappedEvidence : prev.evidence,
          remediation: updatedRemediation,
          retrievedSources: res.retrieved_sources || [],
          retrievalStatus:
            res.retrieval_status ||
            (res.retrieved_sources?.length ? "SUCCESS" : "NO_DOCUMENTS_FOUND"),
        }))

        // Fetch persisted audit trail for this incident
        try {
          const auditEntries = await api.get<AuditLogEntry[]>(
            `/api/v1/investigations/audit/log?incident_id=${targetIncidentId}`
          )
          if (isMounted && Array.isArray(auditEntries)) {
            setAuditLog(auditEntries)
          }
        } catch {
          // ignore audit log fetch failure on initial load
        }
      } catch (err) {
        console.warn(
          "Could not load investigation from API for incident",
          targetIncidentId,
          err
        )
      }
    }

    fetchIncidentInvestigation()

    return () => {
      isMounted = false
    }
  }, [targetIncidentId])

  // Visible steps based on simulation progress
  const visibleSteps: InvestigationStep[] = (
    data.steps || mockInvestigationSteps
  ).slice(0, stepIndex)

  // Visible evidence based on simulation progress
  const activeEvidenceList =
    data.evidence && data.evidence.length > 0
      ? data.evidence
      : mockEvidenceItems
  const visibleEvidence: EvidenceItem[] = activeEvidenceList.filter((_, idx) => {
    if (stepIndex <= 1) return false
    if (stepIndex === 2) return idx <= 1 // metrics
    if (stepIndex === 3) return idx <= 2 // logs
    if (stepIndex === 4) return idx <= 6 // deploys & all
    return true
  })

  // Dynamic hypotheses score progression based on step index
  const activeHypotheses =
    data.hypotheses && data.hypotheses.length > 0
      ? data.hypotheses
      : mockHypotheses
  const dynamicHypotheses: Hypothesis[] = activeHypotheses.map((hyp) => {
    if (stepIndex <= 1) {
      return { ...hyp, score: 25, likelihood: "POSSIBLE", verified: false }
    }
    if (stepIndex === 2) {
      if (hyp.id === "h1")
        return { ...hyp, score: 55, likelihood: "POSSIBLE", verified: false }
      if (hyp.id === "h2")
        return { ...hyp, score: 35, likelihood: "POSSIBLE", verified: false }
      return { ...hyp, score: 20, likelihood: "LESS_LIKELY", verified: false }
    }
    if (stepIndex === 3) {
      if (hyp.id === "h1")
        return { ...hyp, score: 72, likelihood: "LIKELY", verified: false }
      if (hyp.id === "h2")
        return { ...hyp, score: 38, likelihood: "POSSIBLE", verified: false }
      return { ...hyp, score: 18, likelihood: "LESS_LIKELY", verified: false }
    }
    return hyp
  })

  // Simulation timer
  useEffect(() => {
    let timer: NodeJS.Timeout
    if (isPlaying) {
      timer = setInterval(() => {
        setStepIndex((prev) => {
          if (prev >= mockInvestigationSteps.length) {
            setIsPlaying(false)
            return mockInvestigationSteps.length
          }
          return prev + 1
        })
      }, 1800)
    }
    return () => clearInterval(timer)
  }, [isPlaying])

  const toggleEvidenceExpanded = useCallback((id: string) => {
    setExpandedEvidenceIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const stepForward = useCallback(() => {
    setStepIndex((prev) => Math.min(prev + 1, mockInvestigationSteps.length))
  }, [])

  const resetSimulation = useCallback(() => {
    setIsPlaying(false)
    setStepIndex(1)
  }, [])

  const completeSimulation = useCallback(() => {
    setIsPlaying(false)
    setStepIndex(mockInvestigationSteps.length)
  }, [])

  const togglePlaySimulation = useCallback(() => {
    if (stepIndex >= mockInvestigationSteps.length) {
      setStepIndex(1)
      setIsPlaying(true)
    } else {
      setIsPlaying((prev) => !prev)
    }
  }, [stepIndex])

  const approveRemediation = useCallback(
    async (reason?: string): Promise<boolean> => {
      const incId = data.incidentId || targetIncidentId
      if (!incId || isSubmitting) return false
      setIsSubmitting(true)
      setSubmitError(null)
      try {
        const res = await api.post<{
          status: RemediationApprovalStatus
          approved_by?: string
          approved_at?: string
          rejection_reason?: string
        }>(`/api/v1/investigations/${incId}/approve`, {
          action: "approve",
          approved_by: "Afwaan",
          reason: reason || undefined,
        })

        const newStatus = res.status || "APPROVED"
        setApprovalStatus(newStatus)
        setData((prev) => ({
          ...prev,
          remediation: {
            ...prev.remediation,
            status: newStatus,
            approvedBy: res.approved_by || "Afwaan",
            approvedAt: res.approved_at || new Date().toISOString(),
            rejectionReason: undefined,
          },
        }))

        // Refresh persistent audit trail
        try {
          const updatedAudit = await api.get<AuditLogEntry[]>(
            `/api/v1/investigations/audit/log?incident_id=${incId}`
          )
          if (Array.isArray(updatedAudit)) {
            setAuditLog(updatedAudit)
          }
        } catch {
          // ignore secondary fetch failure
        }

        return true
      } catch (err: any) {
        const msg = err?.message || "Failed to approve remediation proposal"
        setSubmitError(msg)
        throw err
      } finally {
        setIsSubmitting(false)
      }
    },
    [data.incidentId, targetIncidentId, isSubmitting]
  )

  const rejectRemediation = useCallback(
    async (reason?: string): Promise<boolean> => {
      const incId = data.incidentId || targetIncidentId
      if (!incId || isSubmitting) return false
      setIsSubmitting(true)
      setSubmitError(null)
      try {
        const res = await api.post<{
          status: RemediationApprovalStatus
          approved_by?: string
          approved_at?: string
          rejection_reason?: string
        }>(`/api/v1/investigations/${incId}/approve`, {
          action: "reject",
          approved_by: "Afwaan",
          reason: reason || "Rejected by operator",
        })

        const newStatus = res.status || "REJECTED"
        setApprovalStatus(newStatus)
        setData((prev) => ({
          ...prev,
          remediation: {
            ...prev.remediation,
            status: newStatus,
            approvedBy: res.approved_by || "Afwaan",
            rejectionReason:
              res.rejection_reason || reason || "Rejected by operator",
          },
        }))

        // Refresh persistent audit trail
        try {
          const updatedAudit = await api.get<AuditLogEntry[]>(
            `/api/v1/investigations/audit/log?incident_id=${incId}`
          )
          if (Array.isArray(updatedAudit)) {
            setAuditLog(updatedAudit)
          }
        } catch {
          // ignore secondary fetch failure
        }

        return true
      } catch (err: any) {
        const msg = err?.message || "Failed to reject remediation proposal"
        setSubmitError(msg)
        throw err
      } finally {
        setIsSubmitting(false)
      }
    },
    [data.incidentId, targetIncidentId, isSubmitting]
  )

  return {
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
    stepForward,
    resetSimulation,
    completeSimulation,
    togglePlaySimulation,
  }
}
