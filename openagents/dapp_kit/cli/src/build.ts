// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// `openagents-dapp build [--tauri]` — vite build, optionally tauri build.

import { runPnpm } from "./dev.js";

export async function buildCmd(args: string[]): Promise<number> {
  const wantTauri = args.includes("--tauri");
  const code = await runPnpm(["build"]);
  if (code !== 0) return code;
  if (!wantTauri) return 0;
  return await runPnpm(["tauri:build"]);
}
