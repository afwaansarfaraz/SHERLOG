import React, { useState, useEffect } from "react"
import { WifiOff, AlertTriangle, RefreshCw, X, ShieldAlert, CheckCircle2 } from "lucide-react"
import { useNetworkStatus, type NetworkConnectionState } from "../../hooks/useNetworkStatus"
import { cn } from "../../lib/utils"

interface NetworkBannerProps {
  className?: string
  overrideState?: NetworkConnectionState
  onManualRetry?: () => void
}

export const NetworkBanner: React.FC<NetworkBannerProps> = ({
  className,
  overrideState,
  onManualRetry,
}) => {
  const { state: detectedState, checkConnection } = useNetworkStatus()
  const activeState = overrideState ?? detectedState

  const [isDismissed, setIsDismissed] = useState(false)
  const [isRetrying, setIsRetrying] = useState(false)
  const [showRestoredNotice, setShowRestoredNotice] = useState(false)
  const [previousState, setPreviousState] = useState<NetworkConnectionState>(activeState)

  if (activeState !== previousState) {
    setPreviousState(activeState)
    if (
      previousState !== "online" &&
      activeState === "online" &&
      previousState !== "rechecking"
    ) {
      setShowRestoredNotice(true)
      setIsDismissed(false)
    } else if (activeState !== "online") {
      setIsDismissed(false)
    }
  }

  useEffect(() => {
    if (!showRestoredNotice) return
    const timer = setTimeout(() => {
      setShowRestoredNotice(false)
    }, 4000)
    return () => clearTimeout(timer)
  }, [showRestoredNotice])

  const handleRetry = async () => {
    setIsRetrying(true)
    try {
      if (onManualRetry) {
        onManualRetry()
      }
      await checkConnection()
    } finally {
      setIsRetrying(false)
    }
  }

  // If online and not showing the restored notice, render nothing
  if (activeState === "online" && !showRestoredNotice) {
    return null
  }

  // If dismissed, render a subtle minimized pill so the operator still knows status
  if (isDismissed && !showRestoredNotice) {
    return (
      <div
        className={cn(
          "fixed bottom-4 right-4 z-50 flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono border shadow-lg cursor-pointer transition-all bg-soot/95 border-ash text-dust hover:text-bone",
          activeState === "offline" ? "border-vermilion/50 text-vermilion" : "border-amber/50 text-amber"
        )}
        onClick={() => setIsDismissed(false)}
        role="status"
        aria-label="Network warning: click to view details"
      >
        <span className="w-2 h-2 rounded-full animate-ping bg-current" />
        <span>{activeState === "offline" ? "Offline Mode" : "API Degraded"}</span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleRetry()
          }}
          disabled={isRetrying}
          className="ml-1 hover:text-bone"
          aria-label="Retry connection"
        >
          <RefreshCw className={cn("w-3 h-3", isRetrying && "animate-spin")} />
        </button>
      </div>
    )
  }

  // Temporary "Connection Restored" banner
  if (showRestoredNotice) {
    return (
      <div
        role="status"
        aria-live="polite"
        className={cn(
          "w-full bg-[#162722] border-b border-[#234A3E] text-verdigris px-4 py-2 text-xs font-mono flex items-center justify-between transition-all",
          className
        )}
      >
        <div className="flex items-center gap-2 max-w-7xl mx-auto flex-1">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>Connection restored. Sherlog telemetry feed reconnected.</span>
        </div>
        <button
          onClick={() => setShowRestoredNotice(false)}
          className="text-verdigris/80 hover:text-verdigris p-1 rounded"
          aria-label="Dismiss restored notice"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    )
  }

  // Error banners
  const isOffline = activeState === "offline"
  const isMaintenance = activeState === "maintenance"

  const bannerConfig = isOffline
    ? {
        icon: WifiOff,
        title: "No Internet Connection",
        description:
          "You are currently offline. Cached dashboard and investigation workspace data remain viewable, but live telemetry and agent actions are paused.",
        bgClass: "bg-[#2A1513] border-b border-[#4E211E] text-bone",
        accentClass: "text-vermilion",
      }
    : isMaintenance
    ? {
        icon: ShieldAlert,
        title: "Scheduled Sherlog API Maintenance",
        description:
          "The Sherlog backend is undergoing planned maintenance. Workspaces are read-only until maintenance concludes.",
        bgClass: "bg-[#251E14] border-b border-[#4A391A] text-bone",
        accentClass: "text-amber",
      }
    : {
        icon: AlertTriangle,
        title: "Backend API Service Unreachable",
        description:
          "Your internet connection is active, but the Sherlog API cluster cannot be reached. Telemetry may be temporarily interrupted.",
        bgClass: "bg-[#251E14] border-b border-[#4A391A] text-bone",
        accentClass: "text-amber",
      }

  const Icon = bannerConfig.icon

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={cn("w-full px-4 py-2.5 text-xs transition-all shadow-md z-40", bannerConfig.bgClass, className)}
    >
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
        <div className="flex items-start sm:items-center gap-2.5 min-w-0 flex-1">
          <Icon className={cn("w-4 h-4 shrink-0 mt-0.5 sm:mt-0", bannerConfig.accentClass)} />
          <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2 min-w-0">
            <span className={cn("font-semibold font-mono text-xs uppercase tracking-wide", bannerConfig.accentClass)}>
              {bannerConfig.title}:
            </span>
            <span className="text-dust text-xs font-sans truncate sm:whitespace-normal">
              {bannerConfig.description}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 self-end sm:self-center font-mono text-xs">
          <button
            onClick={handleRetry}
            disabled={isRetrying}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-soot/80 hover:bg-soot text-bone border border-ash/80 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3 h-3", isRetrying && "animate-spin")} />
            <span>{isRetrying ? "Rechecking..." : "Retry Connection"}</span>
          </button>

          <button
            onClick={() => setIsDismissed(true)}
            className="p-1 rounded text-dust hover:text-bone hover:bg-soot/60 transition-colors"
            aria-label="Dismiss network warning banner"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  )
}
