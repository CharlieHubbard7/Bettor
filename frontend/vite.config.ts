import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Phase 2 builds out the full frontend against the live API.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
