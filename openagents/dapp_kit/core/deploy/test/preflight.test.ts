// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved

import { describe, it, expect } from "vitest";
import { allPassed, firstFailure, preflight } from "../src/preflight.js";
import { configFor, activeRpcUrl } from "../src/chain-config.js";

describe("chain-config", () => {
  it("knows all MVP networks", () => {
    expect(configFor("base-sepolia").chainId).toBe(84532);
    expect(configFor("base").isMainnet).toBe(true);
    expect(configFor("0g-galileo").isMainnet).toBe(false);
    expect(configFor("0g-mainnet").isMainnet).toBe(true);
  });

  it("throws on unknown network", () => {
    expect(() => configFor("does-not-exist")).toThrow(/No deploy config/);
  });

  it("env override beats catalog default for RPC URL", () => {
    const before = process.env["MINDX_DEPLOY_RPC_BASE_SEPOLIA"];
    try {
      process.env["MINDX_DEPLOY_RPC_BASE_SEPOLIA"] = "https://custom.rpc/";
      expect(activeRpcUrl("base-sepolia")).toBe("https://custom.rpc/");
    } finally {
      if (before === undefined) delete process.env["MINDX_DEPLOY_RPC_BASE_SEPOLIA"];
      else process.env["MINDX_DEPLOY_RPC_BASE_SEPOLIA"] = before;
    }
  });
});

describe("preflight", () => {
  it("network-flag passes for testnet without mainnetFlag", async () => {
    const checks = await preflight({ networkKey: "base-sepolia" });
    const flag = checks.find((c) => c.kind === "network-flag");
    expect(flag?.passed).toBe(true);
  });

  it("network-flag fails for mainnet without mainnetFlag", async () => {
    const checks = await preflight({ networkKey: "base" });
    const flag = checks.find((c) => c.kind === "network-flag");
    expect(flag?.passed).toBe(false);
    expect(allPassed(checks)).toBe(false);
    expect(firstFailure(checks)?.kind).toBe("network-flag");
  });

  it("network-flag passes for mainnet with mainnetFlag=true", async () => {
    const checks = await preflight({ networkKey: "base", mainnetFlag: true });
    const flag = checks.find((c) => c.kind === "network-flag");
    expect(flag?.passed).toBe(true);
  });
});
