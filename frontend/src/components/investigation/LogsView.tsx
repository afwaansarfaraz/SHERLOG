import React, { useState } from "react"
import { Search, ShieldAlert, FileText } from "lucide-react"
import type { InvestigationLogEntry } from "../../types"

interface LogsViewProps {
  logs: InvestigationLogEntry[]
}

export const LogsView: React.FC<LogsViewProps> = ({ logs }) => {
  const [filter, setFilter] = useState("")

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
            No log lines matching pattern &apos;{filter}&apos;
          </div>
        )}
      </div>
    </div>
  )
}
