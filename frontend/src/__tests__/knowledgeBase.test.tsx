import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { KnowledgeBase } from "../components/views/KnowledgeBase"

describe("KnowledgeBase Component", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("loads and displays the document list successfully without a 502", async () => {
    const mockDocuments = [
      {
        id: "doc-1",
        doc_id: "runbook:slow_query",
        title: "Runbook: Slow Database Queries",
        doc_type: "runbook",
        service: "orders",
        source: "docs/runbooks/slow_query.md",
        status: "indexed",
        chunk_count: 5,
        error_message: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: "doc-2",
        doc_id: "runbook:pool_exhaustion",
        title: "Runbook: DB Pool Exhaustion",
        doc_type: "runbook",
        service: "orders",
        source: "docs/runbooks/db_pool.md",
        status: "indexed",
        chunk_count: 4,
        error_message: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: () => Promise.resolve(mockDocuments),
      text: () => Promise.resolve(JSON.stringify(mockDocuments)),
    } as unknown as Response)

    render(<KnowledgeBase onBackToOverview={vi.fn()} />)

    // Should show loading initially
    expect(screen.getByText(/Operational Knowledge & Runbooks/i)).toBeInTheDocument()

    // Await documents rendered
    await waitFor(() => {
      expect(screen.getByText("Runbook: Slow Database Queries")).toBeInTheDocument()
      expect(screen.getByText("Runbook: DB Pool Exhaustion")).toBeInTheDocument()
    })

    expect(screen.getByText(/INDEXED · 5 chunks/i)).toBeInTheDocument()
    expect(screen.getByText(/INDEXED · 4 chunks/i)).toBeInTheDocument()
  })

  it("handles empty knowledge base gracefully", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: () => Promise.resolve([]),
      text: () => Promise.resolve("[]"),
    } as unknown as Response)

    render(<KnowledgeBase onBackToOverview={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText(/No Documents Indexed/i)).toBeInTheDocument()
    })
  })
})
