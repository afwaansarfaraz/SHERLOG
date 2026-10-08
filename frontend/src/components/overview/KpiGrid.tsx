import React from "react"
import { AlertTriangle, Server, Activity, FileText } from "lucide-react"
import { Card } from "../common/Card"

interface KpiGridProps {
  activeIncidentsCount?: number
  servicesCount?: number
  overallUptime?: number
  investigations24hCount?: number
  onIncidentKpiClick?: () => void
  onServicesKpiClick?: () => void
}

export const KpiGrid: React.FC<KpiGridProps> = ({
  activeIncidentsCount = 3,
  servicesCount = 4,
  overallUptime = 99.8,
  investigations24hCount = 12,
  onIncidentKpiClick,
  onServicesKpiClick,
}) => {
  const kpis = [
    {
      label: "Active Incidents",
      value: activeIncidentsCount,
      icon: AlertTriangle,
      iconColor: "text-vermilion",
      iconBg: "bg-[#291714] border-[#4A241E]",
      onClick: onIncidentKpiClick,
      hasAlert: activeIncidentsCount > 0,
    },
    {
      label: "Services Monitored",
      value: servicesCount,
      icon: Server,
      iconColor: "text-bone",
      iconBg: "bg-[#211C18] border-ash",
      onClick: onServicesKpiClick,
    },
    {
      label: "Overall Uptime",
      value: `${overallUptime}%`,
      icon: Activity,
      iconColor: "text-verdigris",
      iconBg: "bg-[#162722] border-[#234A3E]",
    },
    {
      label: "Investigations (24h)",
      value: investigations24hCount,
      icon: FileText,
      iconColor: "text-dust",
      iconBg: "bg-[#211C18] border-ash",
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {kpis.map((kpi) => {
        const Icon = kpi.icon

        return (
          <Card
            key={kpi.label}
            interactive={Boolean(kpi.onClick)}
            onClick={kpi.onClick}
            className="flex items-center justify-between p-4 sm:p-5 relative overflow-hidden group select-none"
          >
            <div>
              <div className="text-2xl sm:text-3xl font-semibold text-bone font-mono tracking-tight">
                {kpi.value}
              </div>
              <div className="text-xs text-dust font-sans mt-1 group-hover:text-bone transition-colors">
                {kpi.label}
              </div>
            </div>

            <div
              className={`w-10 h-10 rounded-lg border flex items-center justify-center shrink-0 ${kpi.iconBg} ${kpi.iconColor}`}
            >
              <Icon className="w-5 h-5" />
            </div>
          </Card>
        )
      })}
    </div>
  )
}
