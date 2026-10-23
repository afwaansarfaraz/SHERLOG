/**
 * KnowledgeBase — Operational Knowledge & Runbooks management screen.
 *
 * Provides: document listing with status badges, file upload (MD/TXT/PDF),
 * retry failed ingestion, delete documents, and document detail expansion.
 * Connected to backend /api/knowledge endpoints.
 */

import React, { useState, useEffect, useCallback, useRef } from "react"
import {
  BookOpen,
  Upload,
  FileText,
  RefreshCw,
  Trash2,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ArrowLeft,
  X,
  Layers,
} from "lucide-react"
import { Card, CardHeader, CardTitle } from "../common/Card"
import { Badge } from "../common/Badge"
import { Button } from "../common/Button"
import { EmptyState } from "../common/EmptyState"
import { api } from "../../lib/api"

// ============================================================================
// Types
// ============================================================================

interface KnowledgeDocument {
  id: string
  doc_id: string
  title: string
  doc_type: string
  service: string
  source: string
  status: string
  chunk_count: number
  error_message: string | null
  created_at: string
  updated_at: string
}

interface KnowledgeChunk {
  id: string
  chunk_index: number
  title: string
  content_preview: string
  service: string
  embedding_model: string
}

interface DocumentDetail extends KnowledgeDocument {
  raw_content_preview: string
  chunks: KnowledgeChunk[]
  metadata: Record<string, unknown>
}

// ============================================================================
// Props
// ============================================================================

interface KnowledgeBaseProps {
  onBackToOverview: () => void
}

// ============================================================================
// Component
// ============================================================================

