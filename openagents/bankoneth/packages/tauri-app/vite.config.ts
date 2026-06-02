import { defineConfig } from "vite";

// Vite config for the bankoneth reference dApp.
// Tauri builds use the same Vite — see `pnpm tauri build`.
export default defineConfig({
  server: {
    port: 5173,
    strictPort: true,
    host: "127.0.0.1",
  },
  build: {
    target: "es2022",
    outDir: "dist",
    sourcemap: true,
  },
});
