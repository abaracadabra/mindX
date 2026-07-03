/**
 * Parsec x402 client — wraps https://x402.parsec.finance.
 *
 * Parsec acts as the facilitator between iDEBT (on EVM) and the user's
 * Algorand wallet. The client:
 *   1. looks up the price for a scope,
 *   2. produces a payment intent the caller can hand to parsec-wallet,
 *   3. polls for settlement, and
 *   4. returns the on-chain-ready `Receipt` + signature bundle.
 */

import {
  type Address,
  type Hex,
  keccak256,
  toHex,
  getAddress
} from "viem";

export const X402_DEFAULT_URL = "https://x402.parsec.finance";

export interface X402Price {
  scope:  Hex;
  amount: bigint;
  asset:  Hex;         // bytes32, e.g. toHex("USDCa", { size: 32 })
  assetSymbol: string; // e.g. "USDCa"
}

export interface X402PaymentIntent {
  payer:     Address;
  scope:     Hex;
  amount:    bigint;
  asset:     Hex;
  assetSymbol: string;
  facilitatorAlgoAddress: string; // where to send Algorand payment
  expires:   number;
  nonce:     Hex;
}

export interface X402Receipt {
  facilitator: Address;
  payer:       Address;
  amount:      bigint;
  asset:       Hex;
  scope:       Hex;
  nonce:       bigint;
  expiry:      bigint;
  algoTxId:    Hex;
}

export interface X402ReceiptBundle {
  receipt:   X402Receipt;
  signature: Hex;
}

export interface ParsecX402ClientOptions {
  baseUrl?: string;
  apiKey?: string;
  fetch?: typeof globalThis.fetch;
}

export class ParsecX402Client {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly fetchImpl: typeof globalThis.fetch;

  constructor(opts: ParsecX402ClientOptions = {}) {
    this.baseUrl = (opts.baseUrl ?? X402_DEFAULT_URL).replace(/\/$/, "");
    this.apiKey = opts.apiKey;
    this.fetchImpl = opts.fetch ?? globalThis.fetch.bind(globalThis);
  }

  /** Compute the bytes32 scope identifier from a dotted string. */
  static scope(label: string): Hex {
    return keccak256(toHex(label));
  }

  /** Retrieve current price for a scope. */
  async priceOf(scope: Hex): Promise<X402Price> {
    const res = await this.fetchImpl(`${this.baseUrl}/api/price/${scope}`);
    if (!res.ok) throw new Error(`price failed: ${res.status}`);
    const raw = (await res.json()) as {
      scope: Hex; amount: string; asset: Hex; assetSymbol: string;
    };
    return {
      scope:       raw.scope,
      amount:      BigInt(raw.amount),
      asset:       raw.asset,
      assetSymbol: raw.assetSymbol
    };
  }

  /** Ask Parsec to allocate a payment intent the user's parsec-wallet can fulfil. */
  async createIntent(payer: Address, scope: Hex, chainId: number): Promise<X402PaymentIntent> {
    const res = await this.fetchImpl(`${this.baseUrl}/api/intent`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ payer: getAddress(payer), scope, chainId })
    });
    if (!res.ok) throw new Error(`intent failed: ${res.status} ${await res.text()}`);
    const raw = (await res.json()) as any;
    return {
      payer:       getAddress(raw.payer),
      scope:       raw.scope,
      amount:      BigInt(raw.amount),
      asset:       raw.asset,
      assetSymbol: raw.assetSymbol,
      facilitatorAlgoAddress: raw.facilitatorAlgoAddress,
      expires:     Number(raw.expires),
      nonce:       raw.nonce
    };
  }

  /** Poll until Parsec has observed the Algorand settlement and produced a receipt. */
  async waitForReceipt(nonce: Hex, opts: { intervalMs?: number; timeoutMs?: number } = {}):
    Promise<X402ReceiptBundle>
  {
    const intervalMs = opts.intervalMs ?? 2_000;
    const timeoutMs  = opts.timeoutMs  ?? 120_000;
    const deadline   = Date.now() + timeoutMs;

    while (Date.now() < deadline) {
      const res = await this.fetchImpl(`${this.baseUrl}/api/receipt/${nonce}`);
      if (res.status === 200) return ParsecX402Client.normalise(await res.json());
      if (res.status !== 404 && res.status !== 202) {
        throw new Error(`receipt poll failed: ${res.status}`);
      }
      await new Promise(r => setTimeout(r, intervalMs));
    }
    throw new Error("x402 receipt timeout");
  }

  /**
   * One-shot convenience: create intent → print to user for payment → wait → return receipt.
   * The UI is expected to show `intent.facilitatorAlgoAddress` / `amount` to the user and
   * call `waitForReceipt` itself; this helper exists mostly for scripts and CLIs.
   */
  async payAndResolve(payer: Address, scope: Hex, chainId: number):
    Promise<{ intent: X402PaymentIntent; bundle: X402ReceiptBundle }>
  {
    const intent = await this.createIntent(payer, scope, chainId);
    // Note: the actual Algorand tx is submitted by the user's parsec-wallet.
    const bundle = await this.waitForReceipt(intent.nonce);
    return { intent, bundle };
  }

  private headers(): HeadersInit {
    const h: HeadersInit = { "content-type": "application/json" };
    if (this.apiKey) (h as Record<string, string>).authorization = `Bearer ${this.apiKey}`;
    return h;
  }

  private static normalise(raw: unknown): X402ReceiptBundle {
    const r = raw as { receipt: any; signature: Hex };
    return {
      signature: r.signature,
      receipt: {
        facilitator: getAddress(r.receipt.facilitator),
        payer:       getAddress(r.receipt.payer),
        amount:      BigInt(r.receipt.amount),
        asset:       r.receipt.asset,
        scope:       r.receipt.scope,
        nonce:       BigInt(r.receipt.nonce),
        expiry:      BigInt(r.receipt.expiry),
        algoTxId:    r.receipt.algoTxId
      }
    };
  }
}
