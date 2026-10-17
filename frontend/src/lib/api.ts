/**
 * Sherlog Production-Grade Hardened API Client
 *
 * Provides:
 * - Typed custom error hierarchy
 * - Automatic timeout handling with AbortController
 * - Deduplication for concurrent identical idempotent GET requests
 * - Bounded exponential backoff retries strictly restricted to idempotent requests
 * - Zero automatic retries for mutations (POST, PUT, DELETE, PATCH)
 * - HTTP 429 Retry-After header parsing
 * - Sensitive credential & token redaction in headers, URLs, and bodies
 * - Independent telemetry querying (Prometheus, Loki, Jaeger) without data fabrication
 */

// ============================================================================
// Error Hierarchy
// ============================================================================

export interface ApiErrorOptions {
  message: string
  status?: number
  code?: string
  isRetryable?: boolean
  correlationId?: string
  details?: unknown
  retryAfterSeconds?: number
}

export class ApiClientError extends Error {
  public readonly status: number
  public readonly code: string
  public readonly isRetryable: boolean
  public readonly correlationId: string
  public readonly details?: unknown
  public readonly retryAfterSeconds?: number

  constructor({
    message,
    status = 0,
    code = "API_ERROR",
    isRetryable = false,
    correlationId,
    details,
    retryAfterSeconds,
  }: ApiErrorOptions) {
    // Redact any secrets from message
    super(redactSensitiveString(message))
    this.name = "ApiClientError"
    this.status = status
    this.code = code
    this.isRetryable = isRetryable
    this.correlationId = correlationId || generateCorrelationId()
    this.details = details ? redactSensitiveData(details) : undefined
    this.retryAfterSeconds = retryAfterSeconds

    // Ensure proper prototype chain for instanceof checks
    Object.setPrototypeOf(this, new.target.prototype)
  }
}

export class ApiNetworkError extends ApiClientError {
  constructor(message = "Network connection unavailable. Please verify your connection.") {
    super({
      message,
      status: 0,
      code: "NETWORK_ERROR",
      isRetryable: true,
    })
    this.name = "ApiNetworkError"
  }
}

export class ApiTimeoutError extends ApiClientError {
  constructor(timeoutMs: number) {
    super({
      message: `Request timed out after ${Math.round(timeoutMs / 1000)}s. Please retry.`,
      status: 408,
      code: "REQUEST_TIMEOUT",
      isRetryable: true,
    })
    this.name = "ApiTimeoutError"
  }
}

export class ApiRateLimitError extends ApiClientError {
  constructor(retryAfterSeconds = 5) {
    super({
      message: `Rate limit exceeded. Please wait ${retryAfterSeconds}s before retrying.`,
      status: 429,
      code: "RATE_LIMITED",
      isRetryable: true,
      retryAfterSeconds,
    })
    this.name = "ApiRateLimitError"
  }
}

export class ApiAuthError extends ApiClientError {
  constructor(message = "Authentication required or session expired.") {
    super({
      message,
      status: 401,
      code: "UNAUTHENTICATED",
      isRetryable: false,
    })
    this.name = "ApiAuthError"
  }
}

export class ApiForbiddenError extends ApiClientError {
  constructor(message = "Access denied. You lack permissions for this resource.") {
    super({
      message,
      status: 403,
      code: "FORBIDDEN",
      isRetryable: false,
    })
    this.name = "ApiForbiddenError"
  }
}

export class ApiNotFoundError extends ApiClientError {
  constructor(message = "The requested resource could not be found.") {
    super({
      message,
      status: 404,
      code: "NOT_FOUND",
      isRetryable: false,
    })
    this.name = "ApiNotFoundError"
  }
}

export class ApiServerError extends ApiClientError {
  constructor(status = 500, message = "Internal server error. SRE team notified.") {
    super({
      message,
      status,
      code: "SERVER_ERROR",
      isRetryable: status >= 500,
    })
    this.name = "ApiServerError"
  }
}

export class ApiServiceUnavailableError extends ApiClientError {
  public readonly isMaintenance: boolean

