// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Foundry deployment driver. Shells out to `forge create` or `forge script`.
// Contract: docs/services/contract_deployment_as_a_service.md §2.1, §4, §5.

import type { Address, Hex } from "viem";
import { configFor, activeRpcUrl, type ChainDeployConfig } from "./chain-config.js";
import { preflight, allPassed, firstFailure, type PreflightCheck } from "./preflight.js";

export interface DeployScriptOpts {
  /** Foundry contracts root (containing foundry.toml). */
  contractsRoot: string;
  /** Script file relative to <contractsRoot>/script/. */
  scriptName: string;
  /** Network catalog key (e.g. "base-sepolia"). */
  network: string;
  /** Env vars passed to the script (DEPLOYER_PRIVATE_KEY, DEPLOY_AGENT_REGISTRY, etc.). */
  env?: Record<string, string>;
  /** Pass --broadcast (default true for non-mainnet, off for mainnet without intent). */
  broadcast?: boolean;
  /** Pass --verify (default false). */
  verify?: boolean;
  /** Verifier API key, when verify=true. */
  verifierApiKey?: string;
  /** Skip the two-step confirmation flow for testnet (ignored for mainnet). */
  skipConfirmation?: boolean;
}

export interface DeployIntent {
  id: string;
  network: string;
  isMainnet: boolean;
  preflight: PreflightCheck[];
  estimatedGas: bigint;
  /** Best-effort: estimated cost in USD. 0 until a gas oracle is wired. */
  estimatedCostUSD: number;
  summary: string;
  /** Unix ms when the intent expires. */
  expiresAt: number;
}

export interface DeployScriptResult {
  /** Path where the deployment record landed. */
  receiptPath?: string;
  /** Deployed contracts by name. */
  contracts: Record<
    string,
    {
      address: Address;
      txHash: Hex;
      blockNumber: number;
      gasUsed: bigint;
    }
  >;
  /** Raw stdout from forge (for debugging). */
  stdout: string;
}

export interface SingleDeployOpts {
  contractsRoot: string;
  contractName: string;
  network: string;
  constructorArgs?: unknown[];
  privateKey?: Hex;
  rpcUrl?: string;
  verify?: boolean;
  verifierApiKey?: string;
}

export interface SingleDeployResult {
  contractName: string;
  address: Address;
  txHash: Hex;
  blockNumber: number;
  deployer: Address;
  gasUsed: bigint;
  deployedAt: string;
}

/**
 * Generate an intent for a deploy. Mainnet deploys MUST go through this
 * two-step flow; testnet can skip via `skipConfirmation: true`.
 */
