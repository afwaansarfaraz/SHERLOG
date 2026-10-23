import path from "path"
import react from "@vitejs/plugin-react"
import { loadEnv, type Plugin } from "vite"
import { defineConfig } from "vitest/config"

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  // Read the API key only in the local Vite server process. It is never added to
  // import.meta.env, define, or the production bundle.
  const apiKey = command === "serve"
    ? loadEnv(mode, path.resolve(import.meta.dirname, ".."), "API_KEY").API_KEY?.trim()
    : undefined

  const localProxyAuthGuard: Plugin = {
    name: "sherlog-local-api-auth-guard",
    configResolved(config) {
      if (config.command !== "serve" || !apiKey) return

      const host = config.server.host
      if (typeof host !== "string" || !["127.0.0.1", "localhost", "::1"].includes(host.toLowerCase())) {
        throw new Error("The API-key development proxy may only run on a loopback host.")
      }
    },
  }

  return {
    plugins: [react(), localProxyAuthGuard],
    resolve: {
      alias: {
        "@": path.resolve(import.meta.dirname, "./src"),
      },
    },
    server: {
      // Keep the development proxy private because it holds the backend key.
      host: "127.0.0.1",
      allowedHosts: ["localhost", "127.0.0.1", "::1"],
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8080",
          changeOrigin: true,
          ...(apiKey
            ? {
                configure(proxy) {
                  proxy.on("proxyReq", (proxyReq, request) => {
                    // Grant only the registered-application probe its server-side credential.
                    // Other API routes keep their normal authentication behavior.
                    if (
                      proxyReq.method === "POST" &&
                      /^\/api\/applications\/[^/]+\/test-connection(?:\?.*)?$/.test(proxyReq.path ?? "")
                    ) {
                      // A hostile site must not be able to use a browser form to make
                      // this loopback proxy spend its server-side probe credential.
                      const requestOrigin = request.headers.origin
                      const requestHost = request.headers.host
                      if (
                        !requestOrigin ||
                        !requestHost ||
                        requestOrigin !== `http://${requestHost}` ||
                        request.headers["sec-fetch-site"] !== "same-origin"
                      ) {
                        return
                      }
                      proxyReq.setHeader("Authorization", `Bearer ${apiKey}`)
                    }
                  })
                },
              }
            : {}),
        },
      },
    },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
    },
  }
})