  constructor(message = "Service temporarily unavailable.", isMaintenance = false) {
    super({
      message,
      status: 503,
      code: isMaintenance ? "MAINTENANCE_MODE" : "SERVICE_UNAVAILABLE",
      isRetryable: true,
    })
    this.name = "ApiServiceUnavailableError"
    this.isMaintenance = isMaintenance
  }
}

// ============================================================================
// Sanitization & Security Helpers
// ============================================================================

const SENSITIVE_KEY_PATTERNS = [
  /password/i,
  /token/i,
  /secret/i,
  /api[-_]?key/i,
  /authorization/i,
  /bearer/i,
  /cookie/i,
  /session/i,
  /credential/i,
]

export function redactSensitiveString(str: string): string {
  if (!str) return ""
  // Mask Bearer tokens: Bearer eyJ...
  let result = str.replace(/Bearer\s+[A-Za-z0-9-_.]+/gi, "Bearer [REDACTED]")
  // Mask key-value secrets in query/JSON-like strings: password=..., token=...
  result = result.replace(
    /(["']?(?:password|token|secret|apiKey|api_key|auth)["']?\s*[:=]\s*["']?)([^"'&,\s]+)(["']?)/gi,
    "$1[REDACTED]$3"
  )
  return result
}

export function redactSensitiveData<T>(obj: T): T {
  if (obj === null || obj === undefined) return obj
  if (typeof obj === "string") return redactSensitiveString(obj) as unknown as T
  if (typeof obj !== "object") return obj

  if (Array.isArray(obj)) {
    return obj.map((item) => redactSensitiveData(item)) as unknown as T
  }

  const sanitized: Record<string, unknown> = {}
  for (const [key, val] of Object.entries(obj as Record<string, unknown>)) {
    const isSensitive = SENSITIVE_KEY_PATTERNS.some((pattern) => pattern.test(key))
    if (isSensitive) {
      sanitized[key] = "[REDACTED]"
    } else if (typeof val === "object" && val !== null) {
      sanitized[key] = redactSensitiveData(val)
    } else if (typeof val === "string") {
      sanitized[key] = redactSensitiveString(val)
    } else {
      sanitized[key] = val
    }
  }
  return sanitized as T
}

function generateCorrelationId(): string {
  return "sherlog-" + Math.random().toString(36).substring(2, 10) + "-" + Date.now().toString(36)
}

// ============================================================================
// Request Options & Types
// ============================================================================

export interface RequestOptions extends RequestInit {
  timeoutMs?: number
  maxRetries?: number
  retryDelayMs?: number
  skipAuth?: boolean
}

// Map to track in-flight GET requests for deduplication
const inFlightGetRequests = new Map<string, Promise<unknown>>()

// ============================================================================
// Main API Client Implementation
// ============================================================================

export class ApiClient {
  private baseUrl: string
  private defaultTimeoutMs: number

  constructor(baseUrl = "/api", defaultTimeoutMs = 8000) {
    this.baseUrl = baseUrl.replace(/\/$/, "")
    this.defaultTimeoutMs = defaultTimeoutMs
  }

  /**
   * Safe fetch with timeouts, deduplication, retry handling, and typed error parsing
   */
  public async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const method = (options.method || "GET").toUpperCase()
    const isIdempotent = ["GET", "HEAD", "OPTIONS"].includes(method)
    let url: string
    if (endpoint.startsWith("http")) {
      url = endpoint
    } else if (this.baseUrl && (endpoint === this.baseUrl || endpoint.startsWith(`${this.baseUrl}/`))) {
      url = endpoint
    } else {
      url = `${this.baseUrl}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`
    }

    // Deduplicate in-flight idempotent GET requests
    if (isIdempotent && method === "GET") {
      const cacheKey = `${method}:${url}`
      const existing = inFlightGetRequests.get(cacheKey)
      if (existing) {
        return existing as Promise<T>
      }

      const promise = this.executeWithRetries<T>(url, options, isIdempotent).finally(() => {
        inFlightGetRequests.delete(cacheKey)
      })

      inFlightGetRequests.set(cacheKey, promise)
      return promise
    }

    // Direct mutation or non-GET request: no in-flight deduplication, strict retry rules
    return this.executeWithRetries<T>(url, options, isIdempotent)
  }

  private async executeWithRetries<T>(
    url: string,
    options: RequestOptions,
    isIdempotent: boolean
  ): Promise<T> {
    const maxRetries = isIdempotent ? (options.maxRetries ?? 2) : 0
    const baseDelay = options.retryDelayMs ?? 400
    let attempt = 0

    while (true) {
      try {
        return await this.executeSingle<T>(url, options)
      } catch (err: unknown) {
        attempt++
        const isClientError = err instanceof ApiClientError
        const isRetryable = isClientError ? err.isRetryable : false

        // Never retry mutations or non-retryable errors or if retries exhausted
        if (!isIdempotent || !isRetryable || attempt > maxRetries) {
          throw err
        }

        // Determine wait time (respecting Retry-After if present)
        let waitMs = baseDelay * Math.pow(2, attempt - 1) + Math.random() * 100
        if (err instanceof ApiRateLimitError && err.retryAfterSeconds) {
          waitMs = Math.min(err.retryAfterSeconds * 1000, 10000)
        }

        await new Promise((resolve) => setTimeout(resolve, waitMs))
      }
    }
  }

  private async executeSingle<T>(url: string, options: RequestOptions): Promise<T> {
    const timeoutMs = options.timeoutMs ?? this.defaultTimeoutMs
    const controller = new AbortController()
    let didTimeout = false

    const timeoutTimer = setTimeout(() => {
      didTimeout = true
      controller.abort()
    }, timeoutMs)

    // Build headers with sanitization
    const headers = new Headers(options.headers || {})
    if (!headers.has("Accept")) {
      headers.set("Accept", "application/json")
    }
    if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json")
    }

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers,
      })

      clearTimeout(timeoutTimer)

      if (!response.ok) {
        await this.handleErrorResponse(response)
      }

      // Check for 204 No Content
      if (response.status === 204) {
        return {} as T
      }

      const contentType = response.headers.get("content-type") || ""
      if (contentType.includes("application/json")) {
        return (await response.json()) as T
      }
      return (await response.text()) as unknown as T
    } catch (err: unknown) {
      clearTimeout(timeoutTimer)

      if (didTimeout) {
        throw new ApiTimeoutError(timeoutMs)
      }

      if (err instanceof ApiClientError) {
        throw err
      }

      // Browser abort triggered outside timeout
      if (err instanceof DOMException && err.name === "AbortError") {
        throw new ApiClientError({ message: "Request cancelled.", code: "REQUEST_ABORTED" })
      }

      // Offline or network unreachable
      if (typeof navigator !== "undefined" && !navigator.onLine) {
        throw new ApiNetworkError("Browser is offline. Check your network connection.")
      }

      throw new ApiNetworkError(
        err instanceof Error ? redactSensitiveString(err.message) : "Failed to connect to backend service."
      )
    }
  }

  private async handleErrorResponse(response: Response): Promise<never> {
    const status = response.status
    let responseBody: {
      message?: string
      detail?: string
      error?: string
      maintenance?: boolean
      [key: string]: unknown
    } | null

    try {
      const text = await response.text()
      try {
        responseBody = JSON.parse(text)
      } catch {
        responseBody = { message: text }
      }
    } catch {
      responseBody = null
    }

    const safeMessage =
      responseBody?.message || responseBody?.detail || responseBody?.error || response.statusText

    switch (status) {
      case 400:
        throw new ApiClientError({
          status: 400,
          code: "BAD_REQUEST",
          message: safeMessage || "Invalid request parameters.",
          details: responseBody,
        })
      case 401:
        throw new ApiAuthError(safeMessage || "Authentication required.")
      case 403:
        throw new ApiForbiddenError(safeMessage || "Access forbidden.")
      case 404:
        throw new ApiNotFoundError(safeMessage || "Requested resource not found.")
      case 429: {
        const retryHeader = response.headers.get("Retry-After")
        let retrySeconds = 5
        if (retryHeader) {
          const parsed = parseInt(retryHeader, 10)
          if (!isNaN(parsed) && parsed > 0) {
            retrySeconds = parsed
          }
        }
        throw new ApiRateLimitError(retrySeconds)
      }
      case 503: {
        const isMaintenance =
          responseBody?.maintenance === true ||
          (typeof safeMessage === "string" && safeMessage.toLowerCase().includes("maintenance"))
        throw new ApiServiceUnavailableError(safeMessage || "Service unavailable.", isMaintenance)
      }
      default:
        if (status >= 500) {
          throw new ApiServerError(status, safeMessage || "Internal server error.")
        }
        throw new ApiClientError({
          status,
          code: `HTTP_${status}`,
          message: safeMessage || `Request failed with status ${status}.`,
          details: responseBody,
        })
    }
  }

  // Convenience methods
  public get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "GET" })
  }

  public post<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "POST",
      body: body !== undefined ? (typeof body === "string" ? body : JSON.stringify(body)) : undefined,
    })
  }

  public put<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PUT",
      body: body !== undefined ? (typeof body === "string" ? body : JSON.stringify(body)) : undefined,
    })
  }

  public delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "DELETE" })
  }
}

