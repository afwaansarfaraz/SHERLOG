import React, { useState, useEffect, useRef, useCallback } from "react"
import { Search, X, AlertTriangle, Server, ArrowRight } from "lucide-react"
import { mockIncidents } from "../../mocks/incidents"
import { mockServices } from "../../mocks/services"
import { Badge } from "../common/Badge"

interface SearchModalProps {
  isOpen: boolean
  onClose: () => void
  onSelectIncident?: (id: string) => void
}

export const SearchModal: React.FC<SearchModalProps> = ({ isOpen, onClose, onSelectIncident }) => {
  const [query, setQuery] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  const handleClose = useCallback(() => {
    setQuery("")
    onClose()
  }, [onClose])

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        if (isOpen) handleClose()
      }
      if (e.key === "Escape" && isOpen) {
        handleClose()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, handleClose])

  if (!isOpen) return null

  const filteredIncidents = mockIncidents.filter(
    (inc) =>
      inc.title.toLowerCase().includes(query.toLowerCase()) ||
      inc.id.toLowerCase().includes(query.toLowerCase()) ||
      inc.service.toLowerCase().includes(query.toLowerCase())
  )

  const filteredServices = mockServices.filter(
    (srv) =>
      srv.displayName.toLowerCase().includes(query.toLowerCase()) ||
      srv.name.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-ink/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-xl bg-soot border border-ash rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[70vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-ash bg-ink/50">
          <Search className="w-4 h-4 text-dust shrink-0" />
          <input
            ref={inputRef}
            id="global-search-input"
            name="globalSearch"
            type="text"
            placeholder="Search incidents, services, logs, runbooks..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-transparent text-bone placeholder:text-dust text-sm outline-none font-sans"
          />
          {query ? (
            <button onClick={() => setQuery("")} className="text-dust hover:text-bone p-1">
              <X className="w-3.5 h-3.5" />
            </button>
          ) : (
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-dust bg-soot border border-ash rounded">
              ESC
            </kbd>
          )}
        </div>

        {/* Results List */}
        <div className="p-3 overflow-y-auto space-y-4 text-xs custom-scrollbar">
          {/* Incidents Section */}
          <div>
            <div className="text-[11px] font-mono uppercase text-dust px-2 mb-1.5 tracking-wider">
              Incidents ({filteredIncidents.length})
            </div>
            {filteredIncidents.length > 0 ? (
              <div className="space-y-1">
                {filteredIncidents.map((inc) => (
                  <button
                    key={inc.id}
                    onClick={() => {
                      if (onSelectIncident) onSelectIncident(inc.id)
                      handleClose()
                    }}
                    className="w-full flex items-center justify-between p-2 rounded hover:bg-ink/70 border border-transparent hover:border-ash/70 transition-colors text-left group"
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <AlertTriangle
                        className={
                          inc.status === "INVESTIGATING"
                            ? "w-3.5 h-3.5 text-vermilion shrink-0"
                            : "w-3.5 h-3.5 text-verdigris shrink-0"
                        }
                      />
                      <span className="font-mono text-dust text-[11px] shrink-0">{inc.id}</span>
                      <span className="text-bone font-medium truncate group-hover:text-bone">
                        {inc.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge
                        variant={inc.status === "INVESTIGATING" ? "investigating" : "resolved"}
                      >
                        {inc.status}
                      </Badge>
                      <ArrowRight className="w-3 h-3 text-dust group-hover:text-bone transition-transform group-hover:translate-x-0.5" />
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-dust text-xs px-2 py-1 italic">No matching incidents</div>
            )}
          </div>

          {/* Services Section */}
          <div>
            <div className="text-[11px] font-mono uppercase text-dust px-2 mb-1.5 tracking-wider">
              Monitored Services ({filteredServices.length})
            </div>
            {filteredServices.length > 0 ? (
              <div className="space-y-1">
                {filteredServices.map((srv) => (
                  <div
                    key={srv.id}
                    className="flex items-center justify-between p-2 rounded hover:bg-ink/70 border border-transparent hover:border-ash/70 transition-colors"
                  >
                    <div className="flex items-center gap-2.5">
                      <Server className="w-3.5 h-3.5 text-dust shrink-0" />
                      <span className="text-bone font-medium">{srv.displayName}</span>
                      <span className="text-dust font-mono text-[11px]">p95: {srv.p95Latency}</span>
                    </div>
                    <Badge variant={srv.status === "HEALTHY" ? "healthy" : "degraded"}>
                      {srv.uptime}% Uptime
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-dust text-xs px-2 py-1 italic">No matching services</div>
            )}
          </div>
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 bg-ink/70 border-t border-ash flex items-center justify-between text-[11px] text-dust font-mono">
          <span>Navigate with mouse or keyboard</span>
          <div className="flex items-center gap-2">
            <span>Close:</span>
            <kbd className="px-1.5 py-0.5 text-[10px] bg-soot border border-ash rounded">ESC</kbd>
          </div>
        </div>
      </div>
    </div>
  )
}
