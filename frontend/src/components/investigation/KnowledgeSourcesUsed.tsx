import React, { useState } from "react"
import {
  BookOpen,
  CheckCircle2,
  Clock,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  FileText,
  Search,
} from "lucide-react"
import type { KnowledgeSource } from "../../types"

interface KnowledgeSourcesUsedProps {
  sources?: KnowledgeSource[]
  retrievalStatus?: string
  incidentService?: string
}

export const KnowledgeSourcesUsed: React.FC<KnowledgeSourcesUsedProps> = ({
  sources = [],
  retrievalStatus = "NOT_ATTEMPTED",
  incidentService = "orders",
}) => {
  const [expandedDocIds, setExpandedDocIds] = useState<Set<string>>(new Set())

  const toggleExpand = (id: string) => {
    setExpandedDocIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const effectiveStatus = retrievalStatus || (sources.length > 0 ? "SUCCESS" : "NO_DOCUMENTS_FOUND")

  const includedCount = sources.filter((s) => s.included_in_context).length

  return (
    <div className="space-y-3 pt-3 border-t border-ash/70" data-testid="knowledge-sources-used">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-verdigris" />
          <h4 className="text-xs font-semibold text-bone uppercase tracking-wider font-mono">
            Knowledge Sources Used
          </h4>
          {sources.length > 0 && (
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#162722] text-verdigris border border-[#234A3E]">
              {sources.length} {sources.length === 1 ? "runbook" : "runbooks"} retrieved
            </span>
          )}
        </div>

        {/* Global RAG Status Badge */}
        <div className="flex items-center gap-2">
          {effectiveStatus === "SUCCESS" && (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#162722] text-verdigris border border-[#234A3E]">
              <span className="w-1.5 h-1.5 rounded-full bg-verdigris animate-pulse" />
              RAG Retrieval Active ({includedCount} in context)
            </span>
          )}
          {effectiveStatus === "NO_DOCUMENTS_FOUND" && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#241B1C] text-dust border border-ash/80">
              <Search className="w-3 h-3 text-dust" />
              No relevant documents found
            </span>
          )}
          {effectiveStatus === "DISABLED" && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#291F13] text-amber border border-[#4A391A]">
              Vector RAG Disabled
            </span>
          )}
          {effectiveStatus === "FAILED" && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#331317] text-crimson border border-[#521820]">
              <AlertTriangle className="w-3 h-3 text-crimson" />
              Retrieval Failed
            </span>
          )}
        </div>
      </div>

      <p className="text-[11px] text-dust">
        Operational runbooks, architecture specs, and postmortems retrieved via vector similarity search to ground the investigation.
      </p>

      {/* Case 1: Retrieval Failed */}
      {effectiveStatus === "FAILED" && (
        <div className="p-3 bg-[#331317]/50 border border-crimson/50 rounded-md flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-crimson shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-semibold text-crimson">Knowledge Retrieval Unavailable</span>
            <p className="text-dust text-[11px]">
              The vector knowledge store encountered an error during similarity search. The investigation proceeded with deterministic baseline evidence.
            </p>
          </div>
        </div>
      )}

      {/* Case 2: No relevant documents found */}
      {effectiveStatus === "NO_DOCUMENTS_FOUND" && sources.length === 0 && (
        <div className="p-4 bg-ink/70 border border-ash/80 rounded-md text-center space-y-2">
          <FileText className="w-6 h-6 text-dust/60 mx-auto" />
          <div className="text-xs font-medium text-bone">No relevant documents found</div>
          <p className="text-[11px] text-dust max-w-md mx-auto">
            No knowledge base documents or runbooks matched service &ldquo;{incidentService}&rdquo; above the similarity threshold. Ingest service runbooks in the Knowledge Base to enable AI grounding.
          </p>
        </div>
      )}

      {/* Case 3: Sources Retrieved and Displayed */}
      {sources.length > 0 && (
        <div className="space-y-2.5">
          {sources.map((source, index) => {
            const docKey = source.chunk_id || source.doc_id || `source-${index}`
            const isExpanded = expandedDocIds.has(docKey)
            const similarityPercent = source.similarity_score
              ? Math.round(source.similarity_score * 100)
              : null

            return (
              <div
                key={docKey}
                className={`p-3 rounded-md border transition-all ${
                  source.included_in_context
                    ? "bg-soot/90 border-[#234A3E]/70 hover:border-verdigris/50"
                    : "bg-ink/60 border-ash/70 opacity-80 hover:opacity-100"
                }`}
              >
                {/* Top line: Rank, Title, and Context Inclusion Badge */}
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="flex items-start gap-2 min-w-0">
                    <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-ink border border-ash/80 text-bone">
                      #{source.rank ?? index + 1}
                    </span>

                    <div>
                      <h5 className="text-xs font-semibold text-bone hover:text-verdigris transition-colors break-words flex items-center gap-1.5">
                        {source.title}
                      </h5>
                      <div className="flex flex-wrap items-center gap-2 mt-0.5 text-[10px] font-mono text-dust">
                        <span>Doc ID: {source.doc_id}</span>
                        {source.chunk_id && (
                          <span>• Chunk: {source.chunk_id.slice(0, 8)}</span>
                        )}
                        {source.service && (
                          <span>• Service: {source.service}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Badges: Context Status & Similarity */}
                  <div className="flex items-center gap-1.5 shrink-0">
                    {similarityPercent !== null && (
                      <span
                        className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-ink border border-ash/80 text-bone"
                        title={`Cosine Similarity: ${source.similarity_score}`}
                      >
                        {similarityPercent}% match
                      </span>
                    )}

                    {source.included_in_context ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#162722] text-verdigris border border-[#234A3E]">
                        <CheckCircle2 className="w-3 h-3 text-verdigris" />
                        Included in AI Context
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#291F13] text-amber border border-[#4A391A]">
                        <Clock className="w-3 h-3 text-amber" />
                        Retrieved but not used
                      </span>
                    )}
                  </div>
                </div>

                {/* Relevance Substantiation */}
                {source.why_relevant && (
                  <div className="mt-2 text-[11px] text-bone/90 bg-ink/70 px-2.5 py-1.5 rounded border border-ash/50 flex items-start gap-1.5">
                    <span className="text-[10px] font-mono font-semibold text-verdigris uppercase tracking-wider shrink-0 mt-0.5">
                      Relevance:
                    </span>
                    <span>{source.why_relevant}</span>
                  </div>
                )}

                {/* Excerpt Box */}
                <div className="mt-2.5">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-dust">
                      Retrieved Runbook Excerpt
                    </span>
                    <button
                      onClick={() => toggleExpand(docKey)}
                      className="text-[10px] font-mono text-dust hover:text-bone flex items-center gap-1 transition-colors cursor-pointer"
                    >
                      {isExpanded ? (
                        <>
                          <span>Collapse</span>
                          <ChevronUp className="w-3 h-3" />
                        </>
                      ) : (
                        <>
                          <span>Show full excerpt</span>
                          <ChevronDown className="w-3 h-3" />
                        </>
                      )}
                    </button>
                  </div>

                  <div
                    className={`p-2.5 bg-ink border-l-2 border-verdigris/80 border border-ash/60 rounded-r-md text-[11px] font-mono text-dust/90 leading-relaxed whitespace-pre-wrap ${
                      isExpanded ? "max-h-96 overflow-y-auto" : "line-clamp-3"
                    }`}
                  >
                    {source.excerpt}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