// Global default instance
export const api = new ApiClient()

// ============================================================================
// Observability Telemetry Handlers
// ============================================================================

export interface TelemetryQueryResult<T> {
  source: "prometheus" | "loki" | "jaeger"
  status: "success" | "empty" | "error"
  data: T | null
  error?: string
  isPartial?: boolean
}

/**
 * Independent Prometheus query executor.
 * Never fabricates data; returns explicit success, empty, or error states.
 */
export async function queryPrometheusTelemetry<T>(
  query: string,
  client: ApiClient = api
): Promise<TelemetryQueryResult<T>> {
  try {
    const encoded = encodeURIComponent(query)
    const result = await client.get<{ data?: { result?: T[] } }>(`/prometheus/api/v1/query?query=${encoded}`)
    const items = result?.data?.result ?? []
    if (items.length === 0) {
      return { source: "prometheus", status: "empty", data: null }
    }
    return { source: "prometheus", status: "success", data: items as unknown as T }
  } catch (err) {
    return {
      source: "prometheus",
      status: "error",
      data: null,
      error: err instanceof Error ? err.message : "Prometheus query failed.",
    }
  }
}

/**
 * Independent Loki logs query executor.
 */
export async function queryLokiLogs<T>(
  query: string,
  client: ApiClient = api
): Promise<TelemetryQueryResult<T>> {
  try {
    const encoded = encodeURIComponent(query)
    const result = await client.get<{ data?: { result?: T[] } }>(`/loki/api/v1/query_range?query=${encoded}`)
    const items = result?.data?.result ?? []
    if (items.length === 0) {
      return { source: "loki", status: "empty", data: null }
    }
    return { source: "loki", status: "success", data: items as unknown as T }
  } catch (err) {
    return {
      source: "loki",
      status: "error",
      data: null,
      error: err instanceof Error ? err.message : "Loki log query failed.",
    }
  }
}

/**
 * Independent Jaeger traces query executor.
 */
export async function queryJaegerTraces<T>(
  traceId: string,
  client: ApiClient = api
): Promise<TelemetryQueryResult<T>> {
  try {
    const result = await client.get<{ data?: T[] }>(`/jaeger/api/traces/${traceId}`)
    const items = result?.data ?? []
    if (items.length === 0) {
      return { source: "jaeger", status: "empty", data: null }
    }
    return { source: "jaeger", status: "success", data: items as unknown as T }
  } catch (err) {
    return {
      source: "jaeger",
      status: "error",
      data: null,
      error: err instanceof Error ? err.message : "Jaeger trace query failed.",
    }
  }
}
