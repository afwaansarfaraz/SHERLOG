import React from "react"
import { Server, ArrowRight, ShieldCheck, ShoppingCart, CreditCard, Lock } from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import type { ServiceHealth } from "../../types"

interface SystemHealthCardProps {
  services: ServiceHealth[]
  onViewDetails?: () => void
}

export const SystemHealthCard: React.FC<SystemHealthCardProps> = ({ services, onViewDetails }) => {
  const getServiceIcon = (name: string) => {
    switch (name.toLowerCase()) {
      case "api":
        return <ShieldCheck className="w-3.5 h-3.5" />
      case "orders":
        return <ShoppingCart className="w-3.5 h-3.5" />
      case "payments":
        return <CreditCard className="w-3.5 h-3.5" />
      case "auth":
        return <Lock className="w-3.5 h-3.5" />
      default:
        return <Server className="w-3.5 h-3.5" />
    }
  }

  return (
    <Card className="flex flex-col h-full">
      <CardHeader>
        <CardTitle>
          <Server className="w-4 h-4 text-bone" />
          <span>System Health</span>
        </CardTitle>
        {onViewDetails && (
          <button
            onClick={onViewDetails}
            className="text-xs text-dust hover:text-bone font-medium flex items-center gap-1 transition-colors group"
          >
            <span>View details</span>
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </button>
        )}
      </CardHeader>

      <div className="space-y-3.5 flex-1">
        {services.map((srv) => {
          const isDegraded = srv.status === "DEGRADED"

          return (
            <div
              key={srv.id}
              className="flex items-center justify-between gap-3 p-2.5 rounded-md bg-ink/40 border border-ash/60"
            >
              {/* Service Label */}
              <div className="flex items-center gap-2.5 w-24 shrink-0">
                <span className="text-dust">{getServiceIcon(srv.name)}</span>
                <span className="text-xs font-medium text-bone truncate">{srv.displayName}</span>
              </div>

              {/* Progress Bar */}
              <div className="flex-1 max-w-xs">
                <div className="h-1.5 w-full bg-[#27211B] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isDegraded ? "bg-amber" : "bg-verdigris"
                    }`}
                    style={{ width: `${Math.min(srv.uptime, 100)}%` }}
                  />
                </div>
              </div>

              {/* Uptime % & Sparkline */}
              <div className="flex items-center gap-3 shrink-0">
                <span className="font-mono text-xs text-bone font-medium">{srv.uptime}%</span>

                {/* Micro SVG Sparkline */}
                <div className="w-12 h-4 shrink-0">
                  <svg className="w-full h-full" viewBox="0 0 50 16">
                    <polyline
                      fill="none"
                      stroke={isDegraded ? "#E0A63A" : "#4FA38B"}
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      points={
                        isDegraded
                          ? "0,8 10,6 20,9 30,14 40,12 50,15"
                          : "0,8 10,7 20,8 30,6 40,7 50,6"
                      }
                    />
                  </svg>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
