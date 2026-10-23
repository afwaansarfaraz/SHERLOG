import React, { useState } from "react"
import {
  X,
  Server,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Copy,
  Check,
  Terminal,
  Shield,
  Radio,
} from "lucide-react"
import { Button } from "../common/Button"
import { Badge } from "../common/Badge"
import { api } from "../../lib/api"

export interface ApplicationData {
  id: string
  name: string
  service_name: string
  environment: string
  integration_type: string
  endpoint_url: string | null
  telemetry_config: Record<string, any>
  status: string
  last_checked_at: string | null
  last_success_at: string | null
  last_error: string | null
  created_at: string
  updated_at: string
  instrumentation_instructions?: Record<string, any>
}

interface ConnectApplicationModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (app: ApplicationData) => void
}

export const ConnectApplicationModal: React.FC<ConnectApplicationModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [name, setName] = useState("")
  const [serviceName, setServiceName] = useState("")
  const [serviceNameTouched, setServiceNameTouched] = useState(false)
  const [environment, setEnvironment] = useState("production")
  const [integrationType, setIntegrationType] = useState("opentelemetry")
  const [endpointUrl, setEndpointUrl] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Post-registration test state
  const [registeredApp, setRegisteredApp] = useState<ApplicationData | null>(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{
    status: string
    is_connected: boolean
    latency_ms?: number
    http_status?: number
    observable_telemetry_detected: boolean
    telemetry_summary?: { prometheus_series: number; loki_logs: number; jaeger_traces: boolean }
    message: string
    error?: string | null
  } | null>(null)

  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  const resetState = () => {
    setName("")
    setServiceName("")
    setServiceNameTouched(false)
    setEnvironment("production")
    setIntegrationType("opentelemetry")
    setEndpointUrl("")
    setSubmitting(false)
    setError(null)
    setRegisteredApp(null)
    setTesting(false)
    setTestResult(null)
    setCopiedKey(null)
  }

  const handleClose = () => {
    resetState()
    onClose()
  }

  React.useEffect(() => {
    if (!isOpen) {
      resetState()
    }
  }, [isOpen])

  if (!isOpen) return null

  const getPrometheusConfigSnippet = (app: ApplicationData): string => {
    let host = "localhost:8000"
    if (app.endpoint_url) {
      try {
        const parsed = new URL(app.endpoint_url)
        host = parsed.host || "localhost:8000"
      } catch {
        host = "localhost:8000"
      }
    }
    return `- job_name: '${app.service_name}'\n  metrics_path: '/metrics'\n  static_configs:\n    - targets: ['${host}']\n      labels:\n        service: '${app.service_name}'\n        environment: '${app.environment}'`
  }

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      const payload = {
        name: name.trim(),
        service_name: serviceName.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "-"),
        environment,
        integration_type: integrationType,
        endpoint_url: endpointUrl.trim() || null,
        telemetry_config: {},
      }

      const res = await api.post<ApplicationData>("/api/applications", payload)
      setRegisteredApp(res)
      onSuccess(res)
    } catch (err: any) {
      setError(err?.message || "Failed to register application.")
    } finally {
      setSubmitting(false)
    }
  }

  const handleTestConnection = async () => {
    if (!registeredApp) return
    setTesting(true)
    setError(null)
    setTestResult(null)

    try {
      const result = await api.post<any>(`/api/applications/${registeredApp.id}/test-connection`)
      setTestResult(result)
      setRegisteredApp((prev) => (prev ? { ...prev, status: result.status } : null))
    } catch (err: any) {
      setError(err?.message || "Connection test failed.")
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/80 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-2xl bg-soot border border-ash/80 rounded-xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-ash/50 bg-ink/40">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded bg-amber/10 border border-amber/20 text-amber">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-bone">Connect Application to Sherlog</h3>
              <p className="text-xs text-dust">
                Instrument your microservice or backend to stream telemetry and enable automated root-cause investigations.
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg text-dust hover:text-bone hover:bg-ash/40 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">
          {error && (
            <div className="p-3 rounded-lg bg-[#2E1618] border border-[#572124] text-vermilion text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!registeredApp ? (
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-bone mb-1">
                    Application Name <span className="text-vermilion">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Billing Service"
                    value={name}
                    onChange={(e) => {
                      const val = e.target.value
                      setName(val)
                      if (!serviceNameTouched) {
                        setServiceName(val.toLowerCase().replace(/[^a-z0-9_-]/g, "-"))
                      }
                    }}
                    className="w-full px-3 py-2 bg-ink border border-ash rounded-lg text-xs text-bone focus:border-amber focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-bone mb-1">
                    Service Name (Telemetry Identifier) <span className="text-vermilion">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. billing"
                    value={serviceName}
                    onChange={(e) => {
                      setServiceName(e.target.value)
                      setServiceNameTouched(true)
                    }}
                    className="w-full px-3 py-2 bg-ink border border-ash rounded-lg text-xs text-bone font-mono focus:border-amber focus:outline-none"
                  />
                  <p className="text-[10px] text-dust mt-1">
                    Must match the OTel <code>service.name</code> or Prometheus <code>service</code> label.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-bone mb-1">Environment</label>
                  <select
                    value={environment}
                    onChange={(e) => setEnvironment(e.target.value)}
                    className="w-full px-3 py-2 bg-ink border border-ash rounded-lg text-xs text-bone focus:border-amber focus:outline-none"
                  >
                    <option value="production">Production</option>
                    <option value="staging">Staging</option>
                    <option value="development">Development</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-bone mb-1">Integration Type</label>
                  <select
                    value={integrationType}
                    onChange={(e) => setIntegrationType(e.target.value)}
                    className="w-full px-3 py-2 bg-ink border border-ash rounded-lg text-xs text-bone focus:border-amber focus:outline-none"
                  >
                    <option value="opentelemetry">OpenTelemetry (OTLP gRPC/HTTP)</option>
                    <option value="prometheus">Prometheus Metrics Scrape</option>
                    <option value="health_probe">HTTP Health & Latency Probe</option>
                    <option value="custom">Custom Webhook / Multi-telemetry</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-bone mb-1">
                  Health Check / Service Endpoint URL (Optional)
                </label>
                <input
                  type="url"
                  placeholder="http://localhost:8080/health or http://host.docker.internal:8000/health"
                  value={endpointUrl}
                  onChange={(e) => setEndpointUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-ink border border-ash rounded-lg text-xs text-bone font-mono focus:border-amber focus:outline-none"
                />
                <p className="text-[10px] text-dust mt-1">
                  Used by Sherlog to run active availability health probes and measure HTTP round-trip latency.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-ink/40 border border-ash/40 space-y-1.5 text-xs text-dust">
                <div className="flex items-center gap-1.5 text-bone font-medium">
                  <Shield className="w-3.5 h-3.5 text-amber" />
                  <span>Telemetry Security &amp; Isolation</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  Sherlog connects directly to existing local OpenTelemetry Collectors (port 4317/4318), Prometheus (9090), and Loki (3100). No secrets or credentials are saved or transmitted in plain text.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button variant="ghost" size="sm" type="button" onClick={handleClose}>
                  Cancel
                </Button>
                <Button variant="default" size="sm" type="submit" disabled={submitting}>
                  {submitting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                      Registering Application…
                    </>
                  ) : (
                    "Register Application"
                  )}
                </Button>
              </div>
            </form>
          ) : (
            <div className="space-y-5 animate-fade-in">
              {/* Registration Success Banner */}
              <div className="p-3.5 rounded-lg bg-[#162722] border border-[#234A3E] flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-verdigris">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>Application <strong>{registeredApp.name}</strong> registered successfully!</span>
                </div>
                <Badge variant="awaiting_approval" withDot>{registeredApp.status}</Badge>
              </div>

              {/* Real Connection Verification Action */}
              <div className="p-4 rounded-lg bg-ink border border-ash/60 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-xs font-semibold text-bone flex items-center gap-1.5">
                      <Radio className="w-3.5 h-3.5 text-amber" />
                      Live Connection &amp; Telemetry Test
                    </h4>
                    <p className="text-[11px] text-dust mt-0.5">
                      Executes an active health probe and queries Prometheus, Loki, and Jaeger for observable traces.
                    </p>
                  </div>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleTestConnection}
                    disabled={testing}
                  >
                    {testing ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                        Testing Connection…
                      </>
                    ) : (
                      "Test Connection"
                    )}
                  </Button>
                </div>

                {testResult && (
                  <div
                    className={`p-3 rounded border text-xs space-y-2 ${
                      testResult.is_connected
                        ? "bg-[#162722] border-[#234A3E] text-bone"
                        : "bg-[#2E1618] border-[#572124] text-bone"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs flex items-center gap-1.5">
                        {testResult.is_connected ? (
                          <CheckCircle2 className="w-4 h-4 text-verdigris" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-vermilion" />
                        )}
                        {testResult.message}
                      </span>
                      <Badge variant={testResult.status === "ACTIVE_TELEMETRY" ? "resolved" : testResult.is_connected ? "investigating" : "critical"}>
                        {testResult.status}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-ash/40 font-mono text-[11px] text-dust">
                      <div>
                        Latency: <span className="text-bone">{testResult.latency_ms ? `${testResult.latency_ms} ms` : "N/A"}</span>
                      </div>
                      <div>
                        HTTP Probe: <span className="text-bone">{testResult.http_status ? `${testResult.http_status} OK` : "N/A"}</span>
                      </div>
                      <div>
                        Metric Series: <span className="text-bone">{testResult.telemetry_summary?.prometheus_series ?? 0}</span>
                      </div>
                      <div>
                        Jaeger Traces: <span className="text-bone">{testResult.telemetry_summary?.jaeger_traces ? "Detected" : "None"}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Instrumentation Instructions */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-bone flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-dust" />
                    How to Instrument This Application
                  </h4>
                  <span className="text-[10px] font-mono text-dust">service.name = {registeredApp.service_name}</span>
                </div>

                {registeredApp.integration_type === "opentelemetry" && (
                  <div className="space-y-2">
                    <p className="text-[11px] text-dust">
                      Set the standard OpenTelemetry environment variables in your application container or deployment:
                    </p>
                    <div className="p-3 rounded bg-ink/90 border border-ash/60 font-mono text-xs text-bone/90 relative">
                      <pre className="overflow-x-auto whitespace-pre leading-relaxed">
{`OTEL_SERVICE_NAME=${registeredApp.service_name}
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_TRACES_SAMPLER=always_on`}
                      </pre>
                      <button
                        onClick={() =>
                          handleCopy(
                            `OTEL_SERVICE_NAME=${registeredApp.service_name}\nOTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318\nOTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf\nOTEL_TRACES_SAMPLER=always_on`,
                            "env"
                          )
                        }
                        className="absolute top-2 right-2 p-1.5 rounded bg-soot hover:bg-ash text-dust hover:text-bone transition-colors"
                      >
                        {copiedKey === "env" ? <Check className="w-3.5 h-3.5 text-verdigris" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                )}

                {registeredApp.integration_type === "prometheus" && (() => {
                  const promSnippet = getPrometheusConfigSnippet(registeredApp)
                  return (
                    <div className="space-y-2">
                      <p className="text-[11px] text-dust">
                        Add a scrape job to Prometheus configuration (<code>prometheus/prometheus.yml</code>):
                      </p>
                      <div className="p-3 rounded bg-ink/90 border border-ash/60 font-mono text-xs text-bone/90 relative">
                        <pre className="overflow-x-auto whitespace-pre leading-relaxed">
                          {promSnippet}
                        </pre>
                        <button
                          onClick={() => handleCopy(promSnippet, "prom")}
                          className="absolute top-2 right-2 p-1.5 rounded bg-soot hover:bg-ash text-dust hover:text-bone transition-colors"
                        >
                          {copiedKey === "prom" ? <Check className="w-3.5 h-3.5 text-verdigris" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>
                  )
                })()}

                {registeredApp.integration_type === "health_probe" && (
                  <p className="text-[11px] text-dust leading-relaxed">
                    Sherlog periodically sends HTTP GET requests to <code>{registeredApp.endpoint_url}</code> to record availability, response codes, and round-trip latency.
                  </p>
                )}
              </div>

              <div className="flex justify-end pt-2">
                <Button variant="default" size="sm" onClick={handleClose}>
                  Done
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