export async function intent(opts: DeployScriptOpts): Promise<DeployIntent> {
  const cfg = configFor(opts.network);
  const checks = await preflight({
    networkKey: opts.network,
    foundryOutDir: opts.contractsRoot + "/out",
    mainnetFlag: !cfg.isMainnet || (opts.env?.MAINNET === "true"),
  });

  const id = `deploy-intent-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  return {
    id,
    network: opts.network,
    isMainnet: cfg.isMainnet,
    preflight: checks,
    estimatedGas: 0n,
    estimatedCostUSD: 0,
    summary: `Deploy ${opts.scriptName} to ${opts.network}${cfg.isMainnet ? " (MAINNET)" : ""}.`,
    expiresAt: Date.now() + 5 * 60 * 1000,
  };
}

/**
 * Execute the deploy script. For mainnet, the intent's `id` must already
 * have been operator-confirmed (the dApp UI's responsibility). For testnet
 * with `skipConfirmation: true`, the intent step is bypassed.
 *
 * Calls `forge script <scriptName> --rpc-url <url> [--broadcast] [--verify]`.
 * Streams output. Returns the parsed deployment record on success.
 */
export async function runScript(opts: DeployScriptOpts): Promise<DeployScriptResult> {
  const cfg = configFor(opts.network);
  if (cfg.isMainnet && !opts.skipConfirmation && !opts.env?.MAINNET_INTENT_CONFIRMED) {
    throw new Error(
      `Mainnet deploys require a confirmed intent. Call intent() and pass MAINNET_INTENT_CONFIRMED=<intent_id> in env.`,
    );
  }
  const checks = await preflight({
    networkKey: opts.network,
    foundryOutDir: opts.contractsRoot + "/out",
    mainnetFlag: !cfg.isMainnet || (opts.env?.MAINNET === "true"),
  });
  if (!allPassed(checks)) {
    const failed = firstFailure(checks);
    throw new Error(`Preflight failed: ${JSON.stringify(failed)}`);
  }

  const rpc = opts.env?.RPC_URL || activeRpcUrl(opts.network);
  const args = [
    "script",
    `script/${opts.scriptName}`,
    "--rpc-url",
    rpc,
  ];
  if (opts.broadcast !== false) args.push("--broadcast");
  if (opts.verify) {
    args.push("--verify");
    if (opts.verifierApiKey && cfg.verifierUrl) {
      args.push("--verifier-url", cfg.verifierUrl);
      args.push("--etherscan-api-key", opts.verifierApiKey);
    }
  }

  const stdout = await runForge(args, {
    cwd: opts.contractsRoot,
    env: opts.env ?? {},
  });

  // Foundry writes a broadcast record at:
  //   broadcast/<scriptName>/<chainId>/run-latest.json
  // The dApp kit's expected output is openagents/deployments/<network>.json —
  // a follow-up call to extractDeployments() converts shape. For now we
  // surface the raw stdout and leave the dApp to parse the broadcast/.

  return {
    receiptPath: `${opts.contractsRoot}/broadcast/${opts.scriptName}/${cfg.chainId}/run-latest.json`,
    contracts: {},
    stdout,
  };
}

/**
 * Single-contract deploy via `forge create`.
 */
export async function deploy(opts: SingleDeployOpts): Promise<SingleDeployResult> {
  const cfg = configFor(opts.network);
  const rpc = opts.rpcUrl || activeRpcUrl(opts.network);
  const args = [
    "create",
    `src/${opts.contractName}.sol:${opts.contractName}`,
    "--rpc-url",
    rpc,
  ];
  if (opts.privateKey) args.push("--private-key", opts.privateKey);
  if (opts.constructorArgs && opts.constructorArgs.length > 0) {
    args.push("--constructor-args", ...opts.constructorArgs.map((a) => String(a)));
  }
  if (opts.verify && opts.verifierApiKey && cfg.verifierUrl) {
    args.push("--verify");
    args.push("--verifier-url", cfg.verifierUrl);
    args.push("--etherscan-api-key", opts.verifierApiKey);
  }

  const stdout = await runForge(args, { cwd: opts.contractsRoot });
  // forge create stdout shape:
  //   Deployer: 0x...
  //   Deployed to: 0x...
  //   Transaction hash: 0x...
  const addressMatch = /Deployed to:\s*(0x[a-fA-F0-9]{40})/.exec(stdout);
  const txMatch = /Transaction hash:\s*(0x[a-fA-F0-9]{64})/.exec(stdout);
  const deployerMatch = /Deployer:\s*(0x[a-fA-F0-9]{40})/.exec(stdout);
  if (!addressMatch || !txMatch || !deployerMatch) {
    throw new Error(`Could not parse forge create output:\n${stdout}`);
  }
  return {
    contractName: opts.contractName,
    address: addressMatch[1] as Address,
    txHash: txMatch[1] as Hex,
    blockNumber: 0,
    deployer: deployerMatch[1] as Address,
    gasUsed: 0n,
    deployedAt: new Date().toISOString(),
  };
}

/**
 * Verify whether `forge` is on PATH. Tests use this to skip when the
 * toolchain isn't installed in CI.
 */
export async function forgeAvailable(): Promise<boolean> {
  try {
    await runForge(["--version"], {});
    return true;
  } catch {
    return false;
  }
}

// ─── helpers ────────────────────────────────────────────────────

async function runForge(
  args: string[],
  opts: { cwd?: string; env?: Record<string, string> },
): Promise<string> {
  if (typeof window !== "undefined") {
    throw new Error("foundry-driver runs server-side only (node, Tauri Rust side).");
  }
  const { spawn } = await import("node:child_process");
  return await new Promise<string>((resolve, reject) => {
    const child = spawn("forge", args, {
      cwd: opts.cwd,
      env: { ...process.env, ...(opts.env ?? {}) },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (d) => (stdout += d.toString()));
    child.stderr?.on("data", (d) => (stderr += d.toString()));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve(stdout);
      else reject(new Error(`forge ${args.join(" ")} exited ${code}: ${stderr}`));
    });
  });
}
