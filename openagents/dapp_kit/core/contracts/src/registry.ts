// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Contract registry — TS port of openagents/contracts/registry.py.
// Contract: docs/services/contract_interaction_as_a_service.md §2.

import {
  type Abi,
  type Address,
  type Hash,
  type PublicClient,
  type WalletClient,
  createPublicClient,
  getContract,
  http,
} from "viem";
import { CHAINS, type ChainEntry, chainById } from "@openagents/wallet/chains";
import type { ConnectedAccount } from "@openagents/wallet";
import {
  type DeploymentRecord,
  loadDeploymentRecord,
} from "./deployments.js";
import { loadAbi, type AbiLoaderConfig } from "./abi-loader.js";

export interface ContractsForOptions {
  /** Source for deployments/<network>.json — URL or path. */
  deploymentSource?: string;
  /** Pre-parsed deployment record (overrides deploymentSource). */
  deployment?: DeploymentRecord;
  /** Connected wallet account from @openagents/wallet (required for write calls). */
  signer?: ConnectedAccount;
  /** ABI loader configuration. */
  abi?: AbiLoaderConfig;
  /** Chain catalog entry override (when not in CHAINS). */
  chain?: ChainEntry;
}

export interface ContractHandle {
  name: string;
  address: Address;
  abi: Abi;
  /** viem getContract({ publicClient }) — read accessor. */
  read: ReturnType<typeof getContract>["read"];
  /** viem getContract({ walletClient }) — write accessor (signer required). */
  write?: ReturnType<typeof getContract>["write"];
  /** Decode an event log against this contract's ABI. */
  decodeLog: (log: { topics: readonly Hash[]; data: `0x${string}` }) => unknown;
}

export interface ContractsRegistry {
  /** Network key (e.g. "0g-mainnet"). */
  network: string;
  /** EIP-155 chain id. */
  chainId: number;
  /** Chain catalog entry. */
  chain: ChainEntry;
  /** PublicClient for read-only calls. */
  publicClient: PublicClient;
  /** WalletClient for write calls (undefined when no signer). */
  walletClient: WalletClient | undefined;
  /** List the catalog. */
  list(): string[];
  /** Get a contract handle by name. Throws if not in the deployment record. */
  get(name: string): ContractHandle;
  /** Indexer-style access: registry[name] (proxy). */
  [contract: string]: unknown;
}

/**
 * Build a typed registry against a network's deployment record.
 */
export async function contractsFor(
  networkKey: string,
  opts: ContractsForOptions = {},
): Promise<ContractsRegistry> {
  // 1. Resolve deployment record
  const record =
    opts.deployment ??
    (await loadDeploymentRecord(
      opts.deploymentSource ?? `/deployments/${networkKey}.json`,
    ));

  // 2. Resolve chain catalog entry
  const chain = opts.chain ?? chainById(record.chain_id) ?? CHAINS[networkKey];
  if (!chain) {
    throw new Error(
      `No chain in catalog for ${networkKey} (chain_id=${record.chain_id}). Pass opts.chain.`,
    );
  }

  // 3. Build viem clients
  const publicClient = createPublicClient({
    chain,
    transport: http(record.rpc_url || chain.rpcUrls.default.http[0]),
  });
  const walletClient = opts.signer?.walletClient;

  // 4. Lazy-load ABIs per contract on first access
  const handles = new Map<string, ContractHandle>();

  async function buildHandle(name: string): Promise<ContractHandle> {
    const entry = record.contracts[name];
    if (!entry) {
      throw new Error(
        `Contract '${name}' not in deployment record for ${networkKey}.`,
      );
    }
    const abi = await loadAbi(name, opts.abi ?? {});
    const c = getContract({
      address: entry.address,
      abi,
      client: walletClient
        ? { public: publicClient, wallet: walletClient }
        : { public: publicClient },
    });
    const handle: ContractHandle = {
      name,
      address: entry.address,
      abi,
      read: c.read,
      write: c.write,
      decodeLog: (log) => {
        // viem exposes decodeEventLog; the caller can also use it directly.
        // We inline a thin wrapper here so the handle is one-stop.
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { decodeEventLog } = require("viem") as typeof import("viem");
        return decodeEventLog({ abi, topics: log.topics, data: log.data });
      },
    };
    return handle;
  }

  // Resolve all handle names up front (deterministic list) but defer ABI fetch
  // until a contract is accessed.
  const names = Object.keys(record.contracts);

  const baseRegistry: ContractsRegistry = {
    network: networkKey,
    chainId: record.chain_id,
    chain,
    publicClient,
    walletClient,
    list: () => [...names],
    get(name: string): ContractHandle {
      const cached = handles.get(name);
      if (!cached) {
        throw new Error(
          `Contract '${name}' not built yet. Use the async pattern: await contractsFor(...) then registry.${name} after preload, or call await preload(name).`,
        );
      }
      return cached;
    },
  };

  // Pre-build all handles in parallel so the synchronous access shape works.
  const built = await Promise.all(
    names.map(async (n) => [n, await buildHandle(n)] as const),
  );
  for (const [n, h] of built) handles.set(n, h);

  // Wrap in a Proxy so `registry.AgentRegistry` returns the handle.
  return new Proxy(baseRegistry, {
    get(target, prop, recv) {
      if (typeof prop === "string" && handles.has(prop)) {
        return handles.get(prop);
      }
      return Reflect.get(target, prop, recv);
    },
  });
}
