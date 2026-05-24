// SPDX-License-Identifier: Apache-2.0
//
// BankonethSession — connection-layer wrapper for window.ethereum + viem.
//
// Design notes (per the connection-refit plan):
//   - publicClient is ALWAYS available (HTTP transport, no wallet required)
//     so read-only flows work pre-connect.
//   - walletClient is null until connect() succeeds.
//   - No silent reconnect on construction — `eth_accounts` is NOT polled.
//     The user must press the Connect button explicitly.
//   - On connect(), resolveReverse() populates the primary ENS name. Failure
//     leaves primaryName null; not an error.
//   - Listens for accountsChanged / chainChanged / disconnect on
//     window.ethereum and re-emits via subscribe().
//   - switchChain() calls wallet_switchEthereumChain; the bar surfaces
//     errors (e.g. the user rejects).

import {
  type Address,
  type Chain,
  type PublicClient,
  type WalletClient,
  createPublicClient,
  createWalletClient,
  custom,
  http,
} from "viem";
import { mainnet } from "viem/chains";

import { resolveReverse } from "./universal-resolver";

/** Snapshot of session state. Immutable per emission. */
export interface SessionState {
  /** True when walletClient is bound to a real account. */
  connected: boolean;
  /** Connected account address, or null. */
  address: Address | null;
  /** ENS primary name for `address`, or null if none/lookup failed. */
  primaryName: string | null;
  /** Current chain id (from the wallet when connected, else `defaultChain.id`). */
  chainId: number;
  /** True if window.ethereum is present at construction time. */
  walletAvailable: boolean;
}

/** Optional config for `BankonethSession.create`. */
export interface SessionConfig {
  /** Default chain when no wallet attached. Defaults to viem `mainnet`. */
  defaultChain?: Chain;
  /** HTTP RPC URL for the publicClient. Defaults to the chain's default RPC. */
  rpcUrl?: string;
}

/** Minimal EIP-1193 surface we depend on. */
interface Eip1193Provider {
  request(args: { method: string; params?: unknown[] | object }): Promise<unknown>;
  on?(event: string, cb: (...args: unknown[]) => void): void;
  removeListener?(event: string, cb: (...args: unknown[]) => void): void;
}

function getInjected(): Eip1193Provider | null {
  if (typeof window === "undefined") return null;
  const eth = (window as { ethereum?: Eip1193Provider }).ethereum;
  return eth ?? null;
}

const ZERO_CHAIN = mainnet;

export class BankonethSession {
  readonly publicClient: PublicClient;
  walletClient: WalletClient | null = null;

  private _state: SessionState;
  private _provider: Eip1193Provider | null;
  private _defaultChain: Chain;
  private _listeners = new Set<(s: SessionState) => void>();
  private _bound: Array<[string, (...args: unknown[]) => void]> = [];

  private constructor(cfg: SessionConfig) {
    this._defaultChain = cfg.defaultChain ?? ZERO_CHAIN;
    this._provider = getInjected();

    this.publicClient = createPublicClient({
      chain:     this._defaultChain,
      transport: cfg.rpcUrl ? http(cfg.rpcUrl) : http(),
    });

    this._state = {
      connected:       false,
      address:         null,
      primaryName:     null,
      chainId:         this._defaultChain.id,
      walletAvailable: this._provider !== null,
    };

    if (this._provider) this._bindProviderEvents();
  }

  static create(cfg: SessionConfig = {}): BankonethSession {
    return new BankonethSession(cfg);
  }

  /** Current state snapshot. */
  state(): SessionState { return this._state; }

  /** Subscribe to state changes; returns an unsubscribe fn. */
  subscribe(cb: (s: SessionState) => void): () => void {
    this._listeners.add(cb);
    return () => this._listeners.delete(cb);
  }

