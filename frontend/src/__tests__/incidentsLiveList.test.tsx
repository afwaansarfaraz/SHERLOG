import { afterEach, describe, expect, it, vi } from "vitest"
import { act, render, screen, waitFor } from "@testing-library/react"
import { GenericTabView } from "../components/views/GenericTabViews"
import { api } from "../lib/api"

describe("live incident list", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("renders persisted incidents returned by the incidents API", async () => {
    const incident = {
      id: "INC-00027",
      title: "Orders slow database query latency",
      service: "orders",
      severity: "MEDIUM",
      status: "OPEN",
      summary: "Observed an increase in slow query telemetry from Orders.",
      created_at: "2026-10-22T10:00:00Z",
    }
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => [incident],
    } as Response)

    render(<GenericTabView tab="incidents" onBackToOverview={vi.fn()} />)

    expect(await screen.findByText("INC-00027")).toBeInTheDocument()
    expect(screen.getByText("Orders slow database query latency")).toBeInTheDocument()
    expect(screen.queryByText("INC-00237")).not.toBeInTheDocument()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/incidents",
      expect.objectContaining({ method: "GET" }),
    ))
  })

  it("ignores an older incidents response after navigating away and back", async () => {
    const pending: Array<(value: any) => void> = []
    vi.spyOn(api, "get").mockImplementation((async () =>
      new Promise<any>((resolve) => pending.push(resolve))) as typeof api.get)
    const props = { onBackToOverview: vi.fn() }
    const { rerender } = render(<GenericTabView tab="incidents" {...props} />)
    await waitFor(() => expect(pending).toHaveLength(1))

    rerender(<GenericTabView tab="overview" {...props} />)
    rerender(<GenericTabView tab="incidents" {...props} />)
    await waitFor(() => expect(pending).toHaveLength(2))

    await act(async () => {
      pending[1]([{
        id: "INC-LATEST", title: "Latest incident", service: "orders", severity: "HIGH",
        status: "OPEN", summary: "New response", created_at: "2026-10-23T00:00:00Z",
      }])
    })
    expect(await screen.findByText("Latest incident")).toBeInTheDocument()

    await act(async () => {
      pending[0]([{
        id: "INC-STALE", title: "Stale incident", service: "orders", severity: "HIGH",
        status: "OPEN", summary: "Old response", created_at: "2026-10-22T00:00:00Z",
      }])
    })
    expect(screen.queryByText("Stale incident")).not.toBeInTheDocument()
    expect(screen.getByText("Latest incident")).toBeInTheDocument()
  })
})
