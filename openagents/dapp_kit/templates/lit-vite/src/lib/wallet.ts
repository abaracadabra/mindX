// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Mode detection + connect wrapper. The webview-twin branch lives here:
// in Tauri, secure storage routes via @openagents/tauri-bridge.

import { connect as walletConnect, type ConnectedAccount } from "@openagents/wallet";

export type Mode = "web" | "tauri";

/**
 * Return the active mode. `tauri` when running inside a Tauri 2 webview,
 * `web` otherwise.
 */
export function getMode(): Mode {
  if (typeof window === "undefined") return "web";
  return "__TAURI__" in window ? "tauri" : "web";
}

/**
 * Connect a wallet. Same flow in both modes; the wallet layer abstracts
 * provider details.
 */
export async function connect(): Promise<ConnectedAccount> {
  return await walletConnect();
}

/**
 * Persist a non-secret hint (the connected address) so the UI can show
 * "welcome back, <addr>" on next load. In Tauri this lands in the OS
 * keychain; in webview, sessionStorage (cleared on tab close per the
 * cypherpunk2048 no-trapdoors rule).
 */
export async function rememberAddress(address: string): Promise<void> {
  if (getMode() === "tauri") {
    try {
      // Dynamic import — only loaded inside Tauri.
      const mod = await dynamicImport("@openagents/tauri-bridge");
      if (mod && typeof (mod as { storeKeychain?: (k: string, v: string) => Promise<void> }).storeKeychain === "function") {
        await (mod as { storeKeychain: (k: string, v: string) => Promise<void> }).storeKeychain(
          "openagents.lastAddress",
          address,
        );
        return;
      }
    } catch {
      /* fall through to webview path */
    }
  }
  if (typeof sessionStorage !== "undefined") {
    sessionStorage.setItem("openagents.lastAddress", address);
  }
}

export async function recallAddress(): Promise<string | undefined> {
  if (getMode() === "tauri") {
    try {
      const mod = await dynamicImport("@openagents/tauri-bridge");
      if (mod && typeof (mod as { loadKeychain?: (k: string) => Promise<string | undefined> }).loadKeychain === "function") {
        return await (mod as { loadKeychain: (k: string) => Promise<string | undefined> }).loadKeychain(
          "openagents.lastAddress",
        );
      }
    } catch {
      /* fall through */
    }
  }
  if (typeof sessionStorage !== "undefined") {
    return sessionStorage.getItem("openagents.lastAddress") ?? undefined;
  }
  return undefined;
}

async function dynamicImport(spec: string): Promise<unknown> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-implied-eval
    return await new Function("s", "return import(s)")(spec);
  } catch {
    return null;
  }
}
