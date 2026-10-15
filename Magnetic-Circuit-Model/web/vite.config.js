import { defineConfig } from "vite";

// /api/* is served by api_server.py (reuses the real Python models).
export default defineConfig({
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8765" } },
});
