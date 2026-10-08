export type ActivityType =
  | "ALERT_RECEIVED"
  | "INVESTIGATION_STARTED"
  | "TOOL_EXECUTED"
  | "HYPOTHESIS_FORMULATED"
  | "VERIFICATION_SUCCESS"
  | "REMEDIATION_PROPOSED"
  | "INCIDENT_RESOLVED"

export interface ActivityItem {
  id: string
  timestamp: string
  incidentId: string
  incidentTitle: string
  type: ActivityType
  message: string
  details?: string
  service: string
}
