import React from "react"
import { Terminal, Activity, FileSearch, GitBranch, AlertTriangle } from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"

export const LiveActivityStream: React.FC = () => {
  const events = [
    {
      time: "19:42:07",
      type: "TOOL",
      icon: Terminal,
      iconColor: "text-amber",
      title: "Executing tool",
      code: "query_metrics(service='orders')",
    },
    {
      time: "19:42:06",
      type: "RESULT",
      icon: Activity,
      iconColor: "text-vermilion",
      title: "Tool result",
      code: "API latency increased 8.2x",
    },
    {
      time: "19:42:05",
      type: "TOOL",
      icon: Terminal,
      iconColor: "text-amber",
      title: "Executing tool",
      code: "search_logs(service='orders')",
    },
    {
      time: "19:42:05",
      type: "RESULT",
      icon: FileSearch,
      iconColor: "text-dust",
      title: "Found 12 relevant log entries",
      code: "Showing top 3...",
    },
    {
      time: "19:42:04",
      type: "TOOL",
      icon: Terminal,
      iconColor: "text-amber",
      title: "Executing tool",
      code: "check_deployments()",
    },
    {
      time: "19:42:04",
      type: "RESULT",
      icon: GitBranch,
      iconColor: "text-dust",
      title: "No deployments found",
      code: "in last 30 minutes",
    },
    {
      time: "19:42:03",
      type: "ALERT",
      icon: AlertTriangle,
      iconColor: "text-vermilion",
      title: "Alert received",
      code: "High API latency detected",
    },
  ]

  return (
    <Card className="flex flex-col h-full font-mono text-xs">
      <CardHeader>
        <CardTitle>
          <Terminal className="w-4 h-4 text-amber" />
          <span>Live Agent Activity</span>
        </CardTitle>
      </CardHeader>

      <div className="space-y-3 flex-1 overflow-y-auto pr-1">
        {events.map((ev, idx) => {
          const Icon = ev.icon

          return (
            <div
              key={idx}
              className="flex items-start gap-2.5 p-2 rounded bg-ink/40 border border-ash/40 hover:border-ash transition-colors leading-relaxed"
            >
              <span className="text-dust text-[11px] shrink-0 pt-0.5">{ev.time}</span>

              <Icon className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${ev.iconColor}`} />

              <div className="min-w-0 flex-1">
                <span className="text-dust mr-1.5">{ev.title}</span>
                <span className="text-bone font-medium break-all">{ev.code}</span>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
