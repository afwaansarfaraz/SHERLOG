import React, { useState } from "react"
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Bell,
  Layers,
  Search,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Bug,
} from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import { Button } from "../common/Button"
import { EmptyState } from "../common/EmptyState"
import {
  IncidentListSkeleton,
  MetricsChartSkeleton,
  LogsViewSkeleton,
  TracesWaterfallSkeleton,
  InvestigationTimelineSkeleton,
} from "../common/Skeletons"
import { ErrorBoundary } from "../common/ErrorBoundary"
import { useToast } from "../../hooks/useToast"
import { useFormValidation, FormFieldError } from "../common/FormValidation"

export const HardeningShowcase: React.FC = () => {
  const { success, error, warning, info } = useToast()
  const [selectedSkeleton, setSelectedSkeleton] = useState<
    "incidents" | "metrics" | "logs" | "traces" | "timeline"
  >("incidents")
  const [selectedEmptyState, setSelectedEmptyState] = useState<
    "no-incidents" | "no-search-results" | "no-telemetry" | "no-evidence"
  >("no-incidents")
  const [shouldCrashWidget, setShouldCrashWidget] = useState(false)

  // Form validation demo state
  const { values, errors, setValue, setFieldTouched, validateAll, reset } = useFormValidation(
    {
      remediationId: "",
      operatorEmail: "",
    },
    {
      remediationId: {
        required: "Remediation ID is required (e.g. REM-001)",
        minLength: { value: 4, message: "ID must be at least 4 characters" },
      },
      operatorEmail: {
        required: "Operator email is required",
        pattern: { regex: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: "Invalid email address format" },
      },
    }
  )

  const handleTestDeduplication = () => {
    // Fire 3 identical toasts rapidly
    error("HikariCP connection pool exhausted (limit: 20)", "Critical Telemetry Alert")
    error("HikariCP connection pool exhausted (limit: 20)", "Critical Telemetry Alert")
    error("HikariCP connection pool exhausted (limit: 20)", "Critical Telemetry Alert")
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="p-6 rounded-xl bg-soot border border-ash/90 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-[#271E14] text-amber border border-[#4A391A] mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Interactive Hardening Showcase</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-semibold text-bone tracking-tight">
            Production-Ready Frontend Hardening Gallery
          </h1>
          <p className="text-xs sm:text-sm text-dust mt-1 max-w-2xl leading-relaxed">
            Preview, test, and inspect all implemented error pages, loading skeletons, semantic empty states,
            accessible toasts, isolated error boundaries, and network banners live in one place.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => (window.location.hash = "overview")}>
            Back to Dashboard
          </Button>
        </div>
      </div>

      {/* 1. Quick Route Navigation: Error Pages */}
      <Card className="p-5 space-y-4">
        <CardHeader className="p-0 pb-3 border-b border-ash/60">
          <CardTitle>
            <ShieldAlert className="w-4 h-4 text-vermilion" />
            <span>1. Error Pages (Direct URL Routes)</span>
          </CardTitle>
        </CardHeader>
        <p className="text-xs text-dust">
          Click any link below to visit the full-page branded error state. Each includes functional recovery actions and zero sensitive stack trace exposure:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 font-mono text-xs">
          <button
            onClick={() => (window.location.hash = "404")}
            className="p-3.5 rounded-lg bg-ink/70 border border-ash hover:border-amber hover:bg-soot text-left transition-all group cursor-pointer"
          >
            <div className="text-amber font-semibold flex items-center justify-between">
              <span>HTTP 404</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
            <div className="text-bone font-medium mt-1">Page Not Found</div>
            <div className="text-[11px] text-dust mt-0.5 font-sans">#404 or unknown hash</div>
          </button>

          <button
            onClick={() => (window.location.hash = "500")}
            className="p-3.5 rounded-lg bg-ink/70 border border-ash hover:border-vermilion hover:bg-soot text-left transition-all group cursor-pointer"
          >
            <div className="text-vermilion font-semibold flex items-center justify-between">
              <span>HTTP 500</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
            <div className="text-bone font-medium mt-1">Server Error</div>
            <div className="text-[11px] text-dust mt-0.5 font-sans">#500 (Correlation ID)</div>
          </button>

          <button
            onClick={() => (window.location.hash = "403")}
            className="p-3.5 rounded-lg bg-ink/70 border border-ash hover:border-amber hover:bg-soot text-left transition-all group cursor-pointer"
          >
            <div className="text-amber font-semibold flex items-center justify-between">
              <span>HTTP 403</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
            <div className="text-bone font-medium mt-1">Access Denied</div>
            <div className="text-[11px] text-dust mt-0.5 font-sans">#403 (No fake auth)</div>
          </button>

          <button
            onClick={() => (window.location.hash = "503")}
            className="p-3.5 rounded-lg bg-ink/70 border border-ash hover:border-amber hover:bg-soot text-left transition-all group cursor-pointer"
          >
            <div className="text-amber font-semibold flex items-center justify-between">
              <span>HTTP 503</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
            <div className="text-bone font-medium mt-1">Service Maintenance</div>
            <div className="text-[11px] text-dust mt-0.5 font-sans">#503 (Maintenance mode)</div>
          </button>
        </div>
      </Card>

      {/* 2. Loading Skeletons Interactive Switcher */}
      <Card className="p-5 space-y-4">
        <CardHeader className="p-0 pb-3 border-b border-ash/60">
          <CardTitle>
            <Layers className="w-4 h-4 text-amber" />
            <span>2. High-Fidelity Loading Skeletons</span>
          </CardTitle>
        </CardHeader>
        <p className="text-xs text-dust">
          Select any telemetry view to inspect its layout skeleton designed to prevent visual jumping during data fetches:
        </p>

        {/* Skeleton Selector Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-ink/80 border border-ash rounded-lg text-xs font-mono">
          {(
            [
              { key: "incidents", label: "Incident List" },
              { key: "metrics", label: "Metrics Charts" },
              { key: "logs", label: "Logs Feed" },
              { key: "traces", label: "Jaeger Waterfall" },
              { key: "timeline", label: "Investigation Stepper" },
            ] as const
          ).map((item) => (
            <button
              key={item.key}
              onClick={() => setSelectedSkeleton(item.key)}
              className={`px-3 py-1.5 rounded transition-colors ${
                selectedSkeleton === item.key
                  ? "bg-soot text-bone border border-ash shadow-sm"
                  : "text-dust hover:text-bone border border-transparent"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Skeleton Container */}
        <div className="p-4 rounded-lg bg-ink/30 border border-ash/60">
          {selectedSkeleton === "incidents" && <IncidentListSkeleton count={3} />}
          {selectedSkeleton === "metrics" && <MetricsChartSkeleton count={2} />}
          {selectedSkeleton === "logs" && <LogsViewSkeleton rowCount={5} />}
          {selectedSkeleton === "traces" && <TracesWaterfallSkeleton spanCount={4} />}
          {selectedSkeleton === "timeline" && <InvestigationTimelineSkeleton count={4} />}
        </div>
      </Card>

      {/* 3. Semantic Empty States */}
      <Card className="p-5 space-y-4">
        <CardHeader className="p-0 pb-3 border-b border-ash/60">
          <CardTitle>
            <Search className="w-4 h-4 text-verdigris" />
            <span>3. Semantic Empty States</span>
          </CardTitle>
        </CardHeader>
        <p className="text-xs text-dust">
          Semantic empty states distinguish normal operation, unmatched search queries, empty telemetry windows, and pending evidence:
        </p>

        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-ink/80 border border-ash rounded-lg text-xs font-mono">
          {(
            [
              { key: "no-incidents", label: "No Incidents (Healthy)" },
              { key: "no-search-results", label: "No Search Results" },
              { key: "no-telemetry", label: "No Telemetry Window" },
              { key: "no-evidence", label: "No Investigation Evidence" },
            ] as const
          ).map((item) => (
            <button
              key={item.key}
              onClick={() => setSelectedEmptyState(item.key)}
              className={`px-3 py-1.5 rounded transition-colors ${
                selectedEmptyState === item.key
                  ? "bg-soot text-bone border border-ash shadow-sm"
                  : "text-dust hover:text-bone border border-transparent"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="p-4 rounded-lg bg-ink/30 border border-ash/60">
          <EmptyState
            variant={selectedEmptyState}
            searchQuery={selectedEmptyState === "no-search-results" ? "orders-api-v2" : undefined}
            actionLabel="Reset Filter"
            onAction={() => setSelectedEmptyState("no-incidents")}
          />
        </div>
      </Card>

      {/* 4. Toast Notifications & Deduplication */}
      <Card className="p-5 space-y-4">
        <CardHeader className="p-0 pb-3 border-b border-ash/60">
          <CardTitle>
            <Bell className="w-4 h-4 text-amber" />
            <span>4. Accessible Toast Notifications &amp; Deduplication</span>
          </CardTitle>
        </CardHeader>
        <p className="text-xs text-dust">
          Trigger live toasts. Notice that clicking the deduplication test 3 times results in a single card with a <code className="text-amber">×3</code> badge instead of 3 stacked spam notifications:
        </p>

        <div className="flex flex-wrap gap-2.5">
          <Button
            variant="verdigris"
            size="sm"
            onClick={() => success("Investigation INC00241 root cause identified", "Diagnosis")}
          >
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
            Trigger Success Toast
          </Button>

          <Button
            variant="oxblood"
            size="sm"
            onClick={() => error("PostgreSQL query execution timed out after 8s", "Database Error")}
          >
            <AlertTriangle className="w-3.5 h-3.5 mr-1" />
            Trigger Error Toast
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => warning("Orders DB connection pool saturation at 95%", "Threshold Warning")}
          >
            Trigger Warning Toast
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => info("Real-time telemetry WebSocket reconnected", "Agent Stream")}
          >
            Trigger Info Toast
          </Button>

          <Button variant="default" size="sm" onClick={handleTestDeduplication}>
            Test Deduplication (Fires 3×)
          </Button>
        </div>
      </Card>

      {/* 5. Error Boundary Widget Isolation */}
      <Card className="p-5 space-y-4">
        <CardHeader className="p-0 pb-3 border-b border-ash/60">
          <CardTitle>
            <Bug className="w-4 h-4 text-vermilion" />
            <span>5. Component-Level Error Boundary Isolation</span>
          </CardTitle>
        </CardHeader>
        <p className="text-xs text-dust">
          Click below to intentionally trigger an unhandled rendering crash in this isolated widget. The boundary catches the error, displays an SRE retry card, and keeps the rest of the application fully working:
        </p>

        <ErrorBoundary
          moduleName="Sample Telemetry Chart"
          onReset={() => setShouldCrashWidget(false)}
        >
          {shouldCrashWidget ? (
            <ExplodingComponent />
          ) : (
            <div className="p-6 rounded-lg bg-ink/70 border border-ash flex items-center justify-between">
              <div className="space-y-1">
                <div className="text-sm font-semibold text-bone">Simulated Telemetry Widget</div>
                <div className="text-xs text-dust">This widget is protected by an isolated ErrorBoundary.</div>
              </div>
              <Button
                variant="oxblood"
                size="sm"
                onClick={() => setShouldCrashWidget(true)}
              >
                <Bug className="w-3.5 h-3.5 mr-1" />
                Simulate Widget Crash
              </Button>
            </div>
          )}
        </ErrorBoundary>
      </Card>

      {/* 6. Form Validation & Input Preservation */}
      <Card className="p-5 space-y-4">
        <CardHeader className="p-0 pb-3 border-b border-ash/60">
          <CardTitle>
            <RefreshCw className="w-4 h-4 text-amber" />
            <span>6. Accessible Form Validation &amp; Input Preservation</span>
          </CardTitle>
        </CardHeader>
        <p className="text-xs text-dust">
          Validation errors appear inline with <code className="text-amber">role=&quot;alert&quot;</code> and <code className="text-amber">aria-invalid</code> without wiping entered values:
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (validateAll()) {
              success("Remediation execution request submitted successfully!", "Form Validated")
            }
          }}
          className="max-w-md space-y-3 font-sans text-xs"
        >
          <div>
            <label htmlFor="demo-rem-id" className="block text-bone font-medium mb-1">
              Remediation Action ID
            </label>
            <input
              id="demo-rem-id"
              value={values.remediationId}
              onChange={(e) => setValue("remediationId", e.target.value)}
              onBlur={() => setFieldTouched("remediationId")}
              placeholder="e.g. REM-4091"
              className="w-full px-3 py-2 rounded bg-ink border border-ash text-bone placeholder:text-dust/50 focus:outline-none focus:border-amber font-mono text-xs"
              aria-invalid={!!errors.remediationId}
              aria-describedby={errors.remediationId ? "rem-id-error" : undefined}
            />
            <FormFieldError id="rem-id-error" error={errors.remediationId} />
          </div>

          <div>
            <label htmlFor="demo-operator-email" className="block text-bone font-medium mb-1">
              Authorizing Operator Email
            </label>
            <input
              id="demo-operator-email"
              value={values.operatorEmail}
              onChange={(e) => setValue("operatorEmail", e.target.value)}
              onBlur={() => setFieldTouched("operatorEmail")}
              placeholder="e.g. operator@sherlog.internal"
              className="w-full px-3 py-2 rounded bg-ink border border-ash text-bone placeholder:text-dust/50 focus:outline-none focus:border-amber font-mono text-xs"
              aria-invalid={!!errors.operatorEmail}
              aria-describedby={errors.operatorEmail ? "email-error" : undefined}
            />
            <FormFieldError id="email-error" error={errors.operatorEmail} />
          </div>

          <div className="flex items-center gap-2 pt-1">
            <Button variant="default" size="sm" type="submit">
              Submit Remediation Form
            </Button>
            <Button variant="ghost" size="sm" type="button" onClick={() => reset()}>
              Reset
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}

const ExplodingComponent: React.FC = () => {
  throw new Error("Simulated rendering exception in Telemetry Component!")
}
