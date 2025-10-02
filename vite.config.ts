/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath, URL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    host: true,
    hmr: {
      port: 3001,
      host: "localhost",
    },
    // Optimize file watching
    watch: {
      usePolling: false,
      ignored: ["**/node_modules/**", "**/.git/**", "**/dist/**"],
    },
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  // Optimize build performance
  optimizeDeps: {
    include: ["react", "react-dom", "react-router-dom"],
  },
  // Disable TypeScript type checking during dev for faster restarts
  esbuild: {
    logOverride: { "this-is-undefined-in-esm": "silent" },
  },
  // Test configuration
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/tests/setup.ts"],
    testTimeout: 30000, // 30 seconds for integration tests
  },
});
