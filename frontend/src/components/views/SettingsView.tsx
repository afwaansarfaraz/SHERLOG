import React, { useState, useEffect, useCallback } from "react"
import {
  Settings,
  Database,
  Activity,
  Cpu,
  BookOpen,
  ShieldAlert,
  AlertTriangle,
  RefreshCw,
  ArrowLeft,
  Server,
  Lock,
  Layers,
  Clock,
} from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import { Badge } from "../common/Badge"
import { Button } from "../common/Button"
import { api, ApiClientError } from "../../lib/api"

interface ServiceStatus {
  name: string
  category: string
  status: string
  is_connected: boolean
  endpoint?: string
  latency_ms?: number
  details?: Record<string, unknown>
  error?: string
}

interface PlatformSettingsData {
  app_name: string
  environment: string
  timestamp: string
  services: Record<string, ServiceStatus>
  llm: {
    provider: string
    model: string
    is_configured: boolean
    api_key_masked: string | null
    timeout_seconds: number
    temperature: number
    max_retries: number
  }
  rag: {
    enabled: boolean
    embedding_provider: string
    embedding_model: string
    top_k: number
    similarity_threshold: number
    indexed_documents_count: number
    indexed_chunks_count: number
  }
  budget_guards: {
    max_steps: number
    max_llm_calls: number
    max_tool_calls: number
    max_evidence_items: number
    max_tokens: number
    max_seconds: number
  }
  security: {
    alertmanager_webhook_configured: boolean
    alertmanager_webhook_secret_masked: string | null
    webhook_endpoint: string
    oauth_status: string
    oauth_details: string
  }
}

interface SettingsViewProps {
  onBackToOverview: () => void
}

