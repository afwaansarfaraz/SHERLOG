import { useState, useEffect, useCallback, useRef } from "react"

export type NetworkConnectionState =
  | "online" // Normal connected state
  | "offline" // Browser offline event triggered / no network
  | "backend-unreachable" // Has network, but backend probe failed
  | "maintenance" // 503 Maintenance response from backend
  | "rechecking" // Probe currently in progress

export interface NetworkStatus {
  state: NetworkConnectionState
  isOnline: boolean
  isBackendHealthy: boolean
  lastChecked: Date | null
  checkConnection: () => Promise<NetworkConnectionState>
}

interface UseNetworkStatusOptions {
  healthEndpoint?: string
  probeIntervalMs?: number
  checkOnMount?: boolean
}

export function useNetworkStatus({
  healthEndpoint = "/api/health",
  probeIntervalMs = 30000,
  checkOnMount = false,
}: UseNetworkStatusOptions = {}): NetworkStatus {
  // Safe initial state
  const [state, setState] = useState<NetworkConnectionState>(() => {
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      return "offline"
    }
    return "online"
  })

  const [lastChecked, setLastChecked] = useState<Date | null>(null)
  const isMountedRef = useRef(true)

  const checkConnection = useCallback(async (): Promise<NetworkConnectionState> => {
    // 1. First check navigator.onLine
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      if (isMountedRef.current) {
        setState("offline")
        setLastChecked(new Date())
      }
      return "offline"
    }

    if (isMountedRef.current) {
      setState("rechecking")
    }

    // 2. Perform lightweight fetch probe
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 4000)

      const response = await fetch(healthEndpoint, {
        method: "GET",
        signal: controller.signal,
        cache: "no-store",
        headers: { Accept: "application/json" },
      })

      clearTimeout(timeoutId)

      let nextState: NetworkConnectionState = "online"
      if (response.status === 503) {
        nextState = "maintenance"
      } else if (!response.ok && response.status >= 500) {
        nextState = "backend-unreachable"
      } else {
        nextState = "online"
      }

      if (isMountedRef.current) {
        setState(nextState)
        setLastChecked(new Date())
      }
      return nextState
    } catch {
      // Fetch threw (abort, connection refused, CORS, DNS error)
      const nextState: NetworkConnectionState =
        typeof navigator !== "undefined" && !navigator.onLine ? "offline" : "backend-unreachable"

      if (isMountedRef.current) {
        setState(nextState)
        setLastChecked(new Date())
      }
      return nextState
    }
  }, [healthEndpoint])

  useEffect(() => {
    isMountedRef.current = true

    const handleBrowserOnline = () => {
      // When browser signals online, immediately verify backend connectivity
      checkConnection()
    }

    const handleBrowserOffline = () => {
      setState("offline")
      setLastChecked(new Date())
    }

    window.addEventListener("online", handleBrowserOnline)
    window.addEventListener("offline", handleBrowserOffline)

    let mountTimer: NodeJS.Timeout | null = null
    if (checkOnMount) {
      mountTimer = setTimeout(() => {
        checkConnection()
      }, 0)
    }

    let intervalId: NodeJS.Timeout | null = null
    if (probeIntervalMs > 0) {
      intervalId = setInterval(() => {
        // Only run background periodic probe if we are already online or backend-unreachable
        if (state !== "offline") {
          checkConnection()
        }
      }, probeIntervalMs)
    }

    return () => {
      isMountedRef.current = false
      window.removeEventListener("online", handleBrowserOnline)
      window.removeEventListener("offline", handleBrowserOffline)
      if (mountTimer) clearTimeout(mountTimer)
      if (intervalId) clearInterval(intervalId)
    }
  }, [checkConnection, checkOnMount, probeIntervalMs, state])

  return {
    state,
    isOnline: state === "online",
    isBackendHealthy: state === "online",
    lastChecked,
    checkConnection,
  }
}
