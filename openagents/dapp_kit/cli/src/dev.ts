// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// `openagents-dapp dev` — run `vite` from the current cwd.

import { spawn } from "node:child_process";

export async function devCmd(args: string[]): Promise<number> {
  return await runPnpm(["dev", ...args]);
}

export function runPnpm(args: string[]): Promise<number> {
  return new Promise((resolve) => {
    const child = spawn("pnpm", args, { stdio: "inherit" });
    child.on("exit", (code) => resolve(code ?? 1));
    child.on("error", (err) => {
      console.error(`pnpm not found or failed: ${err.message}`);
      resolve(127);
    });
  });
}