export const SettingsView: React.FC<SettingsViewProps> = ({ onBackToOverview }) => {
  const [settingsData, setSettingsData] = useState<PlatformSettingsData | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false)

  const fetchSettings = useCallback(async () => {
    try {
      setError(null)
      const data = await api.get<PlatformSettingsData>("/api/settings/status")
      setSettingsData(data)
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message)
      } else {
        setError("Failed to query platform settings and integration health.")
      }
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [])

  useEffect(() => {
    fetchSettings()
  }, [fetchSettings])

  const handleRefresh = () => {
    setIsRefreshing(true)
    fetchSettings()
  }

  const renderStatusBadge = (status: string, isConnected: boolean) => {
    if (isConnected || status === "connected") {
      return (
        <Badge variant="healthy" withDot className="font-mono text-[11px]">
          CONNECTED
        </Badge>
      )
    }
    if (status === "configured") {
      return (
        <Badge variant="slate" withDot className="font-mono text-[11px]">
          CONFIGURED
        </Badge>
      )
    }
    if (status === "unhealthy" || status === "unreachable") {
      return (
        <Badge variant="critical" withDot className="font-mono text-[11px]">
          UNREACHABLE
        </Badge>
      )
    }
    if (status === "not_implemented") {
      return (
        <Badge variant="default" className="font-mono text-[11px]">
          NOT IMPLEMENTED
        </Badge>
      )
    }
    return (
      <Badge variant="default" className="font-mono text-[11px]">
        {status.toUpperCase()}
      </Badge>
    )
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBackToOverview}>
            <ArrowLeft className="w-4 h-4 mr-1" /> Overview
          </Button>
          <div>
            <h2 className="text-xl font-semibold text-bone flex items-center gap-2">
              <Settings className="w-5 h-5 text-amber" />
              Platform Settings &amp; Credentials
            </h2>
            <p className="text-xs text-dust mt-0.5">
              Live connectivity checks, masked credentials, observability backends, and investigation budget boundaries.
            </p>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isLoading || isRefreshing}
          className="flex items-center gap-1.5 shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          Test Connections
        </Button>
      </div>

      {/* Error state */}
      {error && (
        <Card className="p-4 bg-vermilion/10 border-vermilion/40 text-vermilion space-y-2">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Settings Diagnostics Error</span>
          </div>
          <p className="text-xs text-bone/90">{error}</p>
          <Button variant="outline" size="sm" onClick={handleRefresh} className="mt-2 text-xs">
            Retry Connectivity Check
          </Button>
        </Card>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="p-6 space-y-4 animate-pulse">
              <div className="h-4 bg-ash/40 rounded w-1/3" />
              <div className="h-8 bg-ash/20 rounded" />
              <div className="h-8 bg-ash/20 rounded" />
            </Card>
          ))}
        </div>
      ) : settingsData ? (
        <div className="space-y-6">
          {/* Section 1: Core Datastores & Message Brokers */}
          <Card className="p-4 space-y-4">
            <CardHeader className="p-0 pb-3 border-b border-ash/60">
              <CardTitle className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-verdigris" />
                  <span>Primary Datastores &amp; Message Brokers</span>
                </div>
                <span className="text-[11px] font-mono text-dust">
                  Environment: {settingsData.environment}
                </span>
              </CardTitle>
            </CardHeader>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* PostgreSQL */}
              {settingsData.services.postgres && (
                <div className="p-3.5 rounded bg-obsidian border border-ash/60 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-bone flex items-center gap-1.5">
                      <Server className="w-4 h-4 text-dust" /> PostgreSQL Persistence
                    </span>
                    {renderStatusBadge(
                      settingsData.services.postgres.status,
                      settingsData.services.postgres.is_connected
                    )}
                  </div>
                  <div className="text-xs font-mono text-dust space-y-1">
                    <div className="truncate">
                      Endpoint: <span className="text-bone">{settingsData.services.postgres.endpoint}</span>
                    </div>
                    {settingsData.services.postgres.latency_ms !== undefined && (
                      <div>
                        Roundtrip Ping:{" "}
                        <span className="text-verdigris font-semibold">
                          {settingsData.services.postgres.latency_ms} ms
                        </span>
                      </div>
                    )}
                    {settingsData.services.postgres.details && (
                      <div className="text-[11px] text-dust/80">
                        Pool: {String(settingsData.services.postgres.details.pool_size || 10)} | Max Overflow:{" "}
                        {String(settingsData.services.postgres.details.max_overflow || 20)}
                      </div>
                    )}
                    {settingsData.services.postgres.error && (
                      <div className="text-vermilion text-[11px]">{settingsData.services.postgres.error}</div>
                    )}
                  </div>
                </div>
              )}

              {/* Redis */}
              {settingsData.services.redis && (
                <div className="p-3.5 rounded bg-obsidian border border-ash/60 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-bone flex items-center gap-1.5">
                      <Layers className="w-4 h-4 text-dust" /> Redis Streams &amp; Queue
                    </span>
                    {renderStatusBadge(
                      settingsData.services.redis.status,
                      settingsData.services.redis.is_connected
                    )}
                  </div>
                  <div className="text-xs font-mono text-dust space-y-1">
                    <div className="truncate">
                      Endpoint: <span className="text-bone">{settingsData.services.redis.endpoint}</span>
                    </div>
                    {settingsData.services.redis.latency_ms !== undefined && (
                      <div>
                        Roundtrip Ping:{" "}
                        <span className="text-verdigris font-semibold">
                          {settingsData.services.redis.latency_ms} ms
                        </span>
                      </div>
                    )}
                    {settingsData.services.redis.details && (
                      <div className="text-[11px] text-dust/80 truncate">
                        Stream: {String(settingsData.services.redis.details.stream_name || "N/A")}
                      </div>
                    )}
                    {settingsData.services.redis.error && (
                      <div className="text-vermilion text-[11px]">{settingsData.services.redis.error}</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Section 2: Observability & Telemetry Infrastructure */}
          <Card className="p-4 space-y-4">
            <CardHeader className="p-0 pb-3 border-b border-ash/60">
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-amber" />
                <span>Observability &amp; Telemetry Backends</span>
              </CardTitle>
            </CardHeader>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {/* Prometheus */}
              {settingsData.services.prometheus && (
                <div className="p-3 rounded bg-obsidian border border-ash/60 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-bone">Prometheus Metrics</span>
                    {renderStatusBadge(
                      settingsData.services.prometheus.status,
                      settingsData.services.prometheus.is_connected
                    )}
                  </div>
                  <div className="text-[11px] font-mono text-dust truncate">
                    {settingsData.services.prometheus.endpoint}
                  </div>
                  {settingsData.services.prometheus.latency_ms && (
                    <div className="text-[10px] font-mono text-dust/80">
                      Latency: {settingsData.services.prometheus.latency_ms} ms
                    </div>
                  )}
                  {settingsData.services.prometheus.error && (
                    <div className="text-[10px] text-vermilion">{settingsData.services.prometheus.error}</div>
                  )}
                </div>
              )}

              {/* Loki */}
              {settingsData.services.loki && (
                <div className="p-3 rounded bg-obsidian border border-ash/60 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-bone">Loki Log Aggregator</span>
                    {renderStatusBadge(
                      settingsData.services.loki.status,
                      settingsData.services.loki.is_connected
                    )}
                  </div>
                  <div className="text-[11px] font-mono text-dust truncate">
                    {settingsData.services.loki.endpoint}
                  </div>
                  {settingsData.services.loki.latency_ms && (
                    <div className="text-[10px] font-mono text-dust/80">
                      Latency: {settingsData.services.loki.latency_ms} ms
                    </div>
                  )}
                  {settingsData.services.loki.error && (
                    <div className="text-[10px] text-vermilion">{settingsData.services.loki.error}</div>
                  )}
                </div>
              )}

              {/* Jaeger */}
              {settingsData.services.jaeger && (
                <div className="p-3 rounded bg-obsidian border border-ash/60 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-bone">Jaeger Distributed Tracing</span>
                    {renderStatusBadge(
                      settingsData.services.jaeger.status,
                      settingsData.services.jaeger.is_connected
                    )}
                  </div>
                  <div className="text-[11px] font-mono text-dust truncate">
                    {settingsData.services.jaeger.endpoint}
                  </div>
                  {settingsData.services.jaeger.latency_ms && (
                    <div className="text-[10px] font-mono text-dust/80">
                      Latency: {settingsData.services.jaeger.latency_ms} ms
                    </div>
                  )}
                  {settingsData.services.jaeger.error && (
                    <div className="text-[10px] text-vermilion">{settingsData.services.jaeger.error}</div>
                  )}
                </div>
              )}
            </div>
          </Card>

          {/* Section 3: AI Investigation Model & RAG */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* LLM Provider */}
            <Card className="p-4 space-y-3">
              <CardHeader className="p-0 pb-2 border-b border-ash/60">
                <CardTitle className="flex items-center justify-between w-full">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-jade" />
                    <span>AI &amp; LLM Provider</span>
                  </div>
                  <Badge variant={settingsData.llm.is_configured ? "healthy" : "critical"}>
                    {settingsData.llm.is_configured ? "CONFIGURED" : "MISSING KEY"}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-ash/30">
                  <span className="text-dust">Provider:</span>
                  <span className="text-bone uppercase">{settingsData.llm.provider}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-ash/30">
                  <span className="text-dust">Active Model:</span>
                  <span className="text-amber">{settingsData.llm.model}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-ash/30">
                  <span className="text-dust">API Key:</span>
                  <span className="text-bone">
                    {settingsData.llm.api_key_masked || "None (Fallback Mode)"}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-ash/30">
                  <span className="text-dust">Timeout &amp; Temperature:</span>
                  <span className="text-bone">
                    {settingsData.llm.timeout_seconds}s | {settingsData.llm.temperature}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-dust">Max Retries:</span>
                  <span className="text-bone">{settingsData.llm.max_retries} attempts</span>
                </div>
              </div>
            </Card>

            {/* RAG Knowledge Retrieval */}
            <Card className="p-4 space-y-3">
              <CardHeader className="p-0 pb-2 border-b border-ash/60">
                <CardTitle className="flex items-center justify-between w-full">
                  <div className="flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-amber" />
                    <span>RAG &amp; Vector Knowledge Base</span>
                  </div>
                  <Badge variant={settingsData.rag.enabled ? "healthy" : "slate"}>
                    {settingsData.rag.enabled ? "ACTIVE" : "DISABLED"}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-ash/30">
                  <span className="text-dust">Embedding Engine:</span>
                  <span className="text-bone">{settingsData.rag.embedding_provider}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-ash/30">
                  <span className="text-dust">Model Name:</span>
                  <span className="text-bone">{settingsData.rag.embedding_model}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-ash/30">
                  <span className="text-dust">Retrieval Parameters:</span>
                  <span className="text-bone">
                    Top-{settingsData.rag.top_k} | Min Cosine {settingsData.rag.similarity_threshold}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-dust">Indexed Corpus:</span>
                  <span className="text-jade font-semibold">
                    {settingsData.rag.indexed_documents_count} docs ({settingsData.rag.indexed_chunks_count} chunks)
                  </span>
                </div>
              </div>
            </Card>
          </div>

          {/* Section 4: Investigation Execution Budget Guardrails */}
          <Card className="p-4 space-y-4">
            <CardHeader className="p-0 pb-3 border-b border-ash/60">
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber" />
                <span>Investigation Execution Hard Budget Guardrails</span>
              </CardTitle>
            </CardHeader>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 font-mono text-center">
              <div className="p-2.5 rounded bg-obsidian border border-ash/60">
                <span className="text-[10px] text-dust block uppercase">Max Steps</span>
                <span className="text-lg font-bold text-bone mt-0.5 block">
                  {settingsData.budget_guards.max_steps}
                </span>
              </div>
              <div className="p-2.5 rounded bg-obsidian border border-ash/60">
                <span className="text-[10px] text-dust block uppercase">Max LLM Calls</span>
                <span className="text-lg font-bold text-bone mt-0.5 block">
                  {settingsData.budget_guards.max_llm_calls}
                </span>
              </div>
              <div className="p-2.5 rounded bg-obsidian border border-ash/60">
                <span className="text-[10px] text-dust block uppercase">Max Tool Calls</span>
                <span className="text-lg font-bold text-bone mt-0.5 block">
                  {settingsData.budget_guards.max_tool_calls}
                </span>
              </div>
              <div className="p-2.5 rounded bg-obsidian border border-ash/60">
                <span className="text-[10px] text-dust block uppercase">Max Evidence</span>
                <span className="text-lg font-bold text-bone mt-0.5 block">
                  {settingsData.budget_guards.max_evidence_items}
                </span>
              </div>
              <div className="p-2.5 rounded bg-obsidian border border-ash/60">
                <span className="text-[10px] text-dust block uppercase">Token Cap</span>
                <span className="text-lg font-bold text-bone mt-0.5 block">
                  {settingsData.budget_guards.max_tokens.toLocaleString()}
                </span>
              </div>
              <div className="p-2.5 rounded bg-obsidian border border-ash/60">
                <span className="text-[10px] text-dust block uppercase">Timeout</span>
                <span className="text-lg font-bold text-bone mt-0.5 block">
                  {settingsData.budget_guards.max_seconds}s
                </span>
              </div>
            </div>
          </Card>

          {/* Section 5: Security & Ingestion Configuration */}
          <Card className="p-4 space-y-4">
            <CardHeader className="p-0 pb-3 border-b border-ash/60">
              <CardTitle className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-verdigris" />
                <span>Security, Webhooks &amp; Access Controls</span>
              </CardTitle>
            </CardHeader>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
              <div className="p-3.5 rounded bg-obsidian border border-ash/60 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-sans font-medium text-bone">Alertmanager Webhook Auth</span>
                  <Badge
                    variant={
                      settingsData.security.alertmanager_webhook_configured ? "healthy" : "slate"
                    }
                  >
                    {settingsData.security.alertmanager_webhook_configured
                      ? "CONFIGURED"
                      : "OPTIONAL (DEV MODE)"}
                  </Badge>
                </div>
                <div className="text-dust">
                  Shared Secret:{" "}
                  <span className="text-bone">
                    {settingsData.security.alertmanager_webhook_secret_masked || "None (Open ingestion)"}
                  </span>
                </div>
                <div className="text-dust">
                  Endpoint: <span className="text-bone">{settingsData.security.webhook_endpoint}</span>
                </div>
              </div>

              <div className="p-3.5 rounded bg-obsidian border border-ash/60 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-sans font-medium text-bone">Single Sign-On (OAuth 2.0)</span>
                  <Badge variant="default">NOT IMPLEMENTED</Badge>
                </div>
                <p className="text-[11px] font-sans text-dust leading-relaxed">
                  {settingsData.security.oauth_details}
                </p>
              </div>
            </div>

            {/* Immutability notice */}
            <div className="p-3 rounded bg-ink border border-ash/60 text-xs text-dust/90 flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-amber shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-bone">Configuration Immutability Policy:</span> Settings and credentials are read directly from server environment variables (<code className="text-amber">.env</code>) to prevent accidental runtime mutations or browser-side secret exfiltration.
              </div>
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  )
}
