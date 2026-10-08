import React from "react"
import { Terminal, Clock, ArrowRight } from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import type { ActivityItem } from "../../types"

interface RecentActivityFeedProps {
  activities: ActivityItem[]
  onSelectIncident?: (id: string) => void
  onViewAll?: () => void
}

export const RecentActivityFeed: React.FC<RecentActivityFeedProps> = ({
  activities,
  onSelectIncident,
  onViewAll,
}) => {
  return (
    <Card className="flex flex-col h-full">
      <CardHeader>
        <CardTitle>
          <Terminal className="w-4 h-4 text-dust" />
          <span>Recent Activity</span>
        </CardTitle>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="text-xs text-dust hover:text-bone font-medium flex items-center gap-1 transition-colors group"
          >
            <span>View all</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </button>
        )}
      </CardHeader>

      <div className="space-y-2.5 flex-1 max-h-72 overflow-y-auto pr-1">
        {activities.map((act) => (
          <div
            key={act.id}
            onClick={() => onSelectIncident?.(act.incidentId)}
            className="p-2.5 rounded bg-ink/40 border border-ash/50 hover:border-ash hover:bg-ink/70 transition-colors cursor-pointer group text-xs font-mono"
          >
            <div className="flex items-center justify-between text-[11px] text-dust mb-1">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3 h-3 text-dust shrink-0" />
                <span>{act.timestamp}</span>
              </span>
              <span className="text-bone/80 group-hover:text-amber transition-colors">
                {act.incidentId}
              </span>
            </div>
            <div className="text-bone truncate font-sans text-xs">{act.message}</div>
            {act.details && (
              <div className="text-[11px] text-dust truncate mt-0.5 font-mono text-dust/80">
                {act.details}
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  )
}
