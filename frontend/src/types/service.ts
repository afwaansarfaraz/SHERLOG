export type ServiceStatus = "HEALTHY" | "DEGRADED" | "CRITICAL"

export interface ServiceHealth {
  id: string
  name: string
  displayName: string
  uptime: number
  status: ServiceStatus
  p95Latency: string
  errorRate: string
  sparkline: number[]
}

export type MetricType = "latency" | "errorRate" | "throughput"

export interface ServiceMetricPoint {
  timestamp: string
  timeLabel: string
  api: number
  orders: number
  payments: number
  auth: number
}
