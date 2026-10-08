import { Component, type ErrorInfo, type ReactNode } from "react"
import { AlertCircle, RefreshCw } from "lucide-react"
import { Button } from "./Button"

interface Props {
  children: ReactNode
  moduleName?: string
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(
      `[ErrorBoundary] ${this.props.moduleName || "Module"} encountered error:`,
      error,
      errorInfo
    )
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="bg-soot border border-ash/80 rounded-lg p-5 flex flex-col items-center justify-center text-center space-y-3 min-h-[140px]">
          <div className="w-8 h-8 rounded bg-[#2E1815] border border-[#54251F] flex items-center justify-center text-vermilion">
            <AlertCircle className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-mono uppercase tracking-wider text-bone font-medium">
              {this.props.moduleName || "Module"} Temporarily Unavailable
            </h4>
            <p className="text-xs text-dust max-w-sm mt-1">
              An isolated error occurred while rendering this widget. The rest of the platform
              remains functional.
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
