// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// viem-backed EVM wallet client.
// Contract: docs/services/wallet_connection_as_a_service.md §4.

import {
  type Address,
  type Chain,
  type Hex,
  type WalletClient,
  type PublicClient,
  createPublicClient,
  createWalletClient,
  custom,
  http,
  numberToHex,
  hexToNumber,
} from "viem";
import {
  discoverProviders,
  pickProvider,
  type AnnouncedProvider,
  type EIP1193Provider,
} from "./eip6963.js";
import { CHAINS, chainByKey, type ChainEntry } from "./chains.js";
import {
  ChainAddRequired,
  ChainMismatch,
  UnknownChain,
  WalletNotFound,
  WalletRejected,
} from "./errors.js";

export interface ConnectOptions {
  /** EIP-6963 rdns hint (e.g. "io.metamask"); first matching provider wins. */
  preferredRdns?: string;
  /** EIP-6963 discovery wait window. Default 500ms. */
  discoveryWaitMs?: number;
  /** Extra Chain entries to merge into the catalog for this session. */
  extraChains?: ChainEntry[];
}

export interface ConnectedAccount {
  address: Address;
  chainId: number;
  rdns: string;
  /** Underlying EIP-1193 provider. */
  provider: EIP1193Provider;
  /** viem WalletClient bound to (provider, chain). */
  walletClient: WalletClient;
  /** viem PublicClient bound to the chain's RPC. */
  publicClient: PublicClient;
  /** Catalog entry for the active chain. */
  chain: ChainEntry;
}

/**
 * Discover wallets and connect to the first matching provider.
 *
 * @throws WalletNotFound when no EIP-6963 providers (and no legacy window.ethereum) are present
 * @throws WalletRejected when the user rejects the eth_requestAccounts prompt
 */
export async function connect(opts: ConnectOptions = {}): Promise<ConnectedAccount> {
  const providers = await discoverProviders(opts.discoveryWaitMs);
  const picked = pickProvider(providers, opts.preferredRdns);
  if (!picked) throw new WalletNotFound();
  return await connectWithProvider(picked, opts);
}

/**
 * Connect to a specific announced provider (for UIs that render a picker).
 */
export async function connectWithProvider(
  picked: AnnouncedProvider,
  opts: ConnectOptions = {},
): Promise<ConnectedAccount> {
  // 1. Request accounts.
  let accounts: Address[];
  try {
    accounts = (await picked.provider.request({ method: "eth_requestAccounts" })) as Address[];
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    // EIP-1193 code 4001 = user rejected
    if (/rejected|denied|4001/i.test(message)) throw new WalletRejected("connect");
    throw err;
  }
  const address = accounts[0];
  if (!address) throw new WalletRejected("connect");

  // 2. Read chainId.
  const chainIdHex = (await picked.provider.request({ method: "eth_chainId" })) as Hex;
  const chainId = hexToNumber(chainIdHex);

  // 3. Resolve catalog entry.
  const catalog = mergeCatalog(opts.extraChains);
  const chain = chainForId(catalog, chainId) ?? {
    // Unknown chain — synthesize a minimal entry so viem clients still work.
    id: chainId,
    name: `Chain ${chainId}`,
    nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 },
    rpcUrls: { default: { http: [] } },
  } as ChainEntry;

  // 4. Build viem clients.
  const walletClient = createWalletClient({
    account: address,
    chain: chain as Chain,
    transport: custom(picked.provider as { request: EIP1193Provider["request"] }),
  });
  const publicClient = createPublicClient({
    chain: chain as Chain,
    transport: chain.rpcUrls.default.http[0]
      ? http(chain.rpcUrls.default.http[0])
      : custom(picked.provider as { request: EIP1193Provider["request"] }),
  });

  return {
    address,
    chainId,
    rdns: picked.info.rdns,
    provider: picked.provider,
    walletClient,
    publicClient,
    chain,
  };
}

/**
 * Switch the wallet to a different chain in the catalog. If the wallet
 * doesn't know the chain, throws ChainAddRequired — caller can then call
 * `addChain()` and retry.
 */
