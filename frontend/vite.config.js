import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    sourcemap: false,
    chunkSizeWarningLimit: 600,
  },
  server: {
    port: 5173,
    open: true,
  },
});
