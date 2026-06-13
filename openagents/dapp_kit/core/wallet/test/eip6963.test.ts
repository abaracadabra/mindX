// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// EIP-6963 discovery contract tests.

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { discoverProviders, pickProvider, type AnnouncedProvider } from "../src/eip6963.js";

// Minimal EIP-1193 provider stub.
function makeProvider(rdns: string, name = rdns): AnnouncedProvider {
  return {
    info: { uuid: `uuid-${rdns}`, name, icon: "", rdns },
    provider: { request: async () => undefined },
  };
}

describe("discoverProviders", () => {
  beforeEach(() => {
    // Make sure we start with a clean window. happy-dom resets per file.
  });

  afterEach(() => {
    // Clear leftover listeners by emitting one final blank dispatch.
  });

  it("dedupes providers by rdns", async () => {
    // Setup: have three providers announce, but two share an rdns.
    const announceWhenRequested = (provs: AnnouncedProvider[]) => {
      const handler = () => {
        for (const p of provs) {
          window.dispatchEvent(new CustomEvent("eip6963:announceProvider", { detail: p }));
        }
      };
      window.addEventListener("eip6963:requestProvider", handler);
      return () => window.removeEventListener("eip6963:requestProvider", handler);
    };

    const provs = [
      makeProvider("io.metamask", "MetaMask"),
      makeProvider("io.metamask", "MetaMask (duplicate)"),
      makeProvider("com.coinbase.wallet", "Coinbase Wallet"),
      makeProvider("io.metamask", "MetaMask (third)"),
      makeProvider("com.brave.wallet", "Brave Wallet"),
      makeProvider("com.coinbase.wallet", "Coinbase Wallet (dup)"),
    ];

    const cleanup = announceWhenRequested(provs);
    try {
      const out = await discoverProviders(50);
      // 3 distinct rdns: metamask, coinbase, brave
      expect(out.length).toBe(3);
      const rdnss = out.map((p) => p.info.rdns).sort();
      expect(rdnss).toEqual([
        "com.brave.wallet",
        "com.coinbase.wallet",
        "io.metamask",
      ]);
    } finally {
      cleanup();
    }
  });

  it("returns empty list with no providers and no window.ethereum", async () => {
    delete (window as unknown as { ethereum?: unknown }).ethereum;
    const out = await discoverProviders(20);
    expect(out).toEqual([]);
  });

  it("falls back to window.ethereum when no EIP-6963 events fire", async () => {
    (window as unknown as { ethereum: unknown }).ethereum = {
      request: async () => undefined,
    };
    const out = await discoverProviders(20);
    expect(out.length).toBe(1);
    expect(out[0]?.info.rdns).toBe("legacy.injected");
    delete (window as unknown as { ethereum?: unknown }).ethereum;
  });
});

describe("pickProvider", () => {
  const list: AnnouncedProvider[] = [
    makeProvider("com.coinbase.wallet"),
    makeProvider("io.metamask"),
    makeProvider("com.brave.wallet"),
  ];

  it("returns the preferred rdns when present", () => {
    const p = pickProvider(list, "io.metamask");
    expect(p?.info.rdns).toBe("io.metamask");
  });

  it("falls back to the first when preferred is absent", () => {
    const p = pickProvider(list, "io.does-not-exist");
    expect(p?.info.rdns).toBe("com.coinbase.wallet");
  });

  it("returns undefined for empty list", () => {
    expect(pickProvider([])).toBeUndefined();
  });
});
