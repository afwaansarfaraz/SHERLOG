import React from "react"
import { GitCommit, AlertCircle, CheckCircle2 } from "lucide-react"
import type { TraceSpan } from "../../types"

interface TracesViewProps {
  traces: TraceSpan[]
}

export const TracesView: React.FC<TracesViewProps> = ({ traces }) => {
  const maxDuration = Math.max(...traces.map((t) => t.startOffsetMs + t.durationMs), 1240)

  return (
    <div className="space-y-3 font-mono text-xs">
      {/* Trace Overview Header */}
      <div className="p-2.5 sm:p-3 rounded bg-ink/70 border border-ash flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex items-center flex-wrap gap-2 text-dust min-w-0">
          <GitCommit className="w-4 h-4 text-amber shrink-0" />
          <span className="text-bone font-medium">Tool: get_traces(service=&apos;orders&apos;)</span>
          <span className="text-[11px] text-dust bg-soot/80 border border-ash/60 px-1.5 py-0.5 rounded font-mono">
            trace_id: 8f4a210bc931e4
          </span>
        </div>
        <div className="flex items-center gap-2 text-[11px] shrink-0">
          <span className="text-dust">Total Latency:</span>
          <span className="text-vermilion font-semibold">1,240ms</span>
          <span className="text-dust">•</span>
          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-[#2D1618] text-vermilion border border-[#4F2025]">
            HTTP 500
          </span>
        </div>
      </div>

      {/* Waterfall Visualization */}
      <div className="rounded-md bg-ink border border-ash p-4 space-y-3">
        <div className="text-[11px] text-dust border-b border-ash pb-2 flex items-center justify-between">
          <span>Span Hierarchy &amp; Latency Waterfall</span>
          <span>Timeline (0ms - {maxDuration}ms)</span>
        </div>

        <div className="space-y-3 pt-1">
          {traces.map((span) => {
            const leftPct = (span.startOffsetMs / maxDuration) * 100
            const widthPct = Math.max((span.durationMs / maxDuration) * 100, 2)
            const isError = span.statusCode === "ERROR"

            return (
              <div key={span.id} className="space-y-1">
                <div className="flex items-center justify-between gap-2 text-[11px]">
                  <div className="flex items-center gap-2 min-w-0">
                    {isError ? (
                      <AlertCircle className="w-3 h-3 text-vermilion shrink-0" />
                    ) : (
                      <CheckCircle2 className="w-3 h-3 text-verdigris shrink-0" />
                    )}
                    <span
                      className={`truncate ${isError ? "text-bone font-semibold" : "text-dust"}`}
                      title={span.name}
                    >
                      {span.name}
                    </span>
                    <span className="text-dust/70 text-[10px] shrink-0">[{span.service}]</span>
                  </div>
                  <span
                    className={`shrink-0 font-medium ${
                      isError ? "text-vermilion font-semibold" : "text-dust"
                    }`}
                  >
                    {span.durationMs}ms
                  </span>
                </div>

                {/* Timeline Bar Container */}
                <div className="h-2 w-full bg-[#201B17] rounded overflow-hidden relative">
                  <div
                    className={`h-full rounded transition-all duration-500 ${
                      isError ? "bg-vermilion" : "bg-verdigris"
                    }`}
                    style={{
                      marginLeft: `${leftPct}%`,
                      width: `${widthPct}%`,
                    }}
                  />
                </div>

                {/* Attributes Callout if Error */}
                {isError && span.attributes && (
                  <div className="text-[10px] text-dust pl-5 font-mono pt-0.5 flex flex-wrap gap-2">
                    {Object.entries(span.attributes).map(([k, v]) => (
                      <span key={k} className="bg-soot border border-ash/60 px-1.5 py-0.5 rounded">
                        {k}: <span className="text-amber">{String(v)}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
