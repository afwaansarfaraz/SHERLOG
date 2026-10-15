import React, { useState } from "react"
import { Search, ShieldAlert, FileText, AlertCircle, RefreshCw } from "lucide-react"
import { LogsViewSkeleton } from "../common/Skeletons"
import { EmptyState } from "../common/EmptyState"
import { Button } from "../common/Button"
import type { InvestigationLogEntry } from "../../types"

interface LogsViewProps {
  logs: InvestigationLogEntry[]
  isLoading?: boolean
  error?: string | null
  onRetry?: () => void
}

export const LogsView: React.FC<LogsViewProps> = ({
  logs,
  isLoading = false,
  error = null,
  onRetry,
}) => {
  const [filter, setFilter] = useState("")

  if (isLoading) {
    return <LogsViewSkeleton rowCount={6} />
  }

  if (error) {
    return (
      <div
        role="alert"
        className="p-6 rounded-lg bg-soot border border-ash/80 space-y-4 text-center"
      >
        <div className="w-10 h-10 rounded-lg bg-[#2D1618] border border-[#4F2025] text-vermilion flex items-center justify-center mx-auto">
          <AlertCircle className="w-5 h-5" />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-bone font-sans">
            Loki Log Telemetry Engine Unavailable
          </h4>
          <p className="text-xs text-dust max-w-md mx-auto mt-1 leading-relaxed">
            {error || "Failed to stream log lines from the Loki cluster. Upstream metrics and traces remain usable."}
          </p>
        </div>
        {onRetry && (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            <span>Retry Log Stream</span>
          </Button>
        )}
      </div>
    )
  }

  if (logs.length === 0) {
    return (
      <EmptyState
        variant="no-telemetry"
        title="No Log Records Found"
        description="The Loki log query returned zero records for service 'orders' in the 15-minute window."
        actionLabel={onRetry ? "Refetch Logs" : undefined}
        onAction={onRetry}
      />
    )
  }

  const filteredLogs = logs.filter(
    (l) =>
      l.message.toLowerCase().includes(filter.toLowerCase()) ||
      l.level.toLowerCase().includes(filter.toLowerCase()) ||
      (l.traceId && l.traceId.toLowerCase().includes(filter.toLowerCase()))
  )

  const getLevelStyle = (level: string) => {
    switch (level) {
      case "ERROR":
        return "bg-[#2D1618] text-vermilion border border-[#4F2025]"
      case "WARN":
        return "bg-[#291F13] text-amber border border-[#4A391A]"
      case "INFO":
        return "bg-[#162722] text-verdigris border border-[#234A3E]"
      default:
        return "bg-soot text-dust border border-ash"
    }
  }

  return (
    <div className="space-y-3 font-mono text-xs">
      {/* Search & Tool Query Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 p-2.5 rounded bg-ink/70 border border-ash">
        <div className="flex items-center gap-2 text-dust text-[11px] min-w-0 flex-1">
          <FileText className="w-3.5 h-3.5 text-amber shrink-0" />
          <span className="text-bone shrink-0">Tool: search_logs</span>
          <span className="truncate">
            query: service=&apos;orders&apos; pattern=&apos;pool|timeout|error&apos; (window: 15m)
          </span>
        </div>

        <div className="flex items-center gap-2 bg-soot border border-ash rounded px-2 py-1 shrink-0">
          <Search className="w-3 h-3 text-dust" />
          <input
            id="logs-filter-input"
            name="logsFilter"
            type="text"
            placeholder="Filter logs..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-transparent text-bone placeholder:text-dust text-[11px] outline-none font-sans w-32 sm:w-40"
          />
        </div>
      </div>

      {/* Untrusted Data Boundary Notice */}
      <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-[#1C1713] border border-ash/80 text-[11px] text-dust">
        <ShieldAlert className="w-3.5 h-3.5 text-amber shrink-0" />
        <span>
          Output Sanitized: Logs are treated as untrusted data and delimited to defend against
          prompt injection.
        </span>
      </div>

      {/* Log Feed */}
      <div className="rounded-md bg-ink border border-ash overflow-hidden divide-y divide-ash/40 max-h-96 overflow-y-auto custom-scrollbar">
        {filteredLogs.map((log) => (
          <div
            key={log.id}
            className="p-2.5 hover:bg-soot/40 transition-colors flex items-start gap-2.5 leading-relaxed"
          >
            <span className="text-dust text-[11px] shrink-0 font-mono">{log.timestamp}</span>

            <span
              className={`px-1.5 py-0.5 rounded text-[10px] font-semibold shrink-0 uppercase ${getLevelStyle(
                log.level
              )}`}
            >
              {log.level}
            </span>

            <span className="text-dust text-[11px] shrink-0 font-mono">[{log.service}]</span>

            <span className="text-bone/90 flex-1 break-words [word-break:break-word] select-text font-mono text-[11px]">
              {log.message}
            </span>

            {log.traceId && (
              <span className="text-slate text-[10px] shrink-0 hidden md:inline font-mono">
                trace:{log.traceId.slice(0, 8)}
              </span>
            )}
          </div>
        ))}

        {filteredLogs.length === 0 && (
          <div className="p-6 text-center text-dust text-xs">
            <EmptyState
              variant="no-search-results"
              searchQuery={filter}
              actionLabel="Clear Filter"
              onAction={() => setFilter("")}
              className="bg-transparent border-0"
            />
          </div>
        )}
      </div>
    </div>
  )
}
