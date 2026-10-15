import React from "react"
import { CheckCircle2, Search, Activity, FileQuestion } from "lucide-react"
import { Button } from "./Button"
import { cn } from "../../lib/utils"

export type EmptyStateVariant =
  | "no-incidents"
  | "no-search-results"
  | "no-telemetry"
  | "no-evidence"
  | "custom"

interface EmptyStateProps {
  variant?: EmptyStateVariant
  title?: string
  description?: string
  searchQuery?: string
  actionLabel?: string
  onAction?: () => void
  icon?: React.ElementType
  className?: string
}

const defaultConfigurations: Record<
  Exclude<EmptyStateVariant, "custom">,
  {
    icon: React.ElementType
    iconColor: string
    iconBg: string
    iconBorder: string
    defaultTitle: string
    defaultDesc: (query?: string) => string
  }
> = {
  "no-incidents": {
    icon: CheckCircle2,
    iconColor: "text-verdigris",
    iconBg: "bg-[#162722]",
    iconBorder: "border-[#234A3E]",
    defaultTitle: "All Systems Operational",
    defaultDesc: () => "Zero active incidents detected across all monitored services and pipelines.",
  },
  "no-search-results": {
    icon: Search,
    iconColor: "text-amber",
    iconBg: "bg-[#271E14]",
    iconBorder: "border-[#4A391A]",
    defaultTitle: "No Matching Records Found",
    defaultDesc: (query) =>
      query
        ? `No results found matching query "${query}". Check your spelling or try broader filters.`
        : "No results matched the current filter criteria.",
  },
  "no-telemetry": {
    icon: Activity,
    iconColor: "text-dust",
    iconBg: "bg-ink",
    iconBorder: "border-ash",
    defaultTitle: "No Telemetry Data Recorded",
    defaultDesc: () =>
      "The specified metric or trace query returned zero data points within the selected time window.",
  },
  "no-evidence": {
    icon: FileQuestion,
    iconColor: "text-amber",
    iconBg: "bg-[#271E14]",
    iconBorder: "border-[#4A391A]",
    defaultTitle: "No Investigation Evidence Gathered",
    defaultDesc: () =>
      "The agent has not collected corroborating or contradicting telemetry artifacts for this stage yet.",
  },
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  variant = "custom",
  title,
  description,
  searchQuery,
  actionLabel,
  onAction,
  icon,
  className,
}) => {
  const config =
    variant !== "custom"
      ? defaultConfigurations[variant]
      : {
          icon: icon || FileQuestion,
          iconColor: "text-dust",
          iconBg: "bg-ink",
          iconBorder: "border-ash",
          defaultTitle: "No Data Available",
          defaultDesc: () => "There is nothing to display at this time.",
        }

  const IconComponent = icon || config.icon
  const displayTitle = title || config.defaultTitle
  const displayDesc = description || config.defaultDesc(searchQuery)

  return (
    <div
      role="status"
      className={cn(
        "p-8 sm:p-10 rounded-lg bg-ink/40 border border-ash/70 flex flex-col items-center justify-center text-center space-y-3 min-h-[160px]",
        className
      )}
    >
      <div
        className={cn(
          "w-10 h-10 rounded-lg border flex items-center justify-center shrink-0 shadow-inner",
          config.iconBg,
          config.iconBorder,
          config.iconColor
        )}
      >
        <IconComponent className="w-5 h-5" />
      </div>

      <div className="max-w-md space-y-1">
        <h4 className="text-xs sm:text-sm font-semibold text-bone font-sans tracking-tight">
          {displayTitle}
        </h4>
        <p className="text-xs text-dust leading-relaxed font-sans">{displayDesc}</p>
      </div>

      {actionLabel && onAction && (
        <div className="pt-2">
          <Button variant="secondary" size="sm" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  )
}
