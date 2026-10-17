import React, { useState, useEffect, useCallback, useMemo } from "react"
import {
  FileText,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  User,
  Clock,
  RefreshCw,
  Search,
  Filter,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  Hash,
} from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import { Badge } from "../common/Badge"
import { Button } from "../common/Button"
import { EmptyState } from "../common/EmptyState"
import { api, ApiClientError } from "../../lib/api"
import type { AuditLogEntry } from "../../types/investigation"

interface AuditLogsViewProps {
  onBackToOverview: () => void
  onSelectIncident?: (id: string) => void
}

export const AuditLogsView: React.FC<AuditLogsViewProps> = ({
  onBackToOverview,
  onSelectIncident,
}) => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [searchIncident, setSearchIncident] = useState<string>("")
  const [actionFilter, setActionFilter] = useState<string>("ALL")
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false)

  const fetchAuditLogs = useCallback(async () => {
    try {
      setError(null)
      const data = await api.get<AuditLogEntry[]>("/api/audit-logs")
      setLogs(Array.isArray(data) ? data : [])
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message)
      } else {
        setError("Failed to fetch audit log trail from backend.")
      }
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [])

  useEffect(() => {
    fetchAuditLogs()
  }, [fetchAuditLogs])

  const handleManualRefresh = () => {
    setIsRefreshing(true)
    fetchAuditLogs()
  }

  // Filter logs based on search query and action
  const filteredLogs = useMemo(() => {
    return logs.filter((entry) => {
      const matchesIncident =
        !searchIncident.trim() ||
        entry.incident_id.toLowerCase().includes(searchIncident.trim().toLowerCase()) ||
        (entry.proposal_id &&
          entry.proposal_id.toLowerCase().includes(searchIncident.trim().toLowerCase())) ||
        entry.id.toLowerCase().includes(searchIncident.trim().toLowerCase())

      const matchesAction =
        actionFilter === "ALL" || entry.action === actionFilter

      return matchesIncident && matchesAction
    })
  }, [logs, searchIncident, actionFilter])

  // Summary Metrics
  const metrics = useMemo(() => {
    const total = logs.length
    const approved = logs.filter((l) => l.action === "REMEDIATION_APPROVED").length
    const rejected = logs.filter((l) => l.action === "REMEDIATION_REJECTED").length
    const uniqueActors = new Set(logs.map((l) => l.actor)).size
    return { total, approved, rejected, uniqueActors }
  }, [logs])

  const formatTimestamp = (iso: string) => {
    try {
      const date = new Date(iso)
      return date.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      })
    } catch {
      return iso
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      {/* Header & Back Action */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBackToOverview}>
            <ArrowLeft className="w-4 h-4 mr-1" /> Overview
          </Button>
          <div>
            <h2 className="text-xl font-semibold text-bone flex items-center gap-2">
              <FileText className="w-5 h-5 text-amber" />
              Audit &amp; Remediation Trail
            </h2>
            <p className="text-xs text-dust mt-0.5">
              Append-only relational audit log of human approvals, rejections, and proposal lifecycles.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleManualRefresh}
            disabled={isLoading || isRefreshing}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="p-3.5 bg-obsidian/60">
          <span className="text-[11px] font-mono text-dust block uppercase tracking-wider">
            Total Audit Records
          </span>
          <span className="text-2xl font-bold font-mono text-bone mt-1 block">
            {metrics.total}
          </span>
          <span className="text-[10px] text-dust/70 flex items-center gap-1 mt-0.5">
            <ShieldCheck className="w-3 h-3 text-verdigris" /> Append-only storage
          </span>
        </Card>

        <Card className="p-3.5 bg-obsidian/60">
          <span className="text-[11px] font-mono text-dust block uppercase tracking-wider">
            Approved Proposals
          </span>
          <span className="text-2xl font-bold font-mono text-verdigris mt-1 block">
            {metrics.approved}
          </span>
          <span className="text-[10px] text-dust/70 flex items-center gap-1 mt-0.5">
            <CheckCircle2 className="w-3 h-3 text-verdigris" /> Authorized by humans
          </span>
        </Card>

        <Card className="p-3.5 bg-obsidian/60">
          <span className="text-[11px] font-mono text-dust block uppercase tracking-wider">
            Rejected Proposals
          </span>
          <span className="text-2xl font-bold font-mono text-vermilion mt-1 block">
            {metrics.rejected}
          </span>
          <span className="text-[10px] text-dust/70 flex items-center gap-1 mt-0.5">
            <XCircle className="w-3 h-3 text-vermilion" /> Dismissed with reason
          </span>
        </Card>

        <Card className="p-3.5 bg-obsidian/60">
          <span className="text-[11px] font-mono text-dust block uppercase tracking-wider">
            Active Operators
          </span>
          <span className="text-2xl font-bold font-mono text-amber mt-1 block">
            {metrics.uniqueActors}
          </span>
          <span className="text-[10px] text-dust/70 flex items-center gap-1 mt-0.5">
            <User className="w-3 h-3 text-amber" /> Decision actors
          </span>
        </Card>
      </div>

      {/* Filter and Search Controls */}
      <Card className="p-3.5 bg-ink border-ash/70 space-y-3">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex flex-1 items-center gap-2 w-full">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-dust absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                placeholder="Filter by Incident ID (e.g. INC-00012) or Proposal ID..."
                value={searchIncident}
                onChange={(e) => setSearchIncident(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-obsidian border border-ash/70 rounded text-bone placeholder:text-dust/60 focus:outline-none focus:border-amber transition-colors"
              />
            </div>
            {searchIncident && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSearchIncident("")}
                className="text-xs text-dust h-8 px-2"
              >
                Clear
              </Button>
            )}
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto shrink-0">
            <Filter className="w-3.5 h-3.5 text-dust" />
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="text-xs bg-obsidian border border-ash/70 rounded px-2.5 py-1.5 text-bone focus:outline-none focus:border-amber transition-colors"
            >
              <option value="ALL">All Actions</option>
              <option value="REMEDIATION_APPROVED">Approved Only</option>
              <option value="REMEDIATION_REJECTED">Rejected Only</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Error Banner */}
      {error && (
        <Card className="p-4 bg-vermilion/10 border-vermilion/40 text-vermilion space-y-2">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>Audit Log Retrieval Error</span>
          </div>
          <p className="text-xs text-bone/90">{error}</p>
          <Button variant="outline" size="sm" onClick={handleManualRefresh} className="mt-2 text-xs">
            Retry Connection
          </Button>
        </Card>
      )}

      {/* Main Audit Records Table */}
      <Card className="overflow-hidden">
        <CardHeader className="border-b border-ash/60 bg-obsidian/40 py-3">
          <div className="flex items-center justify-between">
            <CardTitle>
              <ShieldCheck className="w-4 h-4 text-jade" />
              <span>Relational Audit Trail Records</span>
            </CardTitle>
            <span className="font-mono text-xs text-dust">
              Showing {filteredLogs.length} of {logs.length} records
            </span>
          </div>
        </CardHeader>

        {isLoading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="animate-pulse flex items-center justify-between py-2 border-b border-ash/40">
                <div className="h-4 bg-ash/40 rounded w-1/4" />
                <div className="h-4 bg-ash/40 rounded w-1/6" />
                <div className="h-4 bg-ash/40 rounded w-1/6" />
                <div className="h-4 bg-ash/40 rounded w-1/4" />
              </div>
            ))}
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="p-8">
            <EmptyState
              variant="no-search-results"
              title="No Audit Log Records Found"
              description={
                searchIncident || actionFilter !== "ALL"
                  ? "No audit records match the current filter criteria."
                  : "No audit events recorded yet. Human approvals or rejections on incident remediation proposals will be recorded here."
              }
            />
          </div>
        ) : (
          <div className="divide-y divide-ash/60">
            {filteredLogs.map((entry) => {
              const isExpanded = expandedRowId === entry.id
              const isApproved = entry.action === "REMEDIATION_APPROVED"
              const isRejected = entry.action === "REMEDIATION_REJECTED"

              return (
                <div
                  key={entry.id}
                  className="p-3.5 hover:bg-ink/40 transition-colors cursor-pointer"
                  onClick={() => setExpandedRowId(isExpanded ? null : entry.id)}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5">
                    <div className="flex items-center gap-2.5 min-w-0 flex-1">
                      <button
                        type="button"
                        className="text-dust hover:text-bone transition-colors"
                        aria-label={isExpanded ? "Collapse row" : "Expand row"}
                      >
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4 shrink-0" />
                        ) : (
                          <ChevronRight className="w-4 h-4 shrink-0" />
                        )}
                      </button>

                      <Badge
                        variant={isApproved ? "healthy" : isRejected ? "critical" : "slate"}
                        withDot
                        className="shrink-0 font-mono text-[11px]"
                      >
                        {isApproved
                          ? "APPROVED"
                          : isRejected
                          ? "REJECTED"
                          : entry.action}
                      </Badge>

                      <span className="font-mono text-xs text-dust shrink-0">
                        {entry.id}
                      </span>

                      <div className="flex items-center gap-1.5 shrink-0">
                        <User className="w-3.5 h-3.5 text-dust" />
                        <span className="text-xs font-medium text-bone">
                          {entry.actor}
                        </span>
                      </div>

                      <div className="truncate text-xs text-dust/90 min-w-0">
                        {entry.details}
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0 self-end sm:self-auto">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          if (onSelectIncident) {
                            onSelectIncident(entry.incident_id)
                          }
                        }}
                        className="font-mono text-xs text-amber hover:underline flex items-center gap-1 bg-[#271E14] px-2 py-0.5 rounded border border-[#4A391A]"
                      >
                        <Hash className="w-3 h-3" />
                        {entry.incident_id}
                      </button>

                      <div className="font-mono text-[11px] text-dust flex items-center gap-1">
                        <Clock className="w-3 h-3 text-dust/70" />
                        <span>{formatTimestamp(entry.timestamp)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Audit Record Details */}
                  {isExpanded && (
                    <div className="mt-3.5 pt-3.5 border-t border-ash/40 pl-6 space-y-2.5 text-xs font-mono">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-dust">
                        <div>
                          <span className="text-bone/70 block text-[10px] uppercase">Record ID</span>
                          <span className="text-bone">{entry.id}</span>
                        </div>
                        <div>
                          <span className="text-bone/70 block text-[10px] uppercase">Exact UTC Timestamp</span>
                          <span className="text-bone">{entry.timestamp}</span>
                        </div>
                        <div>
                          <span className="text-bone/70 block text-[10px] uppercase">Investigation Ref</span>
                          <span className="text-bone">{entry.investigation_id}</span>
                        </div>
                        <div>
                          <span className="text-bone/70 block text-[10px] uppercase">Proposal Identifier</span>
                          <span className="text-bone">{entry.proposal_id || "N/A"}</span>
                        </div>
                      </div>

                      {entry.reason && (
                        <div className="p-2.5 rounded bg-obsidian border border-ash/60">
                          <span className="text-[10px] uppercase text-vermilion font-bold block mb-0.5">
                            Rejection / Decision Rationale
                          </span>
                          <p className="text-xs font-sans text-bone/90">{entry.reason}</p>
                        </div>
                      )}

                      <div className="p-2.5 rounded bg-obsidian border border-ash/60">
                        <span className="text-[10px] uppercase text-dust/80 font-bold block mb-0.5">
                          Audit Trail Full Details
                        </span>
                        <p className="text-xs font-sans text-bone/90">{entry.details}</p>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </Card>
    </div>
  )
}
