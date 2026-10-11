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
import { Activity } from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import type { MetricType } from "../../types"
import {
  mockLatencyMetrics,
  mockErrorRateMetrics,
  mockThroughputMetrics,
} from "../../mocks/services"

export const ServiceMetricsChart: React.FC = () => {
  const [activeMetric, setActiveMetric] = useState<MetricType>("latency")
  const [timeWindow, setTimeWindow] = useState("1h")

  const data =
    activeMetric === "latency"
      ? mockLatencyMetrics
      : activeMetric === "errorRate"
        ? mockErrorRateMetrics
        : mockThroughputMetrics

  const formatYAxis = (value: number) => {
    if (activeMetric === "latency") {
      if (value >= 1000) return `${(value / 1000).toFixed(1)}s`
      return `${value}ms`
    }
    if (activeMetric === "errorRate") {
      return `${value}%`
    }
    return `${value}`
  }

  // Case File Service Colors
  const colors = {
    orders: "#E4572E", // Vermilion (Spiking/Incidents)
    payments: "#8FA3C7", // Slate
    api: "#4FA38B", // Verdigris
    auth: "#E0A63A", // Amber
  }

  return (
    <Card className="flex flex-col h-full">
      {/* Header with Title and Time Window Select */}
      <CardHeader>
        <CardTitle>
          <Activity className="w-4 h-4 text-amber" />
          <span>Service Metrics</span>
        </CardTitle>

        <select
          id="metric-time-window"
          name="metricTimeWindow"
          value={timeWindow}
          onChange={(e) => setTimeWindow(e.target.value)}
          aria-label="Select metric time window"
          className="bg-ink text-dust text-xs border border-ash rounded px-2 py-1 outline-none font-mono focus:border-dust"
        >
          <option value="1h">Last 1 hour</option>
          <option value="6h">Last 6 hours</option>
          <option value="24h">Last 24 hours</option>
        </select>
      </CardHeader>

      {/* Tabs: Latency, Error Rate, Throughput */}
      <div className="flex items-center gap-1.5 p-1 bg-ink/70 border border-ash/70 rounded-md w-fit mb-4">
        {(["latency", "errorRate", "throughput"] as MetricType[]).map((tab) => {
          const labels: Record<MetricType, string> = {
            latency: "Latency",
            errorRate: "Error Rate",
            throughput: "Throughput",
          }
          const isActive = activeMetric === tab

          return (
            <button
              key={tab}
              onClick={() => setActiveMetric(tab)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors select-none ${
                isActive
                  ? "bg-soot text-bone border border-ash/80 shadow-sm"
                  : "text-dust hover:text-bone border border-transparent"
              }`}
            >
              {labels[tab]}
            </button>
          )
        })}
      </div>

      {/* Recharts LineChart */}
      <div className="h-56 sm:h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 15, left: -5, bottom: 0 }}>
            <CartesianGrid stroke="#26211C" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="timeLabel"
              stroke="#5C564B"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: "#332D26" }}
              fontFamily="monospace"
            />
            <YAxis
              stroke="#5C564B"
              fontSize={11}
              width={44}
              tickLine={false}
              axisLine={{ stroke: "#332D26" }}
              tickFormatter={formatYAxis}
              fontFamily="monospace"
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="bg-soot border border-ash rounded p-2.5 shadow-xl text-xs font-mono">
                      <div className="text-dust font-semibold border-b border-ash pb-1 mb-1.5">
                        {String(label)}
                      </div>
                      {payload.map((item) => (
                        <div
                          key={String(item.dataKey)}
                          className="flex items-center justify-between gap-4 py-0.5"
                        >
                          <span
                            className="capitalize flex items-center gap-1.5"
                            style={{ color: item.color }}
                          >
                            <span
                              className="w-2 h-2 rounded-full"
                              style={{ backgroundColor: item.color }}
                            />
                            {String(item.dataKey)}:
                          </span>
                          <span className="text-bone font-medium">
                            {formatYAxis(Number(item.value))}
                          </span>
                        </div>
                      ))}
                    </div>
                  )
                }
                return null
              }}
            />
            <Line
              type="monotone"
              dataKey="orders"
              stroke={colors.orders}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, stroke: "#14110F", strokeWidth: 2 }}
            />
            <Line
              type="monotone"
              dataKey="payments"
              stroke={colors.payments}
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="api"
              stroke={colors.api}
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="auth"
              stroke={colors.auth}
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Legend matching reference image */}
      <div className="flex items-center justify-center gap-4 sm:gap-6 pt-3 mt-1 border-t border-ash/60 text-xs font-sans text-dust select-none">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-verdigris" />
          <span className="text-bone">API</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-vermilion" />
          <span className="text-bone">Orders</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-slate" />
          <span className="text-bone">Payments</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-amber" />
          <span className="text-bone">Auth</span>
        </div>
      </div>
    </Card>
  )
}
