import React from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { Activity, Database } from "lucide-react"
import { Card } from "../common/Card"

export const MetricsView: React.FC = () => {
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

  return (
    <div className="space-y-4">
      {/* PromQL Query Header */}
      <div className="p-3 rounded bg-ink/70 border border-ash font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-dust">
          <Activity className="w-4 h-4 text-amber shrink-0" />
          <span className="text-bone">Tool: query_metrics(promql, window=&apos;15m&apos;)</span>
        </div>
        <span className="text-[11px] text-verdigris">Telemetry Correlation Confirmed (r=0.96)</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Chart 1: DB Pool Saturation */}
        <Card className="p-4 space-y-3">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Database className="w-3.5 h-3.5 text-amber" />
                <span className="text-xs font-semibold text-bone">
                  Database Connection Pool Saturation
                </span>
              </div>
              <div className="text-[11px] font-mono text-dust mt-0.5 truncate">
                orders_db_pool_active vs max (limit: 20)
              </div>
            </div>
            <span className="text-xs font-mono text-amber font-semibold">100% Locked</span>
          </div>

          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={poolData} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
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
                  tickLine={false}
                  fontFamily="monospace"
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-soot border border-ash p-2 rounded text-xs font-mono">
                          <div className="text-dust">{String(label)}</div>
                          <div className="text-amber">Active: {payload[0]?.value} / 20</div>
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
                  dot={{ r: 3 }}
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

        {/* Chart 2: Latency Escalation */}
        <Card className="p-4 space-y-3">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Activity className="w-3.5 h-3.5 text-vermilion" />
                <span className="text-xs font-semibold text-bone">
                  Orders API Response Time (p95)
                </span>
              </div>
              <div className="text-[11px] font-mono text-dust mt-0.5 truncate">
                histogram_quantile(0.95, rate(http_request_duration...))
              </div>
            </div>
            <span className="text-xs font-mono text-vermilion font-semibold">1,240ms (+820%)</span>
          </div>

          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={latencyData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
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
                  tickLine={false}
                  tickFormatter={(v) => `${v}ms`}
                  fontFamily="monospace"
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-soot border border-ash p-2 rounded text-xs font-mono">
                          <div className="text-dust">{String(label)}</div>
                          <div className="text-vermilion">p95 Latency: {payload[0]?.value}ms</div>
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
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  )
}
