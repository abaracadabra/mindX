// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Deployment-record loader. Consumes the same JSON files as
// openagents/contracts/registry.py.
// Contract: docs/services/contract_interaction_as_a_service.md §2,
//           docs/services/contract_deployment_as_a_service.md §5.

import type { Address } from "viem";

export interface DeployedContract {
  address: Address;
  deployer?: Address;
  tx_hash?: string;
  block_number?: number;
  gas_used?: number;
  constructor_args?: unknown[];
  deployed_at?: string;
  verified?: boolean;
  explorer_url?: string;
}

export interface DeploymentRecord {
  network: string;
  chain_id: number;
  rpc_url: string;
  explorer?: string;
  native_currency?: { name: string; symbol: string; decimals: number };
  deployed_at?: string;
  contracts: Record<string, DeployedContract>;
}

/**
 * Read a deployment JSON from a string. Throws if shape is invalid.
 */
export function parseDeploymentRecord(json: string): DeploymentRecord {
  const obj = JSON.parse(json);
  if (typeof obj !== "object" || obj === null) {
    throw new Error("deployment record is not an object");
  }
  if (typeof obj.network !== "string") {
    throw new Error("deployment record missing 'network'");
  }
  if (typeof obj.chain_id !== "number") {
    throw new Error("deployment record missing 'chain_id'");
  }
  if (typeof obj.contracts !== "object" || obj.contracts === null) {
    throw new Error("deployment record missing 'contracts'");
  }
  return obj as DeploymentRecord;
}

/**
 * Load a deployment record from a URL or local filesystem path.
 *
 * In browser / Tauri webview: fetches from a URL relative to the dApp.
 * In node: reads from the filesystem. Routing is automatic based on
 * environment.
 */
export async function loadDeploymentRecord(
  source: string,
): Promise<DeploymentRecord> {
  // Node (CLI / tests)
  if (typeof window === "undefined" && !source.startsWith("http")) {
    const { readFile } = await import("node:fs/promises");
    const text = await readFile(source, "utf-8");
    return parseDeploymentRecord(text);
  }
  // Browser
  const res = await fetch(source);
  if (!res.ok) {
    throw new Error(`failed to load deployment ${source}: HTTP ${res.status}`);
  }
  return parseDeploymentRecord(await res.text());
}

/**
 * Resolve a contract's address from a deployment record. Throws if the
 * contract is not in the catalog.
 */
export function addressOf(
  record: DeploymentRecord,
  contractName: string,
): Address {
  const entry = record.contracts[contractName];
  if (!entry) {
    throw new Error(
      `Contract '${contractName}' not in deployment record for ${record.network}.`,
    );
  }
  return entry.address;
}
