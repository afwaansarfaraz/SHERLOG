import { describe, it, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { KnowledgeSourcesUsed } from "../components/investigation/KnowledgeSourcesUsed"
import type { KnowledgeSource } from "../types"

describe("KnowledgeSourcesUsed Component", () => {
  const mockSources: KnowledgeSource[] = [
    {
      doc_id: "upload:9f058f10ea53",
      chunk_id: "d782975a-6ae0-4fe9-9ef5-84c623b4346b",
      title: "Sherlog Demo Database Pool Exhaustion Runbook",
      source: "runbooks/database_pool_exhaustion.md",
      service: "orders",
      excerpt: "Active connections exceed limit. Resolution: Scale database pool connections to 40.",
      similarity_score: 0.81,
      rank: 1,
      included_in_context: true,
      why_relevant: "Matched orders connection saturation symptoms directly.",
    },
    {
      doc_id: "runbook:slow_query_tuning",
      chunk_id: "c84112e4-99b2-4d91-88d4-5399712a1f81",
      title: "Runbook: Slow Database Query Optimization",
      source: "runbooks/slow_queries.md",
      service: "orders",
      excerpt: "Check pg_stat_statements for top queries by latency.",
      similarity_score: 0.62,
      rank: 2,
      included_in_context: false,
      why_relevant: "Considered as secondary candidate.",
    },
  ]

  it("renders the Knowledge Sources Used heading and runbook count", () => {
    render(<KnowledgeSourcesUsed sources={mockSources} retrievalStatus="SUCCESS" />)

    expect(screen.getByText("Knowledge Sources Used")).toBeInTheDocument()
    expect(screen.getByText("2 runbooks retrieved")).toBeInTheDocument()
  })

  it("distinguishes between included in context and retrieved but not used", () => {
    render(<KnowledgeSourcesUsed sources={mockSources} retrievalStatus="SUCCESS" />)

    expect(screen.getByText("Included in AI Context")).toBeInTheDocument()
    expect(screen.getByText("Retrieved but not used")).toBeInTheDocument()
  })

  it("displays runbook title, excerpt, similarity score, and why relevant", () => {
    render(<KnowledgeSourcesUsed sources={mockSources} retrievalStatus="SUCCESS" />)

    expect(screen.getByText("Sherlog Demo Database Pool Exhaustion Runbook")).toBeInTheDocument()
    expect(screen.getByText(/Active connections exceed limit/i)).toBeInTheDocument()
    expect(screen.getByText("81% match")).toBeInTheDocument()
    expect(screen.getByText("Matched orders connection saturation symptoms directly.")).toBeInTheDocument()
  })

  it("displays empty state when no relevant documents found", () => {
    render(<KnowledgeSourcesUsed sources={[]} retrievalStatus="NO_DOCUMENTS_FOUND" incidentService="payments" />)

    expect(screen.getAllByText("No relevant documents found").length).toBe(2)
    expect(screen.getByText(/No knowledge base documents or runbooks matched service/i)).toBeInTheDocument()
  })

  it("displays error banner when retrieval fails", () => {
    render(<KnowledgeSourcesUsed sources={[]} retrievalStatus="FAILED" />)

    expect(screen.getByText("Knowledge Retrieval Unavailable")).toBeInTheDocument()
    expect(screen.getByText("Retrieval Failed")).toBeInTheDocument()
  })

  it("toggles excerpt expansion when Show full excerpt is clicked", () => {
    render(<KnowledgeSourcesUsed sources={mockSources} retrievalStatus="SUCCESS" />)

    const toggleButtons = screen.getAllByText("Show full excerpt")
    expect(toggleButtons.length).toBeGreaterThan(0)
    fireEvent.click(toggleButtons[0])
    expect(screen.getByText("Collapse")).toBeInTheDocument()
  })
})
