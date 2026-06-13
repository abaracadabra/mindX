// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Tauri IPC invoke wrappers. Browser-safe: when not inside a Tauri webview,
// every call throws TauriBridgeError so callers can route around the absence.
//
// Contract: docs/services/wallet_connection_as_a_service.md §6.

export class TauriBridgeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TauriBridgeError";
  }
}

export function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI__" in window;
}

/**
 * Thin wrapper over @tauri-apps/api/core invoke. Throws TauriBridgeError
 * when called outside a Tauri webview.
 */
export async function invokeCommand<T = unknown>(
  cmd: string,
  args?: Record<string, unknown>,
): Promise<T> {
  if (!isTauri()) {
    throw new TauriBridgeError(`invokeCommand('${cmd}') called outside Tauri`);
  }
  try {
    const mod = await dynamicImport("@tauri-apps/api/core");
    const invoke = (mod as { invoke: (cmd: string, args?: Record<string, unknown>) => Promise<T> }).invoke;
    if (!invoke) throw new TauriBridgeError("invoke not found on @tauri-apps/api/core");
    return await invoke(cmd, args);
  } catch (err) {
    if (err instanceof TauriBridgeError) throw err;
    throw new TauriBridgeError(
      err instanceof Error ? err.message : String(err),
    );
  }
}

async function dynamicImport(spec: string): Promise<unknown> {
  // eslint-disable-next-line @typescript-eslint/no-implied-eval
  return await new Function("s", "return import(s)")(spec);
}
