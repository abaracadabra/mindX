/**
 * AgenticPlace API client — wraps https://agenticplace.pythai.net.
 *
 * AgenticPlace is the off-chain agent marketplace that mirrors the on-chain
 * `AgenticPlaceRegistry`. Agents publish capabilities here and consumers
 * (iDEBT holders, DAIO voters) discover them.
 */

import { type Address, type Hex, keccak256, toHex, getAddress } from "viem";

export const AGENTICPLACE_DEFAULT_URL = "https://agenticplace.pythai.net";

export interface AgentCard {
  agentId:   Hex;      // bytes32 = keccak256(slug)
  slug:      string;   // human-readable identifier
  owner:     Address;
  endpoint:  string;
  capabilities: string[];
  reputation: bigint;  // 1e18-scaled
  registeredAt: number;
  lastActivity: number;
}

export interface DiscoveryFilter {
  capability?: string;
  minReputation?: bigint;
  q?: string;
}

export interface AgenticPlaceClientOptions {
  baseUrl?: string;
  apiKey?: string;
  fetch?: typeof globalThis.fetch;
}

export class AgenticPlaceClient {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly fetchImpl: typeof globalThis.fetch;

  constructor(opts: AgenticPlaceClientOptions = {}) {
    this.baseUrl = (opts.baseUrl ?? AGENTICPLACE_DEFAULT_URL).replace(/\/$/, "");
    this.apiKey = opts.apiKey;
    this.fetchImpl = opts.fetch ?? globalThis.fetch.bind(globalThis);
  }

  /** Fetch an agent card by its slug. */
  async getAgent(slug: string): Promise<AgentCard> {
    const res = await this.fetchImpl(`${this.baseUrl}/api/agents/${encodeURIComponent(slug)}`);
    if (!res.ok) throw new Error(`getAgent failed: ${res.status}`);
    return AgenticPlaceClient.normalise(await res.json());
  }

  /** Find agents matching a capability or free-text query. */
  async discover(filter: DiscoveryFilter): Promise<AgentCard[]> {
    const qs = new URLSearchParams();
    if (filter.capability) qs.set("capability", filter.capability);
    if (filter.q)          qs.set("q",          filter.q);
    if (filter.minReputation !== undefined) qs.set("minRep", filter.minReputation.toString());

    const res = await this.fetchImpl(`${this.baseUrl}/api/agents?${qs.toString()}`);
    if (!res.ok) throw new Error(`discover failed: ${res.status}`);
    const arr = (await res.json()) as unknown[];
    return arr.map(a => AgenticPlaceClient.normalise(a));
  }

  /** Register a new agent off-chain. The on-chain `register(agentId, endpoint)` must also be called. */
  async register(slug: string, endpoint: string, capabilities: string[]): Promise<AgentCard> {
    const res = await this.fetchImpl(`${this.baseUrl}/api/agents`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ slug, endpoint, capabilities })
    });
    if (!res.ok) throw new Error(`register failed: ${res.status} ${await res.text()}`);
    return AgenticPlaceClient.normalise(await res.json());
  }

  /** Fetch the current chain-map JSON used by the iDEBT UI. */
  async chainmap(): Promise<ChainMapEntry[]> {
    const res = await this.fetchImpl(`${this.baseUrl}/allchain.json`);
    if (!res.ok) {
      // Fall back to HTML scraping sentinel — rarely needed.
      throw new Error(`chainmap failed: ${res.status}`);
    }
    return (await res.json()) as ChainMapEntry[];
  }

  /** Compute the on-chain agentId for a slug. */
  static agentIdForSlug(slug: string): Hex {
    return keccak256(toHex(slug));
  }

  private headers(): HeadersInit {
    const h: HeadersInit = { "content-type": "application/json" };
    if (this.apiKey) (h as Record<string, string>).authorization = `Bearer ${this.apiKey}`;
    return h;
  }

  private static normalise(raw: unknown): AgentCard {
    const r = raw as Record<string, unknown>;
    return {
      agentId:      r.agentId as Hex,
      slug:         r.slug as string,
      owner:        getAddress(r.owner as string),
      endpoint:     r.endpoint as string,
      capabilities: Array.isArray(r.capabilities) ? (r.capabilities as string[]) : [],
      reputation:   BigInt(r.reputation as string | number),
      registeredAt: Number(r.registeredAt),
      lastActivity: Number(r.lastActivity)
    };
  }
}

export interface ChainMapEntry {
  chainId:      number;
  family:       "EVM" | "ALGORAND" | "COSMOS" | "SOLANA" | "SUI";
  name:         string;
  nativeGas:    string;
  stableAnchor: string;
  rpcHint:      string;
  deployed?: {
    voteToken?: Address;
    treasury?:  Address;
    governor?:  Address;
    oracle?:    Address;
    index?:     Address;
    debtToken?: Address;
    x402?:      Address;
    mindx?:     Address;
    agents?:    Address;
    bankon?:    Address;
  };
}
