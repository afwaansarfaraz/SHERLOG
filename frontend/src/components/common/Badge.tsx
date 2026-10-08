import React from "react"
import { cn } from "../../lib/utils"

export type BadgeVariant =
  | "investigating"
  | "resolved"
  | "awaiting_approval"
  | "healthy"
  | "degraded"
  | "critical"
  | "slate"
  | "default"

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
  withDot?: boolean
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "default",
  withDot = false,
  className,
  ...props
}) => {
  const variantStyles: Record<BadgeVariant, { container: string; dot: string }> = {
    investigating: {
      container: "bg-[#291B15] text-vermilion border border-[#4D281E]",
      dot: "bg-vermilion",
    },
    resolved: {
      container: "bg-[#162722] text-verdigris border border-[#234A3E]",
      dot: "bg-verdigris",
    },
    awaiting_approval: {
      container: "bg-[#2B2313] text-amber border border-[#523F1C]",
      dot: "bg-amber",
    },
    healthy: {
      container: "bg-[#162722] text-verdigris border border-[#234A3E]",
      dot: "bg-verdigris",
    },
    degraded: {
      container: "bg-[#2B2313] text-amber border border-[#523F1C]",
      dot: "bg-amber",
    },
    critical: {
      container: "bg-[#2E1618] text-vermilion border border-[#572124]",
      dot: "bg-vermilion",
    },
    slate: {
      container: "bg-[#1C232D] text-slate border border-[#2A394C]",
      dot: "bg-slate",
    },
    default: {
      container: "bg-soot text-dust border border-ash",
      dot: "bg-dust",
    },
  }

  const { container, dot } = variantStyles[variant] || variantStyles.default

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono uppercase tracking-wider font-medium transition-colors select-none",
        container,
        className
      )}
      {...props}
    >
      {withDot && <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", dot)} />}
      {children}
    </span>
  )
}
