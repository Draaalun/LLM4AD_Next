import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import { tanstackRouter } from "@tanstack/router-plugin/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig, loadEnv } from "vite"

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, "")
  return {
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
        "@docs": path.resolve(__dirname, "../../docs"),
      },
    },
    plugins: [
      tanstackRouter({
        target: "react",
        autoCodeSplitting: true,
      }),
      react(),
      tailwindcss(),
    ],
    build: {
      // 1.5MB warning to surface oversize chunks early
      chunkSizeWarningLimit: 1500,
      rollupOptions: {
        output: {
          // Group heavy/independent libraries into their own chunks so they can
          // be cached separately and skipped on routes that don't need them.
          manualChunks(id) {
            if (!id.includes("node_modules")) return
            if (id.includes("/d3") || id.includes("\\d3")) return "vendor-d3"
            if (id.includes("monaco-editor") || id.includes("@monaco-editor"))
              return "vendor-monaco"
            if (id.includes("echarts")) return "vendor-echarts"
            if (id.includes("recharts")) return "vendor-recharts"
            if (id.includes("react-markdown") || id.includes("remark-"))
              return "vendor-markdown"
            if (id.includes("@tanstack")) return "vendor-tanstack"
            if (id.includes("radix-ui") || id.includes("@radix-ui"))
              return "vendor-radix"
            if (id.includes("lucide-react")) return "vendor-icons"
          },
        },
      },
    },
    server: {
      fs: {
        allow: [path.resolve(__dirname, "../../docs"), "."],
      },
      proxy: {
        "/api": {
          target: env.VITE_PROXY_TARGET || "http://localhost:8000",
          changeOrigin: true,
        },
        "/code_ide": {
          target: env.VITE_PROXY_TARGET || "http://localhost:8000",
          changeOrigin: true,
          ws: true,
        },
      },
    },
  }
})
