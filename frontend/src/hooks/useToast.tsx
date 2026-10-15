/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useCallback, useRef } from "react"

export type ToastVariant = "success" | "error" | "warning" | "info"

export interface ToastItem {
  id: string
  title?: string
  message: string
  variant: ToastVariant
  durationMs?: number
  count?: number // Deduplication counter
  timestamp: number
}

interface ToastContextValue {
  toasts: ToastItem[]
  showToast: (options: {
    message: string
    title?: string
    variant?: ToastVariant
    durationMs?: number
  }) => string
  success: (message: string, title?: string) => string
  error: (message: string, title?: string) => string
  warning: (message: string, title?: string) => string
  info: (message: string, title?: string) => string
  dismissToast: (id: string) => void
  clearAllToasts: () => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const dedupMapRef = useRef<Map<string, { id: string; timestamp: number }>>(new Map())

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const clearAllToasts = useCallback(() => {
    setToasts([])
    dedupMapRef.current.clear()
  }, [])

  const showToast = useCallback(
    ({
      message,
      title,
      variant = "info",
      durationMs = variant === "error" ? 7000 : 4500,
    }: {
      message: string
      title?: string
      variant?: ToastVariant
      durationMs?: number
    }): string => {
      const now = Date.now()
      const dedupKey = `${variant}:${title || ""}:${message}`
      const existing = dedupMapRef.current.get(dedupKey)

      // Deduplicate if posted within 3 seconds
      if (existing && now - existing.timestamp < 3000) {
        existing.timestamp = now
        setToasts((prev) =>
          prev.map((t) =>
            t.id === existing.id
              ? { ...t, count: (t.count || 1) + 1, timestamp: now }
              : t
          )
        )
        return existing.id
      }

      const id = "toast-" + Math.random().toString(36).substring(2, 9) + "-" + now
      dedupMapRef.current.set(dedupKey, { id, timestamp: now })

      const newToast: ToastItem = {
        id,
        title,
        message,
        variant,
        durationMs,
        count: 1,
        timestamp: now,
      }

      setToasts((prev) => [...prev.slice(-4), newToast]) // Keep at most 5 toasts visible

      if (durationMs > 0) {
        setTimeout(() => {
          dismissToast(id)
          dedupMapRef.current.delete(dedupKey)
        }, durationMs)
      }

      return id
    },
    [dismissToast]
  )

  const success = useCallback(
    (message: string, title?: string) => showToast({ message, title, variant: "success" }),
    [showToast]
  )
  const error = useCallback(
    (message: string, title?: string) => showToast({ message, title, variant: "error" }),
    [showToast]
  )
  const warning = useCallback(
    (message: string, title?: string) => showToast({ message, title, variant: "warning" }),
    [showToast]
  )
  const info = useCallback(
    (message: string, title?: string) => showToast({ message, title, variant: "info" }),
    [showToast]
  )

  return (
    <ToastContext.Provider
      value={{
        toasts,
        showToast,
        success,
        error,
        warning,
        info,
        dismissToast,
        clearAllToasts,
      }}
    >
      {children}
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error("useToast must be used within a ToastProvider")
  }
  return ctx
}
