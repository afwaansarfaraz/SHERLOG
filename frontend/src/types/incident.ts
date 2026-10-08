export type IncidentStatus = "INVESTIGATING" | "RESOLVED" | "AWAITING_APPROVAL" | "OPEN"

export type IncidentSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"

export interface Incident {
  id: string
  title: string
  service: string
  status: IncidentStatus
  severity: IncidentSeverity
  openedAt: string
  resolvedAt?: string
  summary: string
  affectedEndpoints?: string[]
  assignedTo?: string
}
