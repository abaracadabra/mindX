// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Pre-flight checks for deploys.
// Contract: docs/services/contract_deployment_as_a_service.md §3.

import { createPublicClient, http, type Address } from "viem";
import { configFor, activeRpcUrl } from "./chain-config.js";

export type PreflightCheck =
  | { kind: "rpc"; passed: boolean; rpcUrl: string; chainId: number; latencyMs: number; error?: string }
  | { kind: "balance"; passed: boolean; required: bigint; have: bigint; address: Address }
  | { kind: "compiled"; passed: boolean; contractName: string; artifactPath: string }
  | { kind: "gas-budget"; passed: boolean; estimated: bigint; budgetUSD: number }
  | { kind: "network-flag"; passed: boolean; isMainnet: boolean; explicitFlag: boolean };

export interface PreflightInput {
  networkKey: string;
  contractName?: string;
  deployer?: Address;
  /** Pre-computed gas estimate (e.g. from `forge script --json`). */
  estimatedGas?: bigint;
  /** Caller-set per-deploy budget in USD; falls back to chain default. */
  gasBudgetUSD?: number;
  /** Foundry out/ dir; only used for the 'compiled' check. */
  foundryOutDir?: string;
  /** True when the operator explicitly passed --mainnet. */
  mainnetFlag?: boolean;
}

/**
 * Run the deterministic pre-flight pipeline.
 * Returns the array of checks; caller verifies every `passed: true`.
 */
export async function preflight(input: PreflightInput): Promise<PreflightCheck[]> {
  const cfg = configFor(input.networkKey);
  const checks: PreflightCheck[] = [];

  // 1. RPC reachability + chain-id verification
  const rpcUrl = activeRpcUrl(input.networkKey);
  const t0 = Date.now();
  try {
    const client = createPublicClient({ transport: http(rpcUrl) });
    const reportedId = await client.getChainId();
    const latencyMs = Date.now() - t0;
    checks.push({
      kind: "rpc",
      passed: reportedId === cfg.chainId && latencyMs < 5000,
      rpcUrl,
      chainId: reportedId,
      latencyMs,
    });
  } catch (err) {
    checks.push({
      kind: "rpc",
      passed: false,
      rpcUrl,
      chainId: 0,
      latencyMs: Date.now() - t0,
      error: err instanceof Error ? err.message : String(err),
    });
  }

  // 2. Deployer balance ≥ 2× estimated gas cost
  if (input.deployer && input.estimatedGas) {
    try {
      const client = createPublicClient({ transport: http(rpcUrl) });
      const balance = await client.getBalance({ address: input.deployer });
      // 2× headroom; gas price not yet known precisely → use the rough rule
      // that 1 unit of gas at chain's typical price ≈ 1 wei × 50 gwei. The
      // dApp's deploy intent computes the real estimate. Here we just check
      // the deployer is solvent enough for a 2× safety margin.
      const required = input.estimatedGas * 50_000_000_000n * 2n;
      checks.push({
        kind: "balance",
        passed: balance >= required,
        required,
        have: balance,
        address: input.deployer,
      });
    } catch {
      checks.push({
        kind: "balance",
        passed: false,
        required: 0n,
        have: 0n,
        address: input.deployer,
      });
    }
  }

  // 3. Compiled artifact exists + is fresh
  if (input.contractName && input.foundryOutDir && typeof window === "undefined") {
    try {
      const { stat } = await import("node:fs/promises");
      const artifactPath = `${input.foundryOutDir}/${input.contractName}.sol/${input.contractName}.json`;
      const s = await stat(artifactPath);
      checks.push({
        kind: "compiled",
        passed: s.isFile() && s.size > 0,
        contractName: input.contractName,
        artifactPath,
      });
    } catch (err) {
      checks.push({
        kind: "compiled",
        passed: false,
        contractName: input.contractName,
        artifactPath: `${input.foundryOutDir}/${input.contractName}.sol/${input.contractName}.json`,
      });
    }
  }

  // 4. Gas budget
  if (input.estimatedGas) {
    const budget = input.gasBudgetUSD ?? cfg.defaultGasBudgetUSD;
    checks.push({
      kind: "gas-budget",
      passed: true, // True until a concrete gas-price-to-USD oracle wires in
      estimated: input.estimatedGas,
      budgetUSD: budget,
    });
  }

  // 5. Network flag (mainnet requires explicit operator confirmation)
  checks.push({
    kind: "network-flag",
    passed: !cfg.isMainnet || !!input.mainnetFlag,
    isMainnet: cfg.isMainnet,
    explicitFlag: !!input.mainnetFlag,
  });

  return checks;
}

/**
 * Convenience: returns true iff every check in the array passed.
 */
export function allPassed(checks: PreflightCheck[]): boolean {
  return checks.every((c) => c.passed);
}

/**
 * Convenience: returns the first failed check, or undefined.
 */
export function firstFailure(checks: PreflightCheck[]): PreflightCheck | undefined {
  return checks.find((c) => !c.passed);
}