  /**
   * Prompt the user to connect via `eth_requestAccounts`. After the user
   * approves, populates `address`, `walletClient`, `primaryName`, `chainId`,
   * and emits a state change.
   *
   * Throws if window.ethereum is missing (caller should pre-check
   * `state().walletAvailable`).
   */
  async connect(): Promise<SessionState> {
    const p = this._provider;
    if (!p) throw new Error("No injected wallet detected (window.ethereum is undefined)");

    const accounts = (await p.request({ method: "eth_requestAccounts" })) as string[];
    if (!accounts || accounts.length === 0) {
      throw new Error("eth_requestAccounts returned no accounts");
    }
    const address = accounts[0] as Address;

    const chainHex = (await p.request({ method: "eth_chainId" })) as string;
    const chainId = parseInt(chainHex, 16);

    this.walletClient = createWalletClient({
      account:   address,
      chain:     this._defaultChain,
      transport: custom(p as Parameters<typeof custom>[0]),
    });

    // Best-effort primary-name lookup.
    let primaryName: string | null = null;
    try {
      const r = await resolveReverse({ client: this.publicClient, address });
      primaryName = r.primary ?? null;
    } catch {
      primaryName = null;
    }

    this._state = {
      connected:       true,
      address,
      primaryName,
      chainId,
      walletAvailable: true,
    };
    this._emit();
    return this._state;
  }

  /**
   * Clear in-memory connection state. Does NOT revoke wallet permissions —
   * EIP-1193 has no revoke method. Returning users will need to reconnect
   * explicitly (per the no-silent-reconnect rule).
   */
  async disconnect(): Promise<void> {
    this.walletClient = null;
    this._state = {
      connected:       false,
      address:         null,
      primaryName:     null,
      chainId:         this._defaultChain.id,
      walletAvailable: this._state.walletAvailable,
    };
    this._emit();
  }

  /**
   * Ask the wallet to switch to `chainId`. Forwards EIP-3326. The bar
   * surfaces any wallet-side rejection; we re-throw.
   */
  async switchChain(chainId: number): Promise<void> {
    const p = this._provider;
    if (!p) throw new Error("No injected wallet detected");
    await p.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: "0x" + chainId.toString(16) }],
    });
    // `chainChanged` event fires after the wallet completes the switch,
    // which updates _state. No need to mutate here.
  }

  /** Re-read the primary name (e.g. after the user changes their reverse). */
  async refreshPrimaryName(): Promise<void> {
    if (!this._state.address) return;
    try {
      const r = await resolveReverse({ client: this.publicClient, address: this._state.address });
      this._state = { ...this._state, primaryName: r.primary ?? null };
      this._emit();
    } catch { /* swallow */ }
  }

  // ── Internal ─────────────────────────────────────────────────────

  private _emit(): void {
    for (const cb of this._listeners) {
      try { cb(this._state); } catch { /* listener bugs shouldn't break siblings */ }
    }
  }

  private _bindProviderEvents(): void {
    const p = this._provider!;
    if (!p.on) return;

    const onAccountsChanged = (accountsRaw: unknown) => {
      const accounts = (accountsRaw as string[]) ?? [];
      if (accounts.length === 0) {
        void this.disconnect();
        return;
      }
      const next = accounts[0] as Address;
      if (next === this._state.address) return;
      this.walletClient = createWalletClient({
        account:   next,
        chain:     this._defaultChain,
        transport: custom(p as Parameters<typeof custom>[0]),
      });
      this._state = { ...this._state, address: next, connected: true, primaryName: null };
      this._emit();
      void this.refreshPrimaryName();
    };

    const onChainChanged = (chainHex: unknown) => {
      const chainId = parseInt(String(chainHex), 16);
      this._state = { ...this._state, chainId };
      this._emit();
    };

    const onDisconnect = () => { void this.disconnect(); };

    p.on("accountsChanged", onAccountsChanged as (...args: unknown[]) => void);
    p.on("chainChanged",    onChainChanged    as (...args: unknown[]) => void);
    p.on("disconnect",      onDisconnect      as (...args: unknown[]) => void);

    this._bound.push(
      ["accountsChanged", onAccountsChanged as (...args: unknown[]) => void],
      ["chainChanged",    onChainChanged    as (...args: unknown[]) => void],
      ["disconnect",      onDisconnect      as (...args: unknown[]) => void],
    );
  }

  /** Tear down the provider listeners. Call when the session goes out of scope. */
  dispose(): void {
    const p = this._provider;
    if (!p?.removeListener) return;
    for (const [evt, fn] of this._bound) p.removeListener(evt, fn);
    this._bound = [];
    this._listeners.clear();
  }
}
