// frontend/vite.config.ts
// Vite build/dev-server config — tells Vite to use the React plugin
// (JSX transform, fast refresh) and to listen on all interfaces so it
// works the same whether run directly or inside Docker.

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
});