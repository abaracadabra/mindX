/**
 * mindX API client — wraps https://mindx.pythai.net/api.
 *
 * The mindX service emits EIP-712 signed advisory attestations about iDEBT
 * positions or their holders. Settlement on-chain is via `MindXBridge.settle`.
 */

import { type Address, type Hex, getAddress, hexToBigInt } from "viem";

export const MINDX_DEFAULT_URL = "https://mindx.pythai.net/api";

/** Raw attestation as emitted by mindX. Mirrors the Solidity struct. */
export interface MindXAttestation {
  requestId:    Hex;     // bytes32
  claimHash:    Hex;     // bytes32
  issuedAt:     number;  // uint64 seconds
  modelVersion: number;  // uint32
  riskScore:    number;  // uint16 bps (0..10000)
  subject:      Address;
}

/** EIP-712 signature over the Attestation. */
export type MindXSignature = Hex;

export interface MindXAdvisoryRequest {
  /** EVM address to score. */
  subject: Address;
  /** Optional iDEBT tokenId the advice is about. */
  positionId?: bigint | number;
  /** Opaque context passed straight through to the mindX model. */
  context?: Record<string, unknown>;
}

export interface MindXAdvisoryResponse {
  attestation: MindXAttestation;
  signature:   MindXSignature;
  /** Full advisory text; hashed into `attestation.claimHash`. */
  advisory:    string;
}

export interface MindXClientOptions {
  /** Base URL. Defaults to mindx.pythai.net/api. */
  baseUrl?: string;
  /** Bearer token for authenticated endpoints. */
  apiKey?: string;
  /** Customised fetch. Useful for wiring retries / tracing. */
  fetch?: typeof globalThis.fetch;
}

export class MindXClient {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly fetchImpl: typeof globalThis.fetch;

  constructor(opts: MindXClientOptions = {}) {
    this.baseUrl = (opts.baseUrl ?? MINDX_DEFAULT_URL).replace(/\/$/, "");
    this.apiKey = opts.apiKey;
    this.fetchImpl = opts.fetch ?? globalThis.fetch.bind(globalThis);
  }

  /** Request a fresh advisory + attestation for a subject. */
  async advisory(req: MindXAdvisoryRequest): Promise<MindXAdvisoryResponse> {
    const body = {
      subject: getAddress(req.subject),
      positionId: req.positionId?.toString(),
      context: req.context ?? {}
    };
    const res = await this.fetchImpl(`${this.baseUrl}/v1/advisory`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(body)
    });
    if (!res.ok) {
      throw new Error(`mindX advisory failed: ${res.status} ${await res.text()}`);
    }
    const json = (await res.json()) as MindXAdvisoryResponse;
    // Normalise numeric fields arriving as strings.
    json.attestation.issuedAt     = Number(json.attestation.issuedAt);
    json.attestation.modelVersion = Number(json.attestation.modelVersion);
    json.attestation.riskScore    = Number(json.attestation.riskScore);
    return json;
  }

  /** Retrieve the currently published mindX signing key. */
  async signingKey(): Promise<Address> {
    const res = await this.fetchImpl(`${this.baseUrl}/v1/signing-key`);
    if (!res.ok) throw new Error(`mindX signingKey failed: ${res.status}`);
    const { address } = (await res.json()) as { address: Address };
    return getAddress(address);
  }

  /** Convert a Solidity 1e18-scaled big-int into a riskScore bps (0..10000). */
  static wadToBps(wad: bigint): number {
    const bps = Number((wad * 10_000n) / 10n ** 18n);
    return Math.min(10_000, Math.max(0, bps));
  }

  /** Compute the numeric riskScore from a hex WAD value. */
  static riskScoreFromHexWad(hex: Hex): number {
    return MindXClient.wadToBps(hexToBigInt(hex));
  }

  private headers(): HeadersInit {
    const h: HeadersInit = { "content-type": "application/json" };
    if (this.apiKey) (h as Record<string, string>).authorization = `Bearer ${this.apiKey}`;
    return h;
  }
}
