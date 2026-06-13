// SPDX-License-Identifier: Apache-2.0
// Tauri-aware Vite config. Same src/ builds for browser AND Tauri webview.
// Refs: docs/services/wallet_connection_as_a_service.md §2.

import { defineConfig } from "vite";

// Tauri 2 looks for these defaults when running `tauri dev/build`.
// They keep the webview happy on hot-reload + production bundles.
export default defineConfig({
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
    host: "127.0.0.1",
  },
  build: {
    target: ["es2022", "chrome105", "safari15"],
    minify: !process.env.TAURI_DEBUG ? "esbuild" : false,
    sourcemap: !!process.env.TAURI_DEBUG,
  },
  envPrefix: ["VITE_", "TAURI_"],
});
