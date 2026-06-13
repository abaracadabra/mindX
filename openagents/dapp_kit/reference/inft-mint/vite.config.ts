import { defineConfig } from "vite";

export default defineConfig({
  clearScreen: false,
  server: { port: 5174, strictPort: true, host: "127.0.0.1" },
  build: {
    target: ["es2022", "chrome105", "safari15"],
    minify: !process.env.TAURI_DEBUG ? "esbuild" : false,
    sourcemap: !!process.env.TAURI_DEBUG,
  },
  envPrefix: ["VITE_", "TAURI_"],
});
