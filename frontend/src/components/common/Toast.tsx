import React from "react"
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from "lucide-react"
import { useToast, type ToastItem, type ToastVariant } from "../../hooks/useToast"
import { cn } from "../../lib/utils"

const variantStyles: Record<
  ToastVariant,
  {
    bg: string
    border: string
    iconColor: string
    titleColor: string
    Icon: React.ElementType
  }
> = {
  success: {
    bg: "bg-[#162722]/95",
    border: "border-[#234A3E]",
    iconColor: "text-verdigris",
    titleColor: "text-verdigris",
    Icon: CheckCircle2,
  },
  error: {
    bg: "bg-[#291714]/95",
    border: "border-[#4A241E]",
    iconColor: "text-vermilion",
    titleColor: "text-vermilion",
    Icon: AlertCircle,
  },
  warning: {
    bg: "bg-[#271E14]/95",
    border: "border-[#4A391A]",
    iconColor: "text-amber",
    titleColor: "text-amber",
    Icon: AlertTriangle,
  },
  info: {
    bg: "bg-soot/95",
    border: "border-ash",
    iconColor: "text-bone",
    titleColor: "text-bone",
    Icon: Info,
  },
}

export const ToastContainer: React.FC = () => {
  const { toasts, dismissToast } = useToast()

  if (toasts.length === 0) return null

  return (
    <div
      className="fixed bottom-5 right-5 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none"
      aria-live="polite"
      aria-label="Notification center"
    >
      {toasts.map((toast) => (
        <ToastCard key={toast.id} toast={toast} onDismiss={() => dismissToast(toast.id)} />
      ))}
    </div>
  )
}

const ToastCard: React.FC<{
  toast: ToastItem
  onDismiss: () => void
}> = ({ toast, onDismiss }) => {
  const style = variantStyles[toast.variant]
  const Icon = style.Icon
  const isError = toast.variant === "error"

  return (
    <div
      role={isError ? "alert" : "status"}
      aria-atomic="true"
      className={cn(
        "pointer-events-auto flex items-start gap-3 p-3.5 rounded-lg border shadow-xl backdrop-blur-sm transition-all duration-200 animate-in slide-in-from-right-4",
        style.bg,
        style.border
      )}
    >
      <Icon className={cn("w-4 h-4 shrink-0 mt-0.5", style.iconColor)} />

      <div className="flex-1 min-w-0 text-xs">
        {toast.title && (
          <div className={cn("font-medium font-mono text-[11px] mb-0.5", style.titleColor)}>
            {toast.title}
          </div>
        )}
        <div className="text-bone/90 break-words leading-relaxed font-sans">{toast.message}</div>
      </div>

      <div className="flex items-center gap-1 shrink-0 ml-1">
        {toast.count && toast.count > 1 && (
          <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-soot text-dust border border-ash">
            ×{toast.count}
          </span>
        )}
        <button
          onClick={onDismiss}
          className="p-1 rounded text-dust hover:text-bone hover:bg-soot transition-colors"
          aria-label="Dismiss notification"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}
