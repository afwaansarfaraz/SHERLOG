import { useState, useEffect, useCallback } from "react"
import {
  mockInvestigationDataINC00241,
  mockInvestigationSteps,
  mockHypotheses,
  mockEvidenceItems,
} from "../mocks"
import type {
  InvestigationTab,
  InvestigationStep,
  Hypothesis,
  EvidenceItem,
  RemediationApprovalStatus,
} from "../types"

export function useInvestigation() {
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

  // Visible steps based on simulation progress
  const visibleSteps: InvestigationStep[] = mockInvestigationSteps.slice(0, stepIndex)

  // Visible evidence based on simulation progress
  const visibleEvidence: EvidenceItem[] = mockEvidenceItems.filter((_, idx) => {
    if (stepIndex <= 1) return false
    if (stepIndex === 2) return idx <= 1 // metrics
    if (stepIndex === 3) return idx <= 2 // logs
    if (stepIndex === 4) return idx <= 6 // deploys & all
    return true
  })

  // Dynamic hypotheses score progression based on step index
  const dynamicHypotheses: Hypothesis[] = mockHypotheses.map((hyp) => {
    if (stepIndex <= 1) {
      return { ...hyp, score: 25, likelihood: "POSSIBLE", verified: false }
    }
    if (stepIndex === 2) {
      if (hyp.id === "h1") return { ...hyp, score: 55, likelihood: "POSSIBLE", verified: false }
      if (hyp.id === "h2") return { ...hyp, score: 35, likelihood: "POSSIBLE", verified: false }
      return { ...hyp, score: 20, likelihood: "LESS_LIKELY", verified: false }
    }
    if (stepIndex === 3) {
      if (hyp.id === "h1") return { ...hyp, score: 72, likelihood: "LIKELY", verified: false }
      if (hyp.id === "h2") return { ...hyp, score: 38, likelihood: "POSSIBLE", verified: false }
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

  const approveRemediation = useCallback(() => {
    setApprovalStatus("APPROVED")
  }, [])

  const rejectRemediation = useCallback(() => {
    setApprovalStatus("REJECTED")
  }, [])

  return {
    data: mockInvestigationDataINC00241,
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
    stepForward,
    resetSimulation,
    completeSimulation,
    togglePlaySimulation,
  }
}
