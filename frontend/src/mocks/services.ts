import type { ServiceHealth, ServiceMetricPoint } from "../types"

export const mockServices: ServiceHealth[] = [
  {
    id: "api",
    name: "api",
    displayName: "API",
    uptime: 99.9,
    status: "HEALTHY",
    p95Latency: "48ms",
    errorRate: "0.02%",
    sparkline: [45, 48, 46, 52, 47, 49, 48],
  },
  {
    id: "orders",
    name: "orders",
    displayName: "Orders",
    uptime: 98.7,
    status: "DEGRADED",
    p95Latency: "1.2s",
    errorRate: "4.85%",
    sparkline: [120, 140, 180, 290, 850, 1200, 1240],
  },
  {
    id: "payments",
    name: "payments",
    displayName: "Payments",
    uptime: 99.4,
    status: "DEGRADED",
    p95Latency: "380ms",
    errorRate: "1.92%",
    sparkline: [210, 220, 215, 290, 340, 380, 375],
  },
  {
    id: "auth",
    name: "auth",
    displayName: "Auth",
    uptime: 99.8,
    status: "HEALTHY",
    p95Latency: "24ms",
    errorRate: "0.01%",
    sparkline: [22, 24, 25, 23, 24, 25, 24],
  },
]

// 1-hour time-series points at 5-minute intervals (matching reference chart timeline 18:30 - 19:30)
export const mockLatencyMetrics: ServiceMetricPoint[] = [
  { timestamp: "18:30", timeLabel: "18:30", api: 45, orders: 120, payments: 210, auth: 22 },
  { timestamp: "18:35", timeLabel: "18:35", api: 48, orders: 135, payments: 215, auth: 24 },
  { timestamp: "18:40", timeLabel: "18:40", api: 46, orders: 130, payments: 220, auth: 23 },
  { timestamp: "18:45", timeLabel: "18:45", api: 52, orders: 145, payments: 225, auth: 25 },
  { timestamp: "18:50", timeLabel: "18:50", api: 47, orders: 180, payments: 230, auth: 24 },
  { timestamp: "18:55", timeLabel: "18:55", api: 49, orders: 210, payments: 240, auth: 25 },
  { timestamp: "19:00", timeLabel: "19:00", api: 48, orders: 340, payments: 260, auth: 24 },
  { timestamp: "19:05", timeLabel: "19:05", api: 50, orders: 490, payments: 290, auth: 26 },
  { timestamp: "19:10", timeLabel: "19:10", api: 52, orders: 820, payments: 330, auth: 25 },
  { timestamp: "19:15", timeLabel: "19:15", api: 55, orders: 1380, payments: 380, auth: 27 },
  { timestamp: "19:20", timeLabel: "19:20", api: 53, orders: 1120, payments: 360, auth: 26 },
  { timestamp: "19:25", timeLabel: "19:25", api: 49, orders: 1240, payments: 375, auth: 25 },
  { timestamp: "19:30", timeLabel: "19:30", api: 51, orders: 1180, payments: 365, auth: 24 },
]

export const mockErrorRateMetrics: ServiceMetricPoint[] = [
  { timestamp: "18:30", timeLabel: "18:30", api: 0.01, orders: 0.12, payments: 0.25, auth: 0.01 },
  { timestamp: "18:35", timeLabel: "18:35", api: 0.02, orders: 0.15, payments: 0.28, auth: 0.01 },
  { timestamp: "18:40", timeLabel: "18:40", api: 0.01, orders: 0.14, payments: 0.31, auth: 0.02 },
  { timestamp: "18:45", timeLabel: "18:45", api: 0.02, orders: 0.22, payments: 0.35, auth: 0.01 },
  { timestamp: "18:50", timeLabel: "18:50", api: 0.01, orders: 0.45, payments: 0.42, auth: 0.02 },
  { timestamp: "18:55", timeLabel: "18:55", api: 0.03, orders: 0.78, payments: 0.58, auth: 0.01 },
  { timestamp: "19:00", timeLabel: "19:00", api: 0.02, orders: 1.45, payments: 0.82, auth: 0.02 },
  { timestamp: "19:05", timeLabel: "19:05", api: 0.02, orders: 2.3, payments: 1.15, auth: 0.01 },
  { timestamp: "19:10", timeLabel: "19:10", api: 0.04, orders: 3.85, payments: 1.58, auth: 0.03 },
  { timestamp: "19:15", timeLabel: "19:15", api: 0.03, orders: 5.4, payments: 2.1, auth: 0.02 },
  { timestamp: "19:20", timeLabel: "19:20", api: 0.02, orders: 4.95, payments: 1.88, auth: 0.01 },
  { timestamp: "19:25", timeLabel: "19:25", api: 0.02, orders: 4.85, payments: 1.92, auth: 0.02 },
  { timestamp: "19:30", timeLabel: "19:30", api: 0.02, orders: 4.7, payments: 1.85, auth: 0.01 },
]

export const mockThroughputMetrics: ServiceMetricPoint[] = [
  { timestamp: "18:30", timeLabel: "18:30", api: 1250, orders: 420, payments: 280, auth: 850 },
  { timestamp: "18:35", timeLabel: "18:35", api: 1280, orders: 435, payments: 295, auth: 870 },
  { timestamp: "18:40", timeLabel: "18:40", api: 1310, orders: 440, payments: 310, auth: 890 },
  { timestamp: "18:45", timeLabel: "18:45", api: 1390, orders: 460, payments: 325, auth: 910 },
  { timestamp: "18:50", timeLabel: "18:50", api: 1420, orders: 485, payments: 340, auth: 935 },
  { timestamp: "18:55", timeLabel: "18:55", api: 1480, orders: 510, payments: 355, auth: 960 },
  { timestamp: "19:00", timeLabel: "19:00", api: 1540, orders: 540, payments: 370, auth: 980 },
  { timestamp: "19:05", timeLabel: "19:05", api: 1590, orders: 580, payments: 395, auth: 1020 },
  { timestamp: "19:10", timeLabel: "19:10", api: 1620, orders: 590, payments: 410, auth: 1040 },
  { timestamp: "19:15", timeLabel: "19:15", api: 1650, orders: 575, payments: 405, auth: 1055 },
  { timestamp: "19:20", timeLabel: "19:20", api: 1610, orders: 550, payments: 390, auth: 1030 },
  { timestamp: "19:25", timeLabel: "19:25", api: 1580, orders: 535, payments: 385, auth: 1010 },
  { timestamp: "19:30", timeLabel: "19:30", api: 1560, orders: 520, payments: 375, auth: 995 },
]
