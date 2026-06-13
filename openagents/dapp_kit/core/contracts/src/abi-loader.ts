// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// ABI loader. Priority: vendored ABI dir → Foundry out/ dir → null (raises).
// Mirrors openagents/contracts/registry.py.

import type { Abi } from "viem";

export interface AbiLoaderConfig {
  /** Base URL or filesystem path for vendored ABIs. e.g. "/abi/" or "./abi". */
  vendoredAbiDir?: string;
  /** Foundry out/ dir as a fallback. e.g. "../daio/contracts/out". */
  foundryOutDir?: string;
  /** In-memory ABI lookup; takes highest priority. */
  inlineAbis?: Record<string, Abi>;
}

/**
 * Load an ABI by contract name. Walks vendored → foundry → inline.
 *
 * @throws Error when none of the sources yield a parseable ABI
 */
export async function loadAbi(
  contractName: string,
  config: AbiLoaderConfig = {},
): Promise<Abi> {
  // 1. Inline (highest priority — used in tests and embedded scenarios)
  if (config.inlineAbis && config.inlineAbis[contractName]) {
    return config.inlineAbis[contractName];
  }

  // 2. Vendored ABI dir
  if (config.vendoredAbiDir) {
    try {
      const text = await fetchOrRead(
        `${stripTrailingSlash(config.vendoredAbiDir)}/${contractName}.json`,
      );
      return JSON.parse(text) as Abi;
    } catch {
      // fall through to foundry path
    }
  }

  // 3. Foundry out/ — JSON shape is { abi: [...], ... }
  if (config.foundryOutDir) {
    try {
      const text = await fetchOrRead(
        `${stripTrailingSlash(config.foundryOutDir)}/${contractName}.sol/${contractName}.json`,
      );
      const parsed = JSON.parse(text);
      if (parsed && Array.isArray(parsed.abi)) return parsed.abi as Abi;
    } catch {
      // fall through to failure
    }
  }

  throw new Error(
    `ABI for ${contractName} not found. Tried: vendoredAbiDir=${config.vendoredAbiDir}, foundryOutDir=${config.foundryOutDir}.`,
  );
}

async function fetchOrRead(source: string): Promise<string> {
  if (typeof window === "undefined" && !source.startsWith("http")) {
    const { readFile } = await import("node:fs/promises");
    return await readFile(source, "utf-8");
  }
  const res = await fetch(source);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.text();
}

function stripTrailingSlash(p: string): string {
  return p.endsWith("/") ? p.slice(0, -1) : p;
}
