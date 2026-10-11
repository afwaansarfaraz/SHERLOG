import React, { useState } from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { Activity, Database, Layers, ArrowUpRight } from "lucide-react"
import { Card } from "../common/Card"

type MetricFilter = "all" | "db-pool" | "latency"

export const MetricsView: React.FC = () => {
  const [selectedMetric, setSelectedMetric] = useState<MetricFilter>("all")

  // Metric 1: DB Pool Saturation Time Series
  const poolData = [
    { time: "19:30", active: 6, max: 20 },
    { time: "19:35", active: 8, max: 20 },
    { time: "19:40", active: 11, max: 20 },
    { time: "19:41", active: 16, max: 20 },
    { time: "19:42", active: 20, max: 20 },
    { time: "19:43", active: 20, max: 20 },
    { time: "19:44", active: 20, max: 20 },
  ]

  // Metric 2: HTTP Latency Spike Time Series
  const latencyData = [
    { time: "19:30", p95: 145 },
    { time: "19:35", p95: 155 },
    { time: "19:40", p95: 320 },
    { time: "19:41", p95: 780 },
    { time: "19:42", p95: 1240 },
    { time: "19:43", p95: 1210 },
    { time: "19:44", p95: 1250 },
  ]

  const showDbPool = selectedMetric === "all" || selectedMetric === "db-pool"
  const showLatency = selectedMetric === "all" || selectedMetric === "latency"

  return (
    <div className="space-y-4">
      {/* PromQL Query Header & Filter Bar */}
      <div className="p-2.5 sm:p-3 rounded bg-ink/70 border border-ash font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-3">
        <div className="flex items-center gap-2 text-dust min-w-0">
          <Activity className="w-4 h-4 text-amber shrink-0" />
          <span className="text-bone break-all sm:truncate">Tool: query_metrics(promql, window=&apos;15m&apos;)</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[11px] text-verdigris flex items-center gap-1 whitespace-nowrap">
            <span className="w-1.5 h-1.5 rounded-full bg-verdigris animate-pulse shrink-0" />
            Telemetry Correlation Confirmed (r=0.96)
          </span>
        </div>
      </div>

      {/* Metric Switcher Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ash/50 pb-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setSelectedMetric("all")}
            className={`px-2.5 py-1 rounded text-xs font-mono whitespace-nowrap transition-colors ${
              selectedMetric === "all"
                ? "bg-soot text-bone border border-ash shadow-sm"
                : "text-dust hover:text-bone border border-transparent"
            }`}
          >
            <span className="flex items-center gap-1.5">
              <Layers className="w-3 h-3 text-amber shrink-0" />
              All Telemetry (2)
            </span>
          </button>
          <button
            onClick={() => setSelectedMetric("db-pool")}
            className={`px-2.5 py-1 rounded text-xs font-mono whitespace-nowrap transition-colors ${
              selectedMetric === "db-pool"
                ? "bg-soot text-bone border border-ash shadow-sm"
                : "text-dust hover:text-bone border border-transparent"
            }`}
          >
            <span className="flex items-center gap-1.5">
              <Database className="w-3 h-3 text-amber shrink-0" />
              DB Pool
            </span>
          </button>
          <button
            onClick={() => setSelectedMetric("latency")}
            className={`px-2.5 py-1 rounded text-xs font-mono whitespace-nowrap transition-colors ${
              selectedMetric === "latency"
                ? "bg-soot text-bone border border-ash shadow-sm"
                : "text-dust hover:text-bone border border-transparent"
            }`}
          >
            <span className="flex items-center gap-1.5">
              <Activity className="w-3 h-3 text-vermilion shrink-0" />
              API Latency
            </span>
          </button>
        </div>
        <span className="text-[11px] font-mono text-dust whitespace-nowrap hidden sm:inline">
          Time Window: 19:30 – 19:44
        </span>
      </div>

      {/* Stacked Telemetry Charts (Full Width to Prevent Text/Label Squeeze) */}
      <div className="flex flex-col gap-4">
        {/* Chart 1: DB Pool Saturation */}
        {showDbPool && (
          <Card className="p-4 sm:p-5 space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3 min-w-0">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 min-w-0">
                  <Database className="w-4 h-4 text-amber shrink-0" />
                  <span className="text-xs sm:text-sm font-semibold text-bone truncate">
                    Database Connection Pool Saturation
                  </span>
                </div>
                <div
                  className="text-[11px] font-mono text-dust mt-1 truncate"
                  title="orders_db_pool_active vs max (limit: 20)"
                >
                  orders_db_pool_active vs max (limit: 20)
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs font-mono text-amber font-semibold px-2 py-0.5 rounded bg-amber/10 border border-amber/30 whitespace-nowrap">
                  100% Locked
                </span>
              </div>
            </div>

            {/* Quick KPI stats row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 py-2 px-3 rounded bg-ink/60 border border-ash/60 text-[11px] font-mono">
              <div>
                <span className="text-dust block">Active Conn</span>
                <span className="text-amber font-semibold">20 / 20</span>
              </div>
              <div>
                <span className="text-dust block">Utilization</span>
                <span className="text-vermilion font-semibold">100.0%</span>
              </div>
              <div>
                <span className="text-dust block">Queue Depth</span>
                <span className="text-amber font-semibold">14 waiting</span>
              </div>
              <div>
                <span className="text-dust block">Status</span>
                <span className="text-vermilion font-semibold">Exhausted</span>
              </div>
            </div>

            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={poolData} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
                  <CartesianGrid stroke="#26211C" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="time"
                    stroke="#5C564B"
                    fontSize={10}
                    tickLine={false}
                    fontFamily="monospace"
                  />
                  <YAxis
                    domain={[0, 25]}
                    stroke="#5C564B"
                    fontSize={10}
                    width={36}
                    tickLine={false}
                    fontFamily="monospace"
                  />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-soot border border-ash p-2 rounded text-xs font-mono shadow-md">
                            <div className="text-dust">{String(label)}</div>
                            <div className="text-amber">Active: {payload[0]?.value} / 20</div>
                            <div className="text-dust text-[10px]">Max Pool Limit: 20</div>
                          </div>
                        )
                      }
                      return null
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="active"
                    stroke="#E0A63A"
                    strokeWidth={2}
                    dot={{ r: 3, fill: "#E0A63A" }}
                  />
                  <Line
                    type="step"
                    dataKey="max"
                    stroke="#8C8576"
                    strokeDasharray="3 3"
                    strokeWidth={1}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}

        {/* Chart 2: Latency Escalation */}
        {showLatency && (
          <Card className="p-4 sm:p-5 space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3 min-w-0">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 min-w-0">
                  <Activity className="w-4 h-4 text-vermilion shrink-0" />
                  <span className="text-xs sm:text-sm font-semibold text-bone truncate">
                    Orders API Response Time (p95)
                  </span>
                </div>
                <div
                  className="text-[11px] font-mono text-dust mt-1 truncate"
                  title="histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
                >
                  histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs font-mono text-vermilion font-semibold px-2 py-0.5 rounded bg-vermilion/10 border border-vermilion/30 whitespace-nowrap flex items-center gap-1">
                  <ArrowUpRight className="w-3 h-3 text-vermilion" />
                  1,240ms (+820%)
                </span>
              </div>
            </div>

            {/* Quick KPI stats row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 py-2 px-3 rounded bg-ink/60 border border-ash/60 text-[11px] font-mono">
              <div>
                <span className="text-dust block">p95 Current</span>
                <span className="text-vermilion font-semibold">1,240ms</span>
              </div>
              <div>
                <span className="text-dust block">Baseline</span>
                <span className="text-verdigris font-semibold">145ms</span>
              </div>
              <div>
                <span className="text-dust block">Degradation</span>
                <span className="text-vermilion font-semibold">+8.2x</span>
              </div>
              <div>
                <span className="text-dust block">SLA Target</span>
                <span className="text-dust font-semibold">&lt; 300ms</span>
              </div>
            </div>

            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={latencyData} margin={{ top: 10, right: 15, left: 5, bottom: 0 }}>
                  <CartesianGrid stroke="#26211C" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="time"
                    stroke="#5C564B"
                    fontSize={10}
                    tickLine={false}
                    fontFamily="monospace"
                  />
                  <YAxis
                    stroke="#5C564B"
                    fontSize={10}
                    width={52}
                    tickLine={false}
                    tickFormatter={(v) => `${v}ms`}
                    fontFamily="monospace"
                  />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-soot border border-ash p-2 rounded text-xs font-mono shadow-md">
                            <div className="text-dust">{String(label)}</div>
                            <div className="text-vermilion">p95 Latency: {payload[0]?.value}ms</div>
                            <div className="text-dust text-[10px]">Normal Baseline: ~145ms</div>
                          </div>
                        )
                      }
                      return null
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="p95"
                    stroke="#E4572E"
                    strokeWidth={2}
                    dot={{ r: 3, fill: "#E4572E" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