export async function switchChain(
  account: ConnectedAccount,
  chainKey: string,
  opts: { extraChains?: ChainEntry[] } = {},
): Promise<ConnectedAccount> {
  const catalog = mergeCatalog(opts.extraChains);
  const target = catalog[chainKey];
  if (!target) throw new UnknownChain(chainKey);

  try {
    await account.provider.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: numberToHex(target.id) }],
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    // EIP-3326 code 4902 = chain not added
    if (/4902|unrecognized chain/i.test(message)) {
      throw new ChainAddRequired(chainKey);
    }
    if (/rejected|denied|4001/i.test(message)) throw new WalletRejected("switchChain");
    throw err;
  }

  // Re-read chainId after the switch.
  const chainIdHex = (await account.provider.request({ method: "eth_chainId" })) as Hex;
  const chainId = hexToNumber(chainIdHex);
  if (chainId !== target.id) throw new ChainMismatch(target.id, chainId);

  const walletClient = createWalletClient({
    account: account.address,
    chain: target as Chain,
    transport: custom(account.provider as { request: EIP1193Provider["request"] }),
  });
  const publicClient = createPublicClient({
    chain: target as Chain,
    transport: target.rpcUrls.default.http[0]
      ? http(target.rpcUrls.default.http[0])
      : custom(account.provider as { request: EIP1193Provider["request"] }),
  });

  return {
    ...account,
    chainId,
    chain: target,
    walletClient,
    publicClient,
  };
}

/**
 * Ask the wallet to add a chain entry it doesn't yet know.
 * The user sees a confirmation prompt; reject surfaces as WalletRejected.
 */
export async function addChain(
  account: ConnectedAccount,
  chainKey: string,
  opts: { extraChains?: ChainEntry[] } = {},
): Promise<void> {
  const catalog = mergeCatalog(opts.extraChains);
  const chain = catalog[chainKey];
  if (!chain) throw new UnknownChain(chainKey);

  try {
    await account.provider.request({
      method: "wallet_addEthereumChain",
      params: [
        {
          chainId: numberToHex(chain.id),
          chainName: chain.name,
          nativeCurrency: chain.nativeCurrency,
          rpcUrls: chain.rpcUrls.default.http,
          blockExplorerUrls: chain.blockExplorers?.default.url
            ? [chain.blockExplorers.default.url]
            : undefined,
        },
      ],
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (/rejected|denied|4001/i.test(message)) throw new WalletRejected("addChain");
    throw err;
  }
}

/**
 * Sign a message with the connected account (EIP-191 personal_sign).
 */
export async function signMessage(account: ConnectedAccount, message: string): Promise<Hex> {
  try {
    return await account.walletClient.signMessage({
      account: account.address,
      message,
    });
  } catch (err) {
    const text = err instanceof Error ? err.message : String(err);
    if (/rejected|denied|4001/i.test(text)) throw new WalletRejected("signMessage");
    throw err;
  }
}

/**
 * Send a transaction. Wallet pops a confirmation. Returns the tx hash;
 * caller waits for the receipt separately via the contract layer.
 */
export async function sendTransaction(
  account: ConnectedAccount,
  tx: { to: Address; value?: bigint; data?: Hex; gas?: bigint },
): Promise<Hex> {
  try {
    return await account.walletClient.sendTransaction({
      account: account.address,
      chain: account.chain as Chain,
      to: tx.to,
      value: tx.value,
      data: tx.data,
      gas: tx.gas,
    });
  } catch (err) {
    const text = err instanceof Error ? err.message : String(err);
    if (/rejected|denied|4001/i.test(text)) throw new WalletRejected("sendTransaction");
    throw err;
  }
}

// ─── helpers ────────────────────────────────────────────────────

function mergeCatalog(extras?: ChainEntry[]): Record<string, ChainEntry> {
  if (!extras || extras.length === 0) return CHAINS;
  const merged: Record<string, ChainEntry> = { ...CHAINS };
  for (const c of extras) {
    const key = String(c.id);
    merged[key] = c;
  }
  return merged;
}

function chainForId(catalog: Record<string, ChainEntry>, id: number): ChainEntry | undefined {
  for (const c of Object.values(catalog)) {
    if (c.id === id) return c;
  }
  return undefined;
}
