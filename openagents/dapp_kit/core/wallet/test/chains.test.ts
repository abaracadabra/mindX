// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved

import { describe, it, expect } from "vitest";
import { CHAINS, chainByKey, chainById } from "../src/chains.js";

describe("chain catalog", () => {
  it("includes all MVP chains", () => {
    const required = [
      "ethereum",
      "sepolia",
      "base",
      "base-sepolia",
      "0g-galileo",
      "0g-mainnet",
      "algorand-mainnet",
      "algorand-testnet",
    ];
    for (const key of required) {
      expect(CHAINS[key], `missing chain '${key}'`).toBeDefined();
    }
  });

  it("0G entries flag isMindXNative=true", () => {
    expect(CHAINS["0g-galileo"]?.isMindXNative).toBe(true);
    expect(CHAINS["0g-mainnet"]?.isMindXNative).toBe(true);
  });

  it("Algorand entries flag isAlgorand=true", () => {
    expect(CHAINS["algorand-mainnet"]?.isAlgorand).toBe(true);
    expect(CHAINS["algorand-testnet"]?.isAlgorand).toBe(true);
  });

  it("chainByKey matches the catalog", () => {
    expect(chainByKey("base")?.id).toBe(8453);
    expect(chainByKey("base-sepolia")?.id).toBe(84532);
    expect(chainByKey("does-not-exist")).toBeUndefined();
  });

  it("chainById matches catalog entries", () => {
    expect(chainById(8453)?.name).toMatch(/Base/);
    expect(chainById(16601)?.isMindXNative).toBe(true);
    expect(chainById(999999)).toBeUndefined();
  });
});
