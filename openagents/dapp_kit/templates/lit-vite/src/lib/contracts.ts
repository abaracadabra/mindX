// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved

import { contractsFor, type ContractsRegistry } from "@openagents/contracts";
import type { ConnectedAccount } from "@openagents/wallet";

/**
 * Build a registry for the given network + signer. The dApp typically
 * pins a single network; if you need multi-chain, call this per chain.
 */
export async function buildRegistry(
  networkKey: string,
  signer: ConnectedAccount,
): Promise<ContractsRegistry> {
  return await contractsFor(networkKey, {
    signer,
    deploymentSource: `/deployments/${networkKey}.json`,
  });
}
