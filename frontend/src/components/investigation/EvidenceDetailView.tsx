import React, { useState } from "react"
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, MinusCircle, Code2 } from "lucide-react"
import type { EvidenceItem, EvidencePolarity } from "../../types"

interface EvidenceDetailViewProps {
  evidence: EvidenceItem[]
  expandedIds: Set<string>
  onToggleExpand: (id: string) => void
}

export const EvidenceDetailView: React.FC<EvidenceDetailViewProps> = ({
  evidence,
  expandedIds,
  onToggleExpand,
}) => {
  const [polarityFilter, setPolarityFilter] = useState<"ALL" | EvidencePolarity>("ALL")

  const filtered = evidence.filter((ev) =>
    polarityFilter === "ALL" ? true : ev.polarity === polarityFilter
  )

  const getPolarityBadge = (polarity: EvidencePolarity) => {
    switch (polarity) {
      case "supporting":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-[#162722] text-verdigris border border-[#234A3E]">
            <CheckCircle2 className="w-3 h-3" />
            <span>SUPPORTING</span>
          </span>
        )
      case "contradicting":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-[#2B1518] text-oxblood border border-[#522127]">
            <XCircle className="w-3 h-3" />
            <span>CONTRADICTING</span>
          </span>
        )
      case "neutral":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-[#211C18] text-dust border border-ash">
            <MinusCircle className="w-3 h-3" />
            <span>NEUTRAL</span>
          </span>
        )
    }
  }

  return (
    <div className="space-y-4">
      {/* Polarity Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-ash/60">
        <div className="flex items-center gap-1.5 p-1 bg-ink/70 border border-ash/70 rounded-md text-xs font-mono">
          {(["ALL", "supporting", "contradicting", "neutral"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setPolarityFilter(tab)}
              className={`px-2.5 py-1 rounded capitalize transition-colors ${
                polarityFilter === tab
                  ? "bg-soot text-bone border border-ash/80 shadow-sm"
                  : "text-dust hover:text-bone border border-transparent"
              }`}
            >
              {tab === "ALL" ? "All Evidence" : tab}
            </button>
          ))}
        </div>

        <span className="text-[11px] font-mono text-dust">
          Showing {filtered.length} evidence items
        </span>
      </div>

      {/* Evidence Items List */}
      <div className="space-y-2.5">
        {filtered.map((item) => {
          const isExpanded = expandedIds.has(item.id)

          return (
            <div
              key={item.id}
              className="rounded-md bg-ink/40 border border-ash/70 hover:border-ash overflow-hidden transition-all text-xs"
            >
              <div
                onClick={() => onToggleExpand(item.id)}
                className="p-3 flex items-center justify-between gap-3 cursor-pointer select-none hover:bg-ink/60 transition-colors"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="text-dust">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </span>
                  <div className="truncate">
                    <span className="font-semibold text-bone">{item.title}</span>
                    <span className="text-dust font-mono text-[11px] ml-2 hidden sm:inline">
                      ({item.source})
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 shrink-0">
                  {item.delta && (
                    <span className="font-mono text-amber text-[11px]">{item.delta}</span>
                  )}
                  {getPolarityBadge(item.polarity)}
                </div>
              </div>

              {isExpanded && (
                <div className="px-4 pb-3.5 pt-1 space-y-2.5 border-t border-ash/40 bg-[#161311]">
                  <p className="text-dust text-xs leading-relaxed">{item.summary}</p>

                  {item.rawSnippet && (
                    <div>
                      <div className="flex items-center gap-1.5 text-[10px] font-mono text-dust mb-1">
                        <Code2 className="w-3 h-3 text-amber" />
                        <span>Source Telemetry Output (Sanitized &amp; Delimited)</span>
                      </div>
                      <pre className="p-2.5 rounded bg-ink border border-ash text-[11px] font-mono text-bone overflow-x-auto whitespace-pre leading-relaxed select-text">
                        {item.rawSnippet}
                      </pre>
                    </div>
                  )}

                  <div className="flex items-center justify-between text-[10px] font-mono text-dust/70 pt-1">
                    <span>Captured at: {item.timestamp}</span>
                    <span>
                      Deterministic Weight: {item.weight > 0 ? `+${item.weight}` : item.weight} pts
                    </span>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
