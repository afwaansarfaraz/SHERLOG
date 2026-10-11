import React, { useRef, useEffect } from "react"
import { AlertTriangle, CheckCircle2, Clock } from "lucide-react"
import { mockIncidents } from "../../mocks/incidents"
import { Badge } from "../common/Badge"

interface NotificationsPopoverProps {
  isOpen: boolean
  onClose: () => void
  onSelectIncident?: (id: string) => void
}

export const NotificationsPopover: React.FC<NotificationsPopoverProps> = ({
  isOpen,
  onClose,
  onSelectIncident,
}) => {
  const popoverRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside)
    }
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      ref={popoverRef}
      className="absolute right-0 top-12 w-80 sm:w-96 bg-soot border border-ash rounded-lg shadow-2xl z-50 overflow-hidden animate-in fade-in duration-100"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-ash bg-ink/40">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-xs text-bone tracking-wide">
            Notifications &amp; Alerts
          </span>
          <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-[#3A1E18] text-vermilion border border-[#5E271D]">
            3 New
          </span>
        </div>
        <button onClick={onClose} className="text-[11px] text-dust hover:text-bone font-mono">
          Mark all read
        </button>
      </div>

      <div className="max-h-80 overflow-y-auto divide-y divide-ash/50 custom-scrollbar">
        {mockIncidents.slice(0, 3).map((inc) => (
          <div
            key={inc.id}
            onClick={() => {
              if (onSelectIncident) onSelectIncident(inc.id)
              onClose()
            }}
            className="p-3 hover:bg-ink/60 transition-colors cursor-pointer group"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                {inc.status === "INVESTIGATING" ? (
                  <AlertTriangle className="w-3.5 h-3.5 text-vermilion shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle2 className="w-3.5 h-3.5 text-verdigris shrink-0 mt-0.5" />
                )}
                <span className="text-xs font-medium text-bone group-hover:text-amber transition-colors">
                  {inc.title}
                </span>
              </div>
              <Badge variant={inc.status === "INVESTIGATING" ? "investigating" : "resolved"}>
                {inc.status}
              </Badge>
            </div>
            <p className="text-[11px] text-dust mt-1 line-clamp-2 pl-5">{inc.summary}</p>
            <div className="flex items-center gap-2 text-[10px] font-mono text-dust mt-2 pl-5">
              <Clock className="w-3 h-3 text-dust" />
              <span>{inc.openedAt}</span>
              <span>•</span>
              <span className="text-bone/80">{inc.service}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="p-2.5 bg-ink/70 border-t border-ash text-center">
        <button onClick={onClose} className="text-xs text-dust hover:text-bone font-medium">
          View all in Incidents tab →
        </button>
      </div>
    </div>
  )
}
