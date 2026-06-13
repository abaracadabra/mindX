/**
 * BANKON API client — wraps https://bankon.pythai.net.
 *
 * BANKON issues AlgoIDNFT sovereign identities on Algorand and signs EVM
 * binding attestations consumed by `BANKONConnector.bind`.
 */

import { type Address, type Hex, getAddress } from "viem";

export const BANKON_DEFAULT_URL = "https://bankon.pythai.net";

export interface BANKONBindingRequest {
  algoIdRoot: Hex;          // 32-byte commitment from AlgoIDNFT
  evm:        Address;      // EVM wallet to bind to
  chainId:    number;       // EIP-155 chain id (or ChainMapping sentinel)
}

export interface BANKONBindingResponse {
  sig: Hex;                 // ECDSA signature bytes (r || s || v)
  signer: Address;          // BANKON signing key
  validThrough?: number;    // unix seconds — informational only
}

export interface BANKONIdentity {
  algoIdRoot:   Hex;
  algoAddress:  string;     // base32 Algorand address
  evmBindings:  { chainId: number; address: Address; boundAt: number; active: boolean }[];
  sovereign:    boolean;
}

export interface BANKONClientOptions {
  baseUrl?: string;
  apiKey?: string;
  fetch?: typeof globalThis.fetch;
}

export class BANKONClient {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly fetchImpl: typeof globalThis.fetch;

  constructor(opts: BANKONClientOptions = {}) {
    this.baseUrl = (opts.baseUrl ?? BANKON_DEFAULT_URL).replace(/\/$/, "");
    this.apiKey = opts.apiKey;
    this.fetchImpl = opts.fetch ?? globalThis.fetch.bind(globalThis);
  }

  /** Request a co-signed binding for (algoIdRoot, evm, chainId). */
  async requestBinding(req: BANKONBindingRequest): Promise<BANKONBindingResponse> {
    const body = { ...req, evm: getAddress(req.evm) };
    const res = await this.fetchImpl(`${this.baseUrl}/api/bind`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error(`BANKON bind failed: ${res.status} ${await res.text()}`);
    const { sig, signer, validThrough } = (await res.json()) as BANKONBindingResponse;
    return { sig, signer: getAddress(signer), validThrough };
  }

  /** Look up a sovereign identity by its Algorand address. */
  async identity(algoAddress: string): Promise<BANKONIdentity | null> {
    const res = await this.fetchImpl(
      `${this.baseUrl}/api/identity/${encodeURIComponent(algoAddress)}`
    );
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`BANKON identity failed: ${res.status}`);
    const raw = (await res.json()) as BANKONIdentity;
    raw.evmBindings = raw.evmBindings.map(b => ({
      ...b,
      address: getAddress(b.address),
      chainId: Number(b.chainId),
      boundAt: Number(b.boundAt)
    }));
    return raw;
  }

  /** Published BANKON signer for the current protocol version. */
  async signer(): Promise<Address> {
    const res = await this.fetchImpl(`${this.baseUrl}/api/signer`);
    if (!res.ok) throw new Error(`BANKON signer failed: ${res.status}`);
    const { address } = (await res.json()) as { address: Address };
    return getAddress(address);
  }

  private headers(): HeadersInit {
    const h: HeadersInit = { "content-type": "application/json" };
    if (this.apiKey) (h as Record<string, string>).authorization = `Bearer ${this.apiKey}`;
    return h;
  }
}