export const KnowledgeBase: React.FC<KnowledgeBaseProps> = ({ onBackToOverview }) => {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null)
  const [docDetail, setDocDetail] = useState<DocumentDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [filterType, setFilterType] = useState<"all" | "builtin" | "uploaded">("all")

  // Upload state
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Action loading state
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)

  // ===========================================================================
  // Data Fetching
  // ===========================================================================

  const fetchDocuments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<KnowledgeDocument[]>("/api/knowledge")
      setDocuments(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents")
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  const fetchDocumentDetail = useCallback(async (docId: string) => {
    setDetailLoading(true)
    try {
      const data = await api.get<DocumentDetail>(`/api/knowledge/${encodeURIComponent(docId)}`)
      setDocDetail(data)
    } catch {
      setDocDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }, [])

  // ===========================================================================
  // Actions
  // ===========================================================================

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true)
    setUploadError(null)
    setUploadSuccess(null)

    const formData = new FormData()
    formData.append("file", file)

    try {
      const result = await api.request<{ message: string }>("/api/knowledge/upload", {
        method: "POST",
        body: formData,
      })
      setUploadSuccess(result.message || `Uploaded ${file.name} successfully`)
      fetchDocuments()
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
    }
  }, [fetchDocuments])

  const handleRetry = useCallback(async (docId: string) => {
    setActionLoadingId(docId)
    try {
      await api.post(`/api/knowledge/${encodeURIComponent(docId)}/retry`)
      fetchDocuments()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retry failed")
    } finally {
      setActionLoadingId(null)
    }
  }, [fetchDocuments])

  const handleDelete = useCallback(async (docId: string) => {
    setActionLoadingId(docId)
    try {
      await api.delete(`/api/knowledge/${encodeURIComponent(docId)}`)
      if (expandedDocId === docId) {
        setExpandedDocId(null)
        setDocDetail(null)
      }
      fetchDocuments()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed")
    } finally {
      setActionLoadingId(null)
    }
  }, [expandedDocId, fetchDocuments])

  const toggleExpand = useCallback((docId: string) => {
    if (expandedDocId === docId) {
      setExpandedDocId(null)
      setDocDetail(null)
    } else {
      setExpandedDocId(docId)
      fetchDocumentDetail(docId)
    }
  }, [expandedDocId, fetchDocumentDetail])

  const onFileSelected = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleUpload(file)
      e.target.value = "" // Reset for re-upload
    }
  }, [handleUpload])

  // ===========================================================================
  // Render Helpers
  // ===========================================================================

  const statusBadge = (doc: KnowledgeDocument) => {
    if (doc.status === "indexed" && doc.chunk_count > 0) {
      return <Badge variant="resolved" withDot>INDEXED · {doc.chunk_count} chunks</Badge>
    }
    if (doc.status === "failed") {
      return <Badge variant="critical" withDot>FAILED</Badge>
    }
    if (doc.status === "processing") {
      return <Badge variant="investigating" withDot>PROCESSING</Badge>
    }
    return <Badge variant="default" withDot>EMPTY</Badge>
  }

  const docTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      runbook: "Runbook",
      architecture: "Architecture",
      service_doc: "Service Doc",
      historical_incident: "Postmortem",
    }
    return labels[type] || type
  }

  // ===========================================================================
  // Render
  // ===========================================================================

  return (
    <div className="space-y-5 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBackToOverview}>
            <ArrowLeft className="w-4 h-4 mr-1" /> Overview
          </Button>
          <h2 className="text-xl font-semibold text-bone">Operational Knowledge & Runbooks</h2>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={fetchDocuments} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 mr-1 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? (
              <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
            ) : (
              <Upload className="w-3.5 h-3.5 mr-1" />
            )}
            {uploading ? "Uploading…" : "Upload Document"}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".md,.txt,.pdf,.markdown"
            className="hidden"
            onChange={onFileSelected}
          />
        </div>
      </div>

      {/* Upload feedback banners */}
      {uploadSuccess && (
        <div className="flex items-center gap-2 px-3 py-2 rounded bg-[#162722] border border-[#234A3E] text-verdigris text-xs">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{uploadSuccess}</span>
          <button onClick={() => setUploadSuccess(null)} className="ml-auto text-dust hover:text-bone">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
      {uploadError && (
        <div className="flex items-center gap-2 px-3 py-2 rounded bg-[#2E1618] border border-[#572124] text-vermilion text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{uploadError}</span>
          <button onClick={() => setUploadError(null)} className="ml-auto text-dust hover:text-bone">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="flex items-center gap-2 px-3 py-2 rounded bg-[#2E1618] border border-[#572124] text-vermilion text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={fetchDocuments} className="ml-auto">
            Retry
          </Button>
        </div>
      )}

      {/* KPI Metrics Cards: Distinct Counts for Built-in Runbooks, Uploaded Docs, and Indexed Chunks */}
      {!loading && documents.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div
            onClick={() => setFilterType("builtin")}
            className={`p-4 rounded-lg bg-soot/80 border transition-all cursor-pointer ${
              filterType === "builtin"
                ? "border-amber shadow-[0_0_12px_rgba(245,158,11,0.15)]"
                : "border-ash hover:border-ash/80"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider text-dust">Built-in Runbooks</span>
              <BookOpen className="w-4 h-4 text-amber" />
            </div>
            <div className="mt-2 text-2xl font-semibold text-bone font-mono">
              {documents.filter((d) => d.doc_id.startsWith("runbook:")).length}
            </div>
            <p className="mt-1 text-[11px] text-dust">
              Standard operational failure categories, reusable across all connected applications.
            </p>
          </div>

          <div
            onClick={() => setFilterType("uploaded")}
            className={`p-4 rounded-lg bg-soot/80 border transition-all cursor-pointer ${
              filterType === "uploaded"
                ? "border-verdigris shadow-[0_0_12px_rgba(20,184,166,0.15)]"
                : "border-ash hover:border-ash/80"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider text-dust">Uploaded Documents</span>
              <Upload className="w-4 h-4 text-verdigris" />
            </div>
            <div className="mt-2 text-2xl font-semibold text-bone font-mono">
              {documents.filter((d) => !d.doc_id.startsWith("runbook:")).length}
            </div>
            <p className="mt-1 text-[11px] text-dust">
              Custom tenant runbooks, architectural specs, and postmortems preserved in storage.
            </p>
          </div>

          <div
            onClick={() => setFilterType("all")}
            className={`p-4 rounded-lg bg-soot/80 border transition-all cursor-pointer ${
              filterType === "all"
                ? "border-bone/60 shadow-[0_0_12px_rgba(255,255,255,0.08)]"
                : "border-ash hover:border-ash/80"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider text-dust">Indexed Chunks</span>
              <Layers className="w-4 h-4 text-bone/70" />
            </div>
            <div className="mt-2 text-2xl font-semibold text-bone font-mono">
              {documents.reduce((sum, d) => sum + (d.chunk_count || 0), 0)}
            </div>
            <p className="mt-1 text-[11px] text-dust">
              Vector-embedded semantic chunks ready for real-time investigation retrieval.
            </p>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      {!loading && documents.length > 0 && (
        <div className="flex items-center gap-2 border-b border-ash/50 pb-2">
          <button
            onClick={() => setFilterType("all")}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              filterType === "all"
                ? "bg-ash/70 text-bone"
                : "text-dust hover:text-bone hover:bg-ink/40"
            }`}
          >
            All Documents ({documents.length})
          </button>
          <button
            onClick={() => setFilterType("builtin")}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              filterType === "builtin"
                ? "bg-amber/20 text-amber border border-amber/40"
                : "text-dust hover:text-bone hover:bg-ink/40"
            }`}
          >
            Built-in Runbooks ({documents.filter((d) => d.doc_id.startsWith("runbook:")).length})
          </button>
          <button
            onClick={() => setFilterType("uploaded")}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              filterType === "uploaded"
                ? "bg-verdigris/20 text-verdigris border border-verdigris/40"
                : "text-dust hover:text-bone hover:bg-ink/40"
            }`}
          >
            Uploaded Documents ({documents.filter((d) => !d.doc_id.startsWith("runbook:")).length})
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <Card className="p-8 flex flex-col items-center justify-center text-center space-y-3 min-h-[200px]">
          <Loader2 className="w-8 h-8 text-amber animate-spin" />
          <p className="text-xs text-dust">Loading knowledge base documents…</p>
        </Card>
      )}

      {/* Empty State */}
      {!loading && !error && documents.length === 0 && (
        <EmptyState
          variant="custom"
          icon={BookOpen}
          title="No Documents Indexed"
          description="Upload operational runbooks, architecture documentation, or postmortems to build the knowledge base. Documents are chunked and embedded for AI-powered retrieval during investigations."
          actionLabel="Upload First Document"
          onAction={() => fileInputRef.current?.click()}
        />
      )}

      {/* Document List */}
      {!loading && documents.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>
              <BookOpen className="w-4 h-4 text-amber" />
              <span>
                {filterType === "builtin"
                  ? "Built-in Operational Runbooks"
                  : filterType === "uploaded"
                  ? "User Uploaded Documents"
                  : "All Indexed Documents"}
              </span>
              <span className="ml-auto font-mono text-xs text-dust font-normal">
                {
                  documents.filter((d) => {
                    if (filterType === "builtin") return d.doc_id.startsWith("runbook:")
                    if (filterType === "uploaded") return !d.doc_id.startsWith("runbook:")
                    return true
                  }).length
                }{" "}
                document(s)
              </span>
            </CardTitle>
          </CardHeader>

          <div className="divide-y divide-ash/60">
            {documents
              .filter((d) => {
                if (filterType === "builtin") return d.doc_id.startsWith("runbook:")
                if (filterType === "uploaded") return !d.doc_id.startsWith("runbook:")
                return true
              })
              .map((doc) => {
              const isExpanded = expandedDocId === doc.doc_id
              const isActionLoading = actionLoadingId === doc.doc_id
              const isBuiltIn = doc.doc_id.startsWith("runbook:")

              return (
                <div key={doc.id}>
                  {/* Document Row */}
                  <div
                    className="py-3 px-3 flex items-center gap-3 hover:bg-ink/50 transition-colors cursor-pointer rounded"
                    onClick={() => toggleExpand(doc.doc_id)}
                  >
                    <div className="text-dust shrink-0">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </div>

                    <div className="w-8 h-8 rounded bg-[#27211B] border border-ash flex items-center justify-center shrink-0">
                      <FileText className={`w-4 h-4 ${isBuiltIn ? "text-amber" : "text-verdigris"}`} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-bone truncate">
                          {doc.title}
                        </span>
                        {isBuiltIn ? (
                          <Badge variant="awaiting_approval" withDot>BUILT-IN RUNBOOK</Badge>
                        ) : (
                          <Badge variant="healthy" withDot>USER UPLOAD</Badge>
                        )}
                        {statusBadge(doc)}
                        <Badge variant="slate">{docTypeLabel(doc.doc_type)}</Badge>
                      </div>
                      <div className="flex items-center gap-3 mt-0.5">
                        <span className="text-[10px] text-dust font-mono">{doc.doc_id}</span>
                        <span className="text-[10px] text-dust">service: {doc.service}</span>
                        <span className="text-[10px] text-dust">
                          {new Date(doc.updated_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div
                      className="flex items-center gap-1 shrink-0"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={() => handleRetry(doc.doc_id)}
                        disabled={isActionLoading}
                        title="Retry ingestion"
                        className="p-1.5 rounded text-dust hover:text-bone hover:bg-soot transition-colors disabled:opacity-50"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${isActionLoading ? "animate-spin" : ""}`} />
                      </button>
                      <button
                        onClick={() => handleDelete(doc.doc_id)}
                        disabled={isActionLoading}
                        title="Delete document"
                        className="p-1.5 rounded text-dust hover:text-vermilion hover:bg-[#2E1618] transition-colors disabled:opacity-50"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Expanded Detail */}
                  {isExpanded && (
                    <div className="px-6 pb-4 space-y-3 border-t border-ash/40 bg-ink/30 ml-4 mr-3 rounded-b">
                      {detailLoading ? (
                        <div className="py-6 flex items-center justify-center">
                          <Loader2 className="w-5 h-5 text-amber animate-spin mr-2" />
                          <span className="text-xs text-dust">Loading document details…</span>
                        </div>
                      ) : docDetail ? (
                        <>
                          {/* Content Preview */}
                          {docDetail.raw_content_preview && (
                            <div className="mt-3">
                              <h4 className="text-[11px] font-mono uppercase tracking-wider text-dust mb-1.5">
                                Content Preview
                              </h4>
                              <pre className="text-xs text-bone/80 bg-ink/60 border border-ash/50 rounded p-3 font-mono leading-relaxed overflow-auto max-h-40 whitespace-pre-wrap">
                                {docDetail.raw_content_preview}
                              </pre>
                            </div>
                          )}

                          {/* Chunks */}
                          {docDetail.chunks.length > 0 && (
                            <div>
                              <h4 className="text-[11px] font-mono uppercase tracking-wider text-dust mb-1.5">
                                Vector Chunks ({docDetail.chunks.length})
                              </h4>
                              <div className="space-y-2 max-h-60 overflow-y-auto">
                                {docDetail.chunks.map((chunk) => (
                                  <div
                                    key={chunk.id}
                                    className="p-2.5 bg-soot/70 border border-ash/50 rounded text-xs"
                                  >
                                    <div className="flex items-center justify-between mb-1">
                                      <span className="text-bone font-medium text-[11px]">
                                        #{chunk.chunk_index} — {chunk.title}
                                      </span>
                                      <span className="text-[10px] text-dust font-mono">
                                        {chunk.embedding_model}
                                      </span>
                                    </div>
                                    <p className="text-dust leading-relaxed">
                                      {chunk.content_preview}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </>
                      ) : (
                        <p className="text-xs text-dust py-3">Unable to load document details.</p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {/* Footer Info */}
      <div className="text-center">
        <span className="px-2.5 py-1 rounded bg-[#27211B] text-dust text-[11px] font-mono border border-ash">
          RAG-indexed documents are used as context during AI-powered incident investigations
        </span>
      </div>
    </div>
  )
}
