export type StepStatus = "completed" | "in_progress" | "pending" | "failed"

export interface InvestigationStep {
  id: string
  title: string
  timestamp?: string
  status: StepStatus
  details?: string
  toolName?: string
}

export type HypothesisLikelihood = "LIKELY" | "POSSIBLE" | "LESS_LIKELY"

export interface Hypothesis {
  id: string
  rank: number
  title: string
  description: string
  score: number // Deterministic score percentage (0-100)
  likelihood: HypothesisLikelihood
  supportingEvidenceCount: number
  contradictingEvidenceCount: number
  verified: boolean
  verificationReason?: string
}

export type EvidenceType = "metric" | "log" | "trace" | "deploy" | "runbook"
export type EvidencePolarity = "supporting" | "contradicting" | "neutral"

export interface EvidenceItem {
  id: string
  hypothesisId: string
  type: EvidenceType
  title: string
  polarity: EvidencePolarity
  delta?: string
  source: string
  timestamp: string
  summary: string
  rawSnippet?: string
  weight: number
}

export interface InvestigationLogEntry {
  id: string
  timestamp: string
  level: "ERROR" | "WARN" | "INFO" | "DEBUG"
  service: string
  message: string
  traceId?: string
}

export interface TraceSpan {
  id: string
  name: string
  service: string
  durationMs: number
  startOffsetMs: number
  statusCode: "OK" | "ERROR"
  attributes?: Record<string, string | number>
}

export type RemediationApprovalStatus = "AWAITING_APPROVAL" | "APPROVED" | "REJECTED"

export interface RemediationProposal {
  id: string
  incidentId: string
  rootCauseTitle: string
  rootCauseDescription: string
  actionTitle: string
  actionDescription: string
  targetService: string
  allowlistedAction: string
  configDiff: string
  status: RemediationApprovalStatus
  approvedBy?: string
  approvedAt?: string
  rejectionReason?: string
}

export type InvestigationTab =
  "hypotheses" | "evidence" | "logs" | "metrics" | "traces" | "agent-activity"

export interface KnowledgeSource {
  doc_id: string
  chunk_id?: string
  title: string
  source?: string
  service?: string
  excerpt: string
  similarity_score?: number
  rank?: number
  included_in_context: boolean
  why_relevant?: string
}

export interface IncidentInvestigationData {
  incidentId: string
  title: string
  service: string
  status: "INVESTIGATING" | "VERIFYING" | "RESOLVED"
  openedAt: string
  summary: string
  steps: InvestigationStep[]
  hypotheses: Hypothesis[]
  evidence: EvidenceItem[]
  logs: InvestigationLogEntry[]
  traces: TraceSpan[]
  remediation: RemediationProposal
  retrievedSources?: KnowledgeSource[]
  retrievalStatus?: string
}

export interface AuditLogEntry {
  id: string
  timestamp: string
  action: string
  actor: string
  investigation_id: string
  incident_id: string
  proposal_id?: string
  reason?: string
  details: string
}



