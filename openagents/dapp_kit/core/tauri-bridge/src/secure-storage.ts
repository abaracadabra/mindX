// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Secure-storage abstraction. In Tauri, routes to the Rust commands
// `keychain_store` / `keychain_load` / `keychain_clear` (defined in
// src-tauri/src/commands/keychain.rs). In browser fallback, routes to
// sessionStorage with a visible "DEV ONLY" caveat.
//
// Contract: docs/services/wallet_connection_as_a_service.md §6.

import { invokeCommand, isTauri } from "./ipc.js";

const SESSION_PREFIX = "openagents:";

/**
 * Store a value under `key`. In Tauri this writes to the OS keychain;
 * in webview fallback, sessionStorage.
 */
export async function storeKeychain(key: string, value: string): Promise<void> {
  if (isTauri()) {
    await invokeCommand("keychain_store", { key, value });
    return;
  }
  if (typeof sessionStorage !== "undefined") {
    sessionStorage.setItem(SESSION_PREFIX + key, value);
  }
}

/**
 * Load a value previously stored under `key`. Returns undefined when no
 * value is set.
 */
export async function loadKeychain(key: string): Promise<string | undefined> {
  if (isTauri()) {
    try {
      return await invokeCommand<string>("keychain_load", { key });
    } catch {
      return undefined;
    }
  }
  if (typeof sessionStorage !== "undefined") {
    return sessionStorage.getItem(SESSION_PREFIX + key) ?? undefined;
  }
  return undefined;
}

/**
 * Clear the entry under `key`.
 */
export async function clearKeychain(key: string): Promise<void> {
  if (isTauri()) {
    await invokeCommand("keychain_clear", { key });
    return;
  }
  if (typeof sessionStorage !== "undefined") {
    sessionStorage.removeItem(SESSION_PREFIX + key);
  }
}

/**
 * Convenience namespace that exposes a typical `Storage`-like interface.
 */
export const osKeychain = {
  store: storeKeychain,
  load: loadKeychain,
  clear: clearKeychain,
};
