import { useState, useEffect, useCallback, useRef } from "react"
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

const inFlightInvestigationTriggers = new Map<string, Promise<any>>()

function isDemoIncident(incidentId?: string) {
  return !incidentId || incidentId === "INC00241" || incidentId === "INC-00241"
}

function emptyInvestigationData(incidentId: string): IncidentInvestigationData {
  const remediation: RemediationProposal = {
    id: "",
    incidentId,
    rootCauseTitle: "",
    rootCauseDescription: "",
    actionTitle: "",
    actionDescription: "",
    targetService: "",
    allowlistedAction: "",
    configDiff: "",
    status: "AWAITING_APPROVAL",
  }
  return {
    incidentId,
    title: "Loading incident investigation…",
    service: "",
    status: "INVESTIGATING",
    openedAt: "",
    summary: "Loading persisted investigation results.",
    steps: [],
    hypotheses: [],
    evidence: [],
    logs: [],
    traces: [],
    remediation,
    retrievedSources: [],
    retrievalStatus: "NOT_ATTEMPTED",
  }
}

function triggerInvestigation(incidentId: string, force = false) {
  const key = `${incidentId}:${force}`
  const existing = inFlightInvestigationTriggers.get(key)
  if (existing) return existing

  const pending = api
    .post("/api/v1/investigations/trigger", {
      incident_id: incidentId,
      force,
    }, {
      // The backend pipeline is bounded at 120 seconds; give it a small transport margin.
      timeoutMs: 130_000,
    })
    .finally(() => {
      inFlightInvestigationTriggers.delete(key)
    })
  inFlightInvestigationTriggers.set(key, pending)
  return pending
}

