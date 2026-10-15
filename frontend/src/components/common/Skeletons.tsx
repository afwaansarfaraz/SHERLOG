import React from "react"
import { Skeleton } from "./Skeleton"

/**
 * Skeleton placeholder for the Incident triage rows in Overview / Incidents tab
 */
export const IncidentListSkeleton: React.FC<{ count?: number }> = ({ count = 3 }) => {
  return (
    <div className="space-y-2.5 w-full" aria-label="Loading incidents" role="status">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex items-center justify-between p-3 rounded-md bg-ink/50 border border-ash/70"
        >
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <Skeleton className="w-7 h-7 rounded shrink-0 bg-[#25201B]" />
            <div className="space-y-1.5 flex-1 min-w-0 pr-4">
              <Skeleton className="h-3.5 w-3/5 max-w-xs" />
              <Skeleton className="h-2.5 w-1/4 max-w-[120px]" />
            </div>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <Skeleton className="h-3 w-16 hidden sm:block" />
            <div className="space-y-1 items-end flex flex-col">
              <Skeleton className="h-4 w-20 rounded-full" />
              <Skeleton className="h-2.5 w-12" />
            </div>
          </div>
        </div>
      ))}
      <span className="sr-only">Loading incidents...</span>
    </div>
  )
}

/**
 * Skeleton placeholder for Metrics telemetry cards and charts
 */
export const MetricsChartSkeleton: React.FC<{ count?: number }> = ({ count = 2 }) => {
  return (
    <div className="space-y-4 w-full" aria-label="Loading telemetry metrics" role="status">
      {/* PromQL query header skeleton */}
      <div className="p-3 rounded bg-ink/70 border border-ash flex items-center justify-between">
        <Skeleton className="h-3.5 w-64 max-w-sm" />
        <Skeleton className="h-3 w-32" />
      </div>

      {/* Metric switcher tabs skeleton */}
      <div className="flex gap-2 border-b border-ash/50 pb-2">
        <Skeleton className="h-6 w-28 rounded" />
        <Skeleton className="h-6 w-24 rounded" />
        <Skeleton className="h-6 w-24 rounded" />
      </div>

      {/* Chart cards */}
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="p-5 rounded-lg bg-soot border border-ash space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1.5">
              <Skeleton className="h-4 w-52" />
              <Skeleton className="h-3 w-72" />
            </div>
            <Skeleton className="h-5 w-24 rounded" />
          </div>

          {/* KPI grid row skeleton */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 py-2 px-3 rounded bg-ink/60 border border-ash/60">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-full" />
          </div>

          {/* Chart canvas area skeleton */}
          <Skeleton className="h-48 w-full rounded" />
        </div>
      ))}
      <span className="sr-only">Loading metrics telemetry...</span>
    </div>
  )
}

/**
 * Skeleton placeholder for Logs feed
 */
export const LogsViewSkeleton: React.FC<{ rowCount?: number }> = ({ rowCount = 6 }) => {
  return (
    <div className="space-y-3 font-mono w-full" aria-label="Loading logs" role="status">
      {/* Search & Tool query bar */}
      <div className="flex items-center justify-between p-2.5 rounded bg-ink/70 border border-ash">
        <Skeleton className="h-3.5 w-60" />
        <Skeleton className="h-6 w-40 rounded" />
      </div>

      {/* Sanitized notice skeleton */}
      <Skeleton className="h-6 w-full rounded" />

      {/* Log lines container */}
      <div className="rounded-md bg-ink border border-ash p-2 space-y-2">
        {Array.from({ length: rowCount }).map((_, i) => (
          <div key={i} className="flex items-center gap-2.5 py-1.5 px-2">
            <Skeleton className="h-3 w-16 shrink-0" />
            <Skeleton className="h-3 w-12 rounded shrink-0" />
            <Skeleton className="h-3 w-14 shrink-0" />
            <Skeleton className="h-3 flex-1" />
          </div>
        ))}
      </div>
      <span className="sr-only">Loading logs...</span>
    </div>
  )
}

/**
 * Skeleton placeholder for Jaeger Traces Waterfall
 */
export const TracesWaterfallSkeleton: React.FC<{ spanCount?: number }> = ({ spanCount = 5 }) => {
  return (
    <div className="space-y-3 font-mono w-full" aria-label="Loading traces" role="status">
      {/* Header */}
      <div className="p-3 rounded bg-ink/70 border border-ash flex items-center justify-between">
        <Skeleton className="h-3.5 w-52" />
        <Skeleton className="h-3.5 w-32" />
      </div>

      {/* Waterfall spans */}
      <div className="rounded-md bg-ink border border-ash p-4 space-y-4">
        <div className="flex justify-between border-b border-ash pb-2">
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-3 w-28" />
        </div>

        {Array.from({ length: spanCount }).map((_, i) => (
          <div key={i} className="space-y-1.5">
            <div className="flex justify-between">
              <Skeleton className="h-3 w-48" />
              <Skeleton className="h-3 w-12" />
            </div>
            <Skeleton className="h-2 w-full rounded" />
          </div>
        ))}
      </div>
      <span className="sr-only">Loading trace spans...</span>
    </div>
  )
}

/**
 * Skeleton placeholder for Investigation Stepper Timeline
 */
export const InvestigationTimelineSkeleton: React.FC<{ count?: number }> = ({ count = 5 }) => {
  return (
    <div className="space-y-4 w-full p-4 rounded-lg bg-soot border border-ash" role="status">
      <Skeleton className="h-4 w-36 mb-2" />
      <div className="space-y-3">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="flex items-start gap-3">
            <Skeleton className="w-6 h-6 rounded-full shrink-0" />
            <div className="flex-1 space-y-1 pt-0.5">
              <Skeleton className="h-3 w-3/4" />
              <Skeleton className="h-2.5 w-1/2" />
            </div>
          </div>
        ))}
      </div>
      <span className="sr-only">Loading investigation timeline...</span>
    </div>
  )
}
