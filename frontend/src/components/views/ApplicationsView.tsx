import React, { useState, useEffect, useCallback } from "react"
import {
  Server,
  Plus,
  RefreshCw,
  Radio,
  CheckCircle2,
  AlertCircle,
  Clock,
  Code2,
  Trash2,
  Loader2,
  ArrowLeft,
} from "lucide-react"
import { Card } from "../common/Card"
import { Badge } from "../common/Badge"
import { Button } from "../common/Button"
import { EmptyState } from "../common/EmptyState"
import { ConnectApplicationModal } from "../applications/ConnectApplicationModal"
import type { ApplicationData } from "../applications/ConnectApplicationModal"
import { api } from "../../lib/api"

interface ApplicationsViewProps {
  onBackToOverview: () => void
}

export const ApplicationsView: React.FC<ApplicationsViewProps> = ({ onBackToOverview }) => {
  const [applications, setApplications] = useState<ApplicationData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Modal state
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false)
  const [selectedAppForGuide, setSelectedAppForGuide] = useState<ApplicationData | null>(null)

  // Testing connection state per app
  const [testingAppId, setTestingAppId] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, any>>({})

  // Deleting app state
  const [deletingAppId, setDeletingAppId] = useState<string | null>(null)

  const fetchApplications = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<ApplicationData[]>("/api/applications")
      setApplications(data)
    } catch (err: any) {
      setError(err?.message || "Failed to load registered applications.")
      setApplications([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchApplications()
  }, [fetchApplications])

  const handleTestConnection = async (appId: string) => {
    setTestingAppId(appId)
    try {
      const result = await api.post<any>(`/api/applications/${appId}/test-connection`)
      setTestResults((prev) => ({ ...prev, [appId]: result }))
      // Update local application status
      setApplications((prev) =>
        prev.map((app) =>
          app.id === appId
            ? {
                ...app,
                status: result.status,
                last_checked_at: result.tested_at,
                last_success_at: result.is_connected ? result.tested_at : app.last_success_at,
                last_error: result.error,
              }
            : app
        )
      )
    } catch (err: any) {
      setTestResults((prev) => ({
        ...prev,
        [appId]: {
          status: "DISCONNECTED",
          is_connected: false,
          message: err?.message || "Connection probe failed.",
        },
      }))
    } finally {
      setTestingAppId(null)
    }
  }

  const handleDeleteApplication = async (appId: string) => {
    if (!window.confirm("Are you sure you want to unregister this application from Sherlog?")) {
      return
    }
    setDeletingAppId(appId)
    try {
      await api.delete(`/api/applications/${appId}`)
      setApplications((prev) => prev.filter((a) => a.id !== appId))
    } catch (err: any) {
      alert(err?.message || "Failed to unregister application.")
    } finally {
      setDeletingAppId(null)
    }
  }

  // Count metrics
  const totalApps = applications.length
  const activeTelemetryCount = applications.filter((a) => a.status === "ACTIVE_TELEMETRY").length
  const connectedCount = applications.filter(
    (a) => a.status === "CONNECTED" || a.status === "ACTIVE_TELEMETRY"
  ).length
  const configuredCount = applications.filter((a) => a.status === "CONFIGURED").length

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBackToOverview}>
            <ArrowLeft className="w-4 h-4 mr-1" /> Overview
          </Button>
          <div>
            <h2 className="text-xl font-semibold text-bone">Monitored Services &amp; Applications</h2>
            <p className="text-xs text-dust">
              Register and connect external microservices to stream OpenTelemetry traces, Prometheus metrics, and Loki logs.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={fetchApplications} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 mr-1 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={() => setIsConnectModalOpen(true)}
            className="shadow-sm"
          >
            <Plus className="w-3.5 h-3.5 mr-1" /> Connect Application
          </Button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg bg-soot/80 border border-ash">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-dust">Registered Apps</span>
            <Server className="w-4 h-4 text-bone/70" />
          </div>
          <div className="mt-2 text-2xl font-semibold text-bone font-mono">{totalApps}</div>
          <p className="mt-1 text-[11px] text-dust">Total inventory of monitored services.</p>
        </div>

        <div className="p-4 rounded-lg bg-soot/80 border border-verdigris/40">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-verdigris">Active Telemetry</span>
            <Radio className="w-4 h-4 text-verdigris animate-pulse" />
          </div>
          <div className="mt-2 text-2xl font-semibold text-verdigris font-mono">{activeTelemetryCount}</div>
          <p className="mt-1 text-[11px] text-dust">Emitting observable metrics or traces.</p>
        </div>

        <div className="p-4 rounded-lg bg-soot/80 border border-amber/40">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-amber">Connected / Probed</span>
            <CheckCircle2 className="w-4 h-4 text-amber" />
          </div>
          <div className="mt-2 text-2xl font-semibold text-amber font-mono">{connectedCount}</div>
          <p className="mt-1 text-[11px] text-dust">Passing HTTP health checks.</p>
        </div>

        <div className="p-4 rounded-lg bg-soot/80 border border-ash">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-dust">Configured Only</span>
            <Clock className="w-4 h-4 text-dust" />
          </div>
          <div className="mt-2 text-2xl font-semibold text-dust font-mono">{configuredCount}</div>
          <p className="mt-1 text-[11px] text-dust">Awaiting first telemetry emit.</p>
        </div>
      </div>

      {/* Error State */}
      {error && !loading && (
        <div className="flex items-center gap-2 px-3 py-2 rounded bg-[#2E1618] border border-[#572124] text-vermilion text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={fetchApplications} className="ml-auto">
            Retry
          </Button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <Card className="p-8 flex flex-col items-center justify-center text-center space-y-3 min-h-[200px]">
          <Loader2 className="w-8 h-8 text-amber animate-spin" />
          <p className="text-xs text-dust">Loading application inventory…</p>
        </Card>
      )}

      {/* Empty State */}
      {!loading && applications.length === 0 && !error && (
        <EmptyState
          variant="custom"
          icon={Server}
          title="No Applications Connected"
          description="Connect your first application or microservice to Sherlog to ingest telemetry, monitor health, and automate incident root-cause investigations."
          actionLabel="Connect Application"
          onAction={() => setIsConnectModalOpen(true)}
        />
      )}

      {/* Application Grid */}
      {!loading && applications.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {applications.map((app) => {
            const isTesting = testingAppId === app.id
            const isDeleting = deletingAppId === app.id
            const result = testResults[app.id]

            return (
              <Card key={app.id} className="p-5 space-y-4 hover:border-ash/80 transition-colors">
                {/* Header Row */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-ink border border-ash flex items-center justify-center shrink-0">
                      <Server className="w-4 h-4 text-amber" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-bone text-sm">{app.name}</h3>
                        <Badge variant="slate">{app.environment}</Badge>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 font-mono text-[11px] text-dust">
                        <span>service: {app.service_name}</span>
                        <span>•</span>
                        <span className="capitalize">{app.integration_type}</span>
                      </div>
                    </div>
                  </div>

                  {/* Status Badge */}
                  <div>
                    {app.status === "ACTIVE_TELEMETRY" && (
                      <Badge variant="resolved" withDot>
                        ACTIVE TELEMETRY
                      </Badge>
                    )}
                    {app.status === "CONNECTED" && (
                      <Badge variant="investigating" withDot>
                        CONNECTED
                      </Badge>
                    )}
                    {app.status === "CONFIGURED" && (
                      <Badge variant="awaiting_approval" withDot>
                        CONFIGURED
                      </Badge>
                    )}
                    {app.status === "DISCONNECTED" && (
                      <Badge variant="critical" withDot>
                        DISCONNECTED
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Details Section */}
                <div className="space-y-2 text-xs text-dust font-mono bg-ink/50 p-3 rounded-lg border border-ash/40">
                  <div className="flex items-center justify-between">
                    <span className="text-dust/80">HEALTH ENDPOINT:</span>
                    <span className="text-bone truncate max-w-[240px]">
                      {app.endpoint_url || "None (Telemetry Only)"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-dust/80">LAST CHECKED:</span>
                    <span className="text-bone">
                      {app.last_checked_at
                        ? new Date(app.last_checked_at).toLocaleTimeString()
                        : "Never"}
                    </span>
                  </div>
                  {app.last_error && (
                    <div className="text-vermilion text-[11px] pt-1 border-t border-ash/40">
                      Error: {app.last_error}
                    </div>
                  )}
                </div>

                {/* Live Test Connection Result Banner */}
                {result && (
                  <div
                    className={`p-2.5 rounded text-xs space-y-1 ${
                      result.is_connected
                        ? "bg-[#162722] border border-[#234A3E] text-bone"
                        : "bg-[#2E1618] border border-[#572124] text-bone"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-[11px] flex items-center gap-1.5">
                        {result.is_connected ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-verdigris" />
                        ) : (
                          <AlertCircle className="w-3.5 h-3.5 text-vermilion" />
                        )}
                        {result.message}
                      </span>
                      {result.latency_ms && (
                        <span className="font-mono text-[10px] text-dust">
                          {result.latency_ms} ms
                        </span>
                      )}
                    </div>
                    {result.telemetry_summary && (
                      <div className="flex flex-wrap gap-x-3 gap-y-1 border-t border-ash/40 pt-1 font-mono text-[10px] text-dust">
                        {result.http_status != null && <span>Health HTTP: {result.http_status}</span>}
                        <span>Prometheus: {result.telemetry_summary.prometheus_series ?? 0} series</span>
                        <span>Loki: {result.telemetry_summary.loki_logs ?? 0} logs</span>
                        <span>Jaeger: {result.telemetry_summary.jaeger_traces ? "service detected" : "no service detected"}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex items-center justify-between pt-2 border-t border-ash/50">
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleTestConnection(app.id)}
                      disabled={isTesting}
                      className="text-xs"
                    >
                      {isTesting ? (
                        <>
                          <Loader2 className="w-3 h-3 mr-1 animate-spin" /> Testing…
                        </>
                      ) : (
                        <>
                          <Radio className="w-3 h-3 mr-1 text-amber" /> Test Connection
                        </>
                      )}
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedAppForGuide(app)}
                      className="text-xs"
                    >
                      <Code2 className="w-3 h-3 mr-1" /> Instrumentation Guide
                    </Button>
                  </div>

                  {!["app-api-gateway", "app-orders-service", "app-payments-service"].includes(
                    app.id
                  ) && (
                    <button
                      onClick={() => handleDeleteApplication(app.id)}
                      disabled={isDeleting}
                      title="Unregister application"
                      className="p-1.5 rounded text-dust hover:text-vermilion hover:bg-[#2E1618] transition-colors"
                    >
                      {isDeleting ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="w-3.5 h-3.5" />
                      )}
                    </button>
                  )}
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* Connect Application Modal */}
      <ConnectApplicationModal
        isOpen={isConnectModalOpen}
        onClose={() => setIsConnectModalOpen(false)}
        onSuccess={(newApp) => {
          setApplications((prev) => [newApp, ...prev.filter((a) => a.id !== newApp.id)])
        }}
      />

      {/* Instrumentation Guide Modal */}
      {selectedAppForGuide && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-xl bg-soot border border-ash/80 rounded-xl shadow-2xl overflow-hidden p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-ash/50 pb-3">
              <div className="flex items-center gap-2">
                <Code2 className="w-4 h-4 text-amber" />
                <h3 className="font-semibold text-bone text-sm">
                  Instrumentation: {selectedAppForGuide.name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedAppForGuide(null)}
                className="text-dust hover:text-bone"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs text-dust">
              <p>
                To enable automated Sherlog root-cause investigations for{" "}
                <strong>{selectedAppForGuide.name}</strong>, set the following environment variables
                so traces and metrics stream to Sherlog&apos;s OpenTelemetry Collector:
              </p>
              <div className="p-3 rounded bg-ink border border-ash font-mono text-bone/90 space-y-1">
                <div>OTEL_SERVICE_NAME={selectedAppForGuide.service_name}</div>
                <div>OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318</div>
                <div>OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf</div>
                <div>OTEL_TRACES_SAMPLER=always_on</div>
              </div>

              <div className="p-3 rounded bg-ink/40 border border-ash/40 text-[11px] leading-relaxed">
                <strong>Verification Tip:</strong> Once configured, invoke any endpoint on your
                service, then return to Sherlog and click <strong>Test Connection</strong>. Sherlog
                will query Prometheus and Jaeger to confirm active telemetry arrival.
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button
                variant="default"
                size="sm"
                onClick={() => setSelectedAppForGuide(null)}
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
