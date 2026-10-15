import { Component, type ErrorInfo, type ReactNode } from "react"
import { AlertCircle, RefreshCw, LayoutDashboard } from "lucide-react"
import { Button } from "./Button"
import { redactSensitiveString } from "../../lib/api"

interface Props {
  children: ReactNode
  moduleName?: string
  fallback?: ReactNode
  onReset?: () => void
  isRoot?: boolean
}

interface State {
  hasError: boolean
  error: Error | null
  correlationId: string | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    correlationId: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    const correlationId = "ERR-EB-" + Math.random().toString(36).substring(2, 8).toUpperCase()
    return { hasError: true, error, correlationId }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Redact sensitive details before logging to console to maintain safety
    const safeMsg = redactSensitiveString(error?.message || "Unknown error")
    console.error(
      `[ErrorBoundary] ${this.props.moduleName || "Module"} caught an unhandled error (${this.state.correlationId}):`,
      safeMsg,
      errorInfo?.componentStack ? "[Component stack recorded]" : ""
    )
  }

  private handleRetry = () => {
    if (this.props.onReset) {
      this.props.onReset()
    }
    this.setState({ hasError: false, error: null, correlationId: null })
  }

  private handleGoToDashboard = () => {
    window.location.hash = "overview"
    this.handleRetry()
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      // If this is the root application error boundary, render a full-screen branded safety screen
      if (this.props.isRoot) {
        return (
          <div className="min-h-screen bg-ink flex items-center justify-center p-4">
            <div className="bg-soot border border-ash/90 rounded-lg p-8 max-w-lg w-full text-center space-y-6 shadow-2xl">
              <div className="w-14 h-14 rounded-xl bg-[#2A1513] border border-[#52211C] flex items-center justify-center text-vermilion mx-auto">
                <AlertCircle className="w-7 h-7" />
              </div>
              <div className="space-y-2">
                <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-[#2E1815] text-vermilion border border-[#54251F]">
                  <span>APPLICATION CRITICAL SAFETY BOUNDARY</span>
                </div>
                <h2 className="text-xl font-semibold text-bone">Sherlog Session Interrupted</h2>
                <p className="text-xs text-dust leading-relaxed max-w-sm mx-auto">
                  An unexpected rendering exception was caught. Unsaved UI state has been isolated
                  to protect session integrity.
                </p>
              </div>

              {this.state.correlationId && (
                <div className="p-2.5 rounded bg-ink border border-ash/60 font-mono text-[11px] text-dust">
                  Reference: <span className="text-bone">{this.state.correlationId}</span>
                </div>
              )}

              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                <Button variant="secondary" size="md" onClick={() => window.location.reload()} className="w-full sm:w-auto">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  <span>Reload Sherlog</span>
                </Button>
                <Button variant="default" size="md" onClick={this.handleGoToDashboard} className="w-full sm:w-auto">
                  <LayoutDashboard className="w-4 h-4 mr-2" />
                  <span>Go to Overview</span>
                </Button>
              </div>
            </div>
          </div>
        )
      }

      // Widget / Component isolated boundary
      return (
        <div
          role="alert"
          className="bg-soot border border-ash/80 rounded-lg p-5 flex flex-col items-center justify-center text-center space-y-3 min-h-[140px]"
        >
          <div className="w-8 h-8 rounded bg-[#2E1815] border border-[#54251F] flex items-center justify-center text-vermilion">
            <AlertCircle className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-mono uppercase tracking-wider text-bone font-medium">
              {this.props.moduleName || "Module"} Temporarily Unavailable
            </h4>
            <p className="text-xs text-dust max-w-sm mt-1">
              An isolated error occurred while rendering this widget. The rest of the platform
              remains fully functional.
            </p>
          </div>
          <Button variant="secondary" size="sm" onClick={this.handleRetry}>
            <RefreshCw className="w-3.5 h-3.5 mr-1" /> Retry Component
          </Button>
        </div>
      )
    }

    return this.props.children
  }
}
