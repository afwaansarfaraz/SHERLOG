import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import {
  ApiClient,
  ApiTimeoutError,
  ApiRateLimitError,
  ApiAuthError,
  ApiForbiddenError,
  ApiNotFoundError,
  ApiServerError,
  ApiServiceUnavailableError,
  redactSensitiveString,
  redactSensitiveData,
  queryPrometheusTelemetry,
  queryLokiLogs,
  queryJaegerTraces,
} from "../lib/api"

describe("Sherlog Hardened API Client", () => {
  const originalFetch = global.fetch

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    global.fetch = originalFetch
  })

  describe("Sensitive Information Redaction", () => {
    it("redacts bearer tokens and passwords in raw strings", () => {
      const input = "Authorization: Bearer secret-jwt-token-123456 and password=super_secret_pw"
      const redacted = redactSensitiveString(input)
      expect(redacted).not.toContain("secret-jwt-token-123456")
      expect(redacted).not.toContain("super_secret_pw")
      expect(redacted).toContain("Bearer [REDACTED]")
      expect(redacted).toContain("password=[REDACTED]")
    })

    it("redacts sensitive fields in nested objects", () => {
      const payload = {
        username: "operator",
        password: "cleartext_password",
        nested: {
          apiKey: "sk-live-99999",
          normalMetric: 42,
        },
      }
      const sanitized = redactSensitiveData(payload)
      expect(sanitized.password).toBe("[REDACTED]")
      expect(sanitized.nested.apiKey).toBe("[REDACTED]")
      expect(sanitized.nested.normalMetric).toBe(42)
      expect(sanitized.username).toBe("operator")
    })
  })

  describe("Endpoint URL Normalization", () => {
    it("avoids duplicating the baseUrl prefix when endpoint already includes it", async () => {
      let requestedUrl = ""
      global.fetch = vi.fn((url: string) => {
        requestedUrl = url
        return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }))
      }) as unknown as typeof fetch

      const client = new ApiClient("/api")
      await client.get("/api/knowledge")
      expect(requestedUrl).toBe("/api/knowledge")

      await client.get("/knowledge")
      expect(requestedUrl).toBe("/api/knowledge")

      await client.get("http://external-api.com/v1/data")
      expect(requestedUrl).toBe("http://external-api.com/v1/data")
    })
  })

  describe("Authorization Header Handling", () => {
    beforeEach(() => {
      if (typeof localStorage !== "undefined") {
        localStorage.clear()
      }
    })

    afterEach(() => {
      if (typeof localStorage !== "undefined") {
        localStorage.clear()
      }
    })

    it("attaches Authorization header when stored credential exists and URL is API origin", async () => {
      localStorage.setItem("sherlog_token", "my-secret-token")
      let sentHeaders: Headers | undefined
      global.fetch = vi.fn((_url, options?: RequestInit) => {
        sentHeaders = options?.headers as Headers
        return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }))
      }) as unknown as typeof fetch

      const client = new ApiClient("/api")
      await client.get("/incidents")
      expect(sentHeaders?.get("Authorization")).toBe("Bearer my-secret-token")
    })

    it("does not attach Authorization header to cross-origin requests", async () => {
      localStorage.setItem("sherlog_token", "my-secret-token")
      let sentHeaders: Headers | undefined
      global.fetch = vi.fn((_url, options?: RequestInit) => {
        sentHeaders = options?.headers as Headers
        return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }))
      }) as unknown as typeof fetch

      const client = new ApiClient("/api")
      await client.get("http://thirdparty.com/telemetry")
      expect(sentHeaders?.get("Authorization")).toBeNull()
    })

    it("does not treat a protocol-relative URL as the API origin", async () => {
      localStorage.setItem("sherlog_token", "my-secret-token")
      let sentHeaders: Headers | undefined
      global.fetch = vi.fn((_url, options?: RequestInit) => {
        sentHeaders = options?.headers as Headers
        return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }))
      }) as unknown as typeof fetch

      const client = new ApiClient("/api")
      await client.get("//attacker.example/telemetry")
      expect(sentHeaders?.get("Authorization")).toBeNull()
    })

    it("does not attach Authorization header when no stored credential exists", async () => {
      let sentHeaders: Headers | undefined
      global.fetch = vi.fn((_url, options?: RequestInit) => {
        sentHeaders = options?.headers as Headers
        return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }))
      }) as unknown as typeof fetch

      const client = new ApiClient("/api")
      await client.get("/incidents")
      expect(sentHeaders?.get("Authorization")).toBeNull()
    })

    it("respects skipAuth option", async () => {
      localStorage.setItem("sherlog_token", "my-secret-token")
      let sentHeaders: Headers | undefined
      global.fetch = vi.fn((_url, options?: RequestInit) => {
        sentHeaders = options?.headers as Headers
        return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }))
      }) as unknown as typeof fetch

      const client = new ApiClient("/api")
      await client.get("/public", { skipAuth: true })
      expect(sentHeaders?.get("Authorization")).toBeNull()
    })

    it("preserves explicit caller Authorization header", async () => {
      localStorage.setItem("sherlog_token", "stored-token")
      let sentHeaders: Headers | undefined
      global.fetch = vi.fn((_url, options?: RequestInit) => {
        sentHeaders = options?.headers as Headers
        return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }))
      }) as unknown as typeof fetch

      const client = new ApiClient("/api")
      await client.get("/custom", { headers: { Authorization: "Bearer custom-override" } })
      expect(sentHeaders?.get("Authorization")).toBe("Bearer custom-override")
    })
  })

  describe("Timeout Handling", () => {
    it("throws ApiTimeoutError when request duration exceeds timeoutMs", async () => {
      global.fetch = vi.fn((_url, options?: RequestInit) => {
        return new Promise((_, reject) => {
          options?.signal?.addEventListener("abort", () => {
            const err = new DOMException("The operation was aborted", "AbortError")
            reject(err)
          })
        })
      }) as unknown as typeof fetch

      const client = new ApiClient("/api", 100) // 100ms timeout
      await expect(client.get("/slow-query", { timeoutMs: 50 })).rejects.toBeInstanceOf(
        ApiTimeoutError
      )
    })
  })

  describe("HTTP Status Mapping", () => {
    it("maps 401 to ApiAuthError", async () => {
      global.fetch = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ message: "Token expired" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        })
      )
      const client = new ApiClient("/api")
      await expect(client.get("/protected")).rejects.toBeInstanceOf(ApiAuthError)
    })

    it("maps 403 to ApiForbiddenError", async () => {
      global.fetch = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ message: "Admin role required" }), {
          status: 403,
          headers: { "Content-Type": "application/json" },
        })
      )
      const client = new ApiClient("/api")
      await expect(client.get("/admin")).rejects.toBeInstanceOf(ApiForbiddenError)
    })

    it("maps 404 to ApiNotFoundError", async () => {
      global.fetch = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ message: "Incident not found" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        })
      )
      const client = new ApiClient("/api")
      await expect(client.get("/incidents/9999")).rejects.toBeInstanceOf(ApiNotFoundError)
    })

    it("maps 429 to ApiRateLimitError and parses Retry-After header", async () => {
      global.fetch = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ message: "Too many queries" }), {
          status: 429,
          headers: {
            "Content-Type": "application/json",
            "Retry-After": "12",
          },
        })
      )
      const client = new ApiClient("/api")
      try {
        await client.get("/rate-limited", { maxRetries: 0 })
        expect.unreachable("Should have thrown")
      } catch (err) {
        expect(err).toBeInstanceOf(ApiRateLimitError)
        expect((err as ApiRateLimitError).retryAfterSeconds).toBe(12)
      }
    })

    it("maps 503 to ApiServiceUnavailableError and detects maintenance mode", async () => {
      global.fetch = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ maintenance: true, message: "System maintenance window" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        })
      )
      const client = new ApiClient("/api")
      try {
        await client.get("/status", { maxRetries: 0 })
        expect.unreachable("Should have thrown")
      } catch (err) {
        expect(err).toBeInstanceOf(ApiServiceUnavailableError)
        expect((err as ApiServiceUnavailableError).isMaintenance).toBe(true)
      }
    })
  })

  describe("Mutation Safety & Bounded Retries", () => {
    it("NEVER automatically retries non-idempotent POST mutations", async () => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        return Promise.resolve(
          new Response(JSON.stringify({ error: "Upstream failure" }), { status: 500 })
        )
      })

      const client = new ApiClient("/api")
      await expect(client.post("/remediations/apply", { patch: true })).rejects.toBeInstanceOf(
        ApiServerError
      )
      // Exactly 1 attempt - zero retries on mutation
      expect(callCount).toBe(1)
    })

    it("performs bounded retries on idempotent GET requests with server errors", async () => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount < 2) {
          return Promise.resolve(
            new Response(JSON.stringify({ error: "Transient gateway error" }), { status: 502 })
          )
        }
        return Promise.resolve(
          new Response(JSON.stringify({ status: "healthy" }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        )
      })

      const client = new ApiClient("/api")
      const result = await client.get<{ status: string }>("/health", {
        maxRetries: 2,
        retryDelayMs: 10,
      })
      expect(result.status).toBe("healthy")
      expect(callCount).toBe(2)
    })
  })

  describe("Inflight Request Deduplication", () => {
    it("deduplicates concurrent identical GET calls to a single network invocation", async () => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve(
              new Response(JSON.stringify({ data: "shared-response" }), {
                status: 200,
                headers: { "Content-Type": "application/json" },
              })
            )
          }, 30)
        })
      })

      const client = new ApiClient("/api")
      const [res1, res2] = await Promise.all([
        client.get("/metrics/concurrent-1"),
        client.get("/metrics/concurrent-1"),
      ])

      expect(res1).toEqual({ data: "shared-response" })
      expect(res2).toEqual({ data: "shared-response" })
      expect(callCount).toBe(1)
    })
  })

  describe("Observability Telemetry Isolation", () => {
    it("queries Prometheus and returns empty status without fabricating fake data", async () => {
      const mockClient = {
        get: vi.fn().mockResolvedValue({ data: { result: [] } }),
      } as unknown as ApiClient

      const result = await queryPrometheusTelemetry("orders_http_errors", mockClient)
      expect(result.status).toBe("empty")
      expect(result.data).toBeNull()
      expect(result.source).toBe("prometheus")
    })

    it("handles Prometheus query failure gracefully with explicit error state", async () => {
      const mockClient = {
        get: vi.fn().mockRejectedValue(new Error("Connection refused to Prometheus on port 9090")),
      } as unknown as ApiClient

      const result = await queryPrometheusTelemetry("orders_http_errors", mockClient)
      expect(result.status).toBe("error")
      expect(result.error).toContain("Connection refused")
      expect(result.data).toBeNull()
    })

    it("handles Loki log query failure independently", async () => {
      const mockClient = {
        get: vi.fn().mockRejectedValue(new Error("Loki chunk timeout")),
      } as unknown as ApiClient

      const result = await queryLokiLogs("{app='orders'}", mockClient)
      expect(result.status).toBe("error")
      expect(result.source).toBe("loki")
      expect(result.error).toContain("Loki chunk timeout")
    })

    it("handles Jaeger trace query failure independently", async () => {
      const mockClient = {
        get: vi.fn().mockRejectedValue(new Error("Trace ID 8f4a210bc931e4 not found in memory store")),
      } as unknown as ApiClient

      const result = await queryJaegerTraces("8f4a210bc931e4", mockClient)
      expect(result.status).toBe("error")
      expect(result.source).toBe("jaeger")
    })
  })
})
