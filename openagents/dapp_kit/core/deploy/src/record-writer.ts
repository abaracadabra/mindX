// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Atomic write of openagents/deployments/<network>.json.
// Contract: docs/services/contract_deployment_as_a_service.md §5.

import type { DeploymentRecord, DeployedContract } from "@openagents/contracts";

/**
 * Append a contract entry to an existing deployment record (or create the
 * record fresh). Writes atomically via `<file>.tmp` then rename.
 *
 * @param deploymentsDir absolute path to openagents/deployments/
 * @param networkKey catalog key (becomes `<networkKey>.json` filename)
 * @param chainId EIP-155 id
 * @param rpcUrl
 * @param contractName
 * @param entry
 */
export async function appendDeployedContract(
  deploymentsDir: string,
  networkKey: string,
  chainId: number,
  rpcUrl: string,
  contractName: string,
  entry: DeployedContract,
): Promise<string> {
  if (typeof window !== "undefined") {
    throw new Error("record-writer runs server-side only.");
  }
  const { readFile, writeFile, rename, mkdir } = await import("node:fs/promises");
  const path = `${deploymentsDir.replace(/\/$/, "")}/${networkKey}.json`;
  const tmp = `${path}.tmp`;

  await mkdir(deploymentsDir, { recursive: true });

  let record: DeploymentRecord;
  try {
    const existing = await readFile(path, "utf-8");
    record = JSON.parse(existing) as DeploymentRecord;
  } catch {
    record = {
      network: networkKey,
      chain_id: chainId,
      rpc_url: rpcUrl,
      deployed_at: new Date().toISOString(),
      contracts: {},
    };
  }
  record.contracts[contractName] = entry;
  // Keep deployed_at as the latest-touched timestamp.
  record.deployed_at = new Date().toISOString();

  await writeFile(tmp, JSON.stringify(record, null, 2), "utf-8");
  await rename(tmp, path);
  return path;
}
