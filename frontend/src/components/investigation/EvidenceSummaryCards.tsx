import React from "react"
import { Database, Clock, GitBranch, ArrowRight } from "lucide-react"

interface EvidenceSummaryCardsProps {
  onViewAllEvidence?: () => void
}

export const EvidenceSummaryCards: React.FC<EvidenceSummaryCardsProps> = ({
  onViewAllEvidence,
}) => {
  const summaryCards = [
    {
      title: "DB Connections",
      value: "100% utilization",
      delta: "+340% vs normal",
      icon: Database,
      iconColor: "text-amber",
      iconBg: "bg-[#291F13] border-[#4A391A]",
      isAlert: true,
    },
    {
      title: "API Latency",
      value: "1.2s (p95)",
      delta: "+820% vs normal",
      icon: Clock,
      iconColor: "text-amber",
      iconBg: "bg-[#291F13] border-[#4A391A]",
      isAlert: true,
    },
    {
      title: "No Recent Deployments",
      value: "Last deployment",
      delta: "2 hours ago",
      icon: GitBranch,
      iconColor: "text-dust",
      iconBg: "bg-[#211C18] border-ash",
      isAlert: false,
    },
  ]

  return (
    <div className="space-y-3 pt-2">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-bone uppercase tracking-wider font-mono">
          Evidence Summary
        </h4>
        {onViewAllEvidence && (
          <button
            onClick={onViewAllEvidence}
            className="text-xs text-dust hover:text-bone font-medium flex items-center gap-1 transition-colors group cursor-pointer"
          >
            <span>View all evidence</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {summaryCards.map((card) => {
          const Icon = card.icon

          return (
            <div
              key={card.title}
              onClick={onViewAllEvidence}
              className="p-3 rounded-md bg-ink/40 border border-ash/70 hover:border-ash hover:bg-ink/70 transition-all flex items-start gap-3 cursor-pointer group"
            >
              <div
                className={`w-7 h-7 rounded border flex items-center justify-center shrink-0 ${card.iconBg} ${card.iconColor}`}
              >
                <Icon className="w-3.5 h-3.5" />
              </div>

              <div className="min-w-0 flex-1">
                <div className="text-[11px] text-dust font-sans leading-snug line-clamp-1" title={card.title}>
                  {card.title}
                </div>
                <div className="text-xs font-semibold text-bone font-mono leading-tight mt-0.5 break-words">
                  {card.value}
                </div>
                <div
                  className={`text-[10px] font-mono mt-0.5 break-words ${
                    card.isAlert ? "text-amber" : "text-dust/80"
                  }`}
                >
                  {card.delta}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