export function useInvestigation(targetIncidentId?: string) {
  const currentTargetIncidentId = useRef(targetIncidentId)
  currentTargetIncidentId.current = targetIncidentId

  const [data, setData] = useState<IncidentInvestigationData>(() =>
    isDemoIncident(targetIncidentId)
      ? mockInvestigationDataINC00241
      : emptyInvestigationData(targetIncidentId!)
  )
  const [isLoading, setIsLoading] = useState(Boolean(targetIncidentId && !isDemoIncident(targetIncidentId)))
  const [investigationError, setInvestigationError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<InvestigationTab>("hypotheses")
  const [stepIndex, setStepIndex] = useState<number>(
    isDemoIncident(targetIncidentId) ? mockInvestigationSteps.length : 0
  )
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

  const applyInvestigationResponse = useCallback((res: any, incidentId: string) => {
    const mappedHypotheses: Hypothesis[] = (res.hypotheses || []).map(
      (h: any, idx: number) => ({
        id: h.id || `h${idx + 1}`,
        rank: h.rank || idx + 1,
        title: h.title || h.root_cause || "Hypothesis",
        description: h.causal_explanation || "",
        score: Number(h.score ?? 0),
        likelihood: (h.likelihood || "POSSIBLE") as HypothesisLikelihood,
        supportingEvidenceCount: (h.supporting_evidence || []).length,
        contradictingEvidenceCount: (h.contradicting_evidence || []).length,
        verified: Boolean(h.verified),
        verificationReason: h.causal_explanation,
      })
    )

    const mappedEvidence: EvidenceItem[] = (res.evidence || []).map(
      (e: any, idx: number) => ({
        id: e.id || `ev-${idx + 1}`,
        hypothesisId: "h1",
        type: (e.type || "metric") as EvidenceType,
        title: e.title || "Evidence Item",
        polarity: (e.polarity || "neutral") as EvidencePolarity,
        source: e.source || "investigation-pipeline",
        timestamp: e.timestamp || new Date().toISOString(),
        summary: e.summary || e.title,
        rawSnippet: e.raw_snippet,
        weight: e.weight || 0,
      })
    )

    const mappedSteps: InvestigationStep[] = (res.tool_executions || []).map(
      (tool: any, idx: number) => ({
        id: `tool-${idx + 1}`,
        title: `${String(tool.tool || "Telemetry tool").replace(/Tool$/, "")} query`,
        status: tool.status === "ERROR" ? "failed" : "completed",
        timestamp: tool.duration_ms != null ? `${Math.round(tool.duration_ms)} ms` : undefined,
        details: [tool.query, tool.status, tool.error].filter(Boolean).join(" · "),
        toolName: tool.tool,
      })
    )

    const remediation = res.remediation
      ? {
          id: res.remediation.id || `REM-${incidentId}`,
          incidentId: res.remediation.incident_id || incidentId,
          rootCauseTitle: res.remediation.root_cause_title || res.root_cause || "Service Degradation",
          rootCauseDescription: res.remediation.root_cause_description || res.summary || "",
          actionTitle: res.remediation.action_title || "Remediate Incident",
          actionDescription: res.remediation.action_description || "",
          targetService: res.remediation.target_service || res.service || "unknown",
          allowlistedAction: res.remediation.action_title || "remediation",
          configDiff: "",
          status: (res.remediation.status || "AWAITING_APPROVAL") as RemediationApprovalStatus,
          approvedBy: res.remediation.approved_by,
          approvedAt: res.remediation.approved_at,
          rejectionReason: res.remediation.rejection_reason,
        }
      : emptyInvestigationData(incidentId).remediation

    setData({
      incidentId: res.incident_id || incidentId,
      title: res.summary || `Investigation ${incidentId}`,
      service: res.service || "unknown",
      status:
        res.status === "COMPLETED"
          ? "RESOLVED"
          : res.status === "FAILED" || res.status === "INSUFFICIENT_EVIDENCE"
            ? "FAILED"
            : "INVESTIGATING",
      openedAt: res.started_at || "",
      summary: res.summary || "",
      steps: mappedSteps,
      hypotheses: mappedHypotheses,
      evidence: mappedEvidence,
      logs: [],
      traces: [],
      remediation,
      retrievedSources: res.retrieved_sources || [],
      retrievalStatus: res.retrieval_status || "NOT_ATTEMPTED",
    })
    setApprovalStatus(remediation.status)
    setStepIndex(mappedSteps.length)
    setExpandedEvidenceIds(new Set(mappedEvidence.slice(0, 2).map((item) => item.id)))
    setInvestigationError(
      res.is_simulated
        ? "The backend returned a simulated investigation; it is not verified telemetry."
        : res.status === "FAILED"
          ? res.error_message || "The investigation pipeline failed. Retry it after reviewing the pipeline error."
          : res.status === "INSUFFICIENT_EVIDENCE"
            ? res.error_message || "The investigation did not collect enough evidence to support a conclusion."
            : null
    )
  }, [])

  // Load real investigation data when an incidentId is specified
  useEffect(() => {
    let isMounted = true

    async function fetchIncidentInvestigation() {
      // If no ID is specified, use default demo mock
      if (!targetIncidentId) {
        setData(mockInvestigationDataINC00241)
        setApprovalStatus(mockInvestigationDataINC00241.remediation.status)
        setIsLoading(false)
        setInvestigationError(null)
        return
      }

      if (isDemoIncident(targetIncidentId)) {
        setData(mockInvestigationDataINC00241)
        setApprovalStatus(mockInvestigationDataINC00241.remediation.status)
        setStepIndex(mockInvestigationSteps.length)
        setIsLoading(false)
        setInvestigationError(null)
        return
      }

      setData(emptyInvestigationData(targetIncidentId))
      setApprovalStatus("AWAITING_APPROVAL")
      setStepIndex(0)
      setIsLoading(true)
      setInvestigationError(null)
      setAuditLog([])

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
            res = await triggerInvestigation(targetIncidentId)
          } else {
            throw fetchErr
          }
        }

        if (!isMounted || !res) return
        applyInvestigationResponse(res, targetIncidentId)

        // Audit history is secondary; it must not hold the actual evidence view in loading state.
        void api.get<AuditLogEntry[]>(
          `/api/v1/investigations/audit/log?incident_id=${targetIncidentId}`
        ).then((auditEntries) => {
          if (isMounted && Array.isArray(auditEntries)) setAuditLog(auditEntries)
        }).catch(() => undefined)
      } catch (err) {
        if (isMounted) {
          setInvestigationError(err instanceof Error ? err.message : "Unable to load this investigation.")
        }
        console.warn(
          "Could not load investigation from API for incident",
          targetIncidentId,
          err
        )
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }

    fetchIncidentInvestigation()

    return () => {
      isMounted = false
    }
  }, [targetIncidentId, applyInvestigationResponse])

  const retryInvestigation = useCallback(async () => {
    const incidentId = targetIncidentId
    if (
      !incidentId ||
      isDemoIncident(incidentId) ||
      currentTargetIncidentId.current !== incidentId
    ) return
    const force = data.status !== "INVESTIGATING"
    setIsLoading(true)
    setInvestigationError(null)
    try {
      const res = await triggerInvestigation(incidentId, force)
      if (currentTargetIncidentId.current !== incidentId) return
      applyInvestigationResponse(res, incidentId)
    } catch (err) {
      if (currentTargetIncidentId.current === incidentId) {
        setInvestigationError(err instanceof Error ? err.message : "Unable to retry this investigation.")
      }
    } finally {
      if (currentTargetIncidentId.current === incidentId) setIsLoading(false)
    }
  }, [targetIncidentId, data.status, applyInvestigationResponse])

  // Visible steps based on simulation progress
  const demoWorkspace = isDemoIncident(targetIncidentId)
  const visibleSteps: InvestigationStep[] = (
    demoWorkspace ? (data.steps.length ? data.steps : mockInvestigationSteps) : data.steps
  ).slice(0, stepIndex)

  // Visible evidence based on simulation progress
  const activeEvidenceList = demoWorkspace
    ? (data.evidence.length > 0 ? data.evidence : mockEvidenceItems)
    : data.evidence
  const visibleEvidence: EvidenceItem[] = demoWorkspace
    ? activeEvidenceList.filter((_, idx) => {
        if (stepIndex <= 1) return false
        if (stepIndex === 2) return idx <= 1 // metrics
        if (stepIndex === 3) return idx <= 2 // logs
        if (stepIndex === 4) return idx <= 6 // deploys & all
        return true
      })
    : activeEvidenceList

  // Dynamic hypotheses score progression based on step index
  const activeHypotheses = demoWorkspace
    ? (data.hypotheses.length > 0 ? data.hypotheses : mockHypotheses)
    : data.hypotheses
  const dynamicHypotheses: Hypothesis[] = demoWorkspace ? activeHypotheses.map((hyp) => {
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
  }) : activeHypotheses

  // Simulation timer
  useEffect(() => {
    let timer: NodeJS.Timeout
    if (isPlaying && isDemoIncident(targetIncidentId)) {
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
  }, [isPlaying, targetIncidentId])

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
    isLoading,
    investigationError,
    retryInvestigation,
    demoWorkspace,
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
