/**
 * x402-AVM adapter for AgenticPlace — Algorand rail for HTTP 402 micropayments.
 *
 * Sibling to `p2p.ts` (which is EVM-only). This file wraps the published
 * `@x402-avm/*` packages (ISC, v^2.6.1, 2026-05-02) so AgenticPlace clients
 * can pay 402 challenges that advertise the AVM rail, and so paid Hono routes
 * inside AgenticPlace can mint AVM challenges.
 *
 * Why a separate file vs. extending p2p.ts:
 *   - p2p.ts uses `0x${string}` addresses + EIP-3009 typed-data. AVM
 *     addresses are 58-char base32 and signing is Ed25519 over an
 *     AssetTransferTxn. Conflating them muddles types.
 *   - When mindX runs triple-rail (Base USDC + Tempo MPP + Algorand ASA),
 *     a future `index.ts` façade can compose both adapters; for now they
 *     stay isolated.
 *
 * See docs/X402.md for the wire format and operator runbook.
 */

import { wrapFetchWithPayment } from "@x402-avm/fetch";
import {
  registerExactAvmScheme,
  toClientAvmSigner,
  seedFromMnemonic,
} from "@x402-avm/avm";

// `@x402-avm/core` types — re-export so callers don't import the package twice.
export type {
  PaymentRequirements as X402AvmAccepts,
  PaymentPayload as X402AvmPayment,
  // The 402 envelope on the wire.
  PaymentRequirementsResponse as X402AvmChallenge,
} from "@x402-avm/core";

const FACILITATOR_URL_DEFAULT = "https://mindx.pythai.net:4022";

const API_BASE =
  (typeof process !== "undefined" && process.env?.MINDX_API_BASE) ||
  "/api/agenticplace";

/* ------------------------------------------------------------------ *
 * Errors
 * ------------------------------------------------------------------ */

export class X402AvmError extends Error {
  constructor(message: string, public readonly cause?: unknown) {
    super(message);
    this.name = "X402AvmError";
  }
}

export class X402AvmPaymentRequiredError extends Error {
  constructor(public readonly accepts: unknown[]) {
    super("payment required (AVM rail)");
    this.name = "X402AvmPaymentRequiredError";
  }
}

/* ------------------------------------------------------------------ *
 * Service
 * ------------------------------------------------------------------ */

export interface X402AvmServiceOptions {
  /** 25-word Algorand mnemonic for the buyer wallet (Machine custody, vault). */
  mnemonic: string;
  /** Facilitator URL — defaults to GoPlausible hosted. */
  facilitatorUrl?: string;
  /** Network label per x402.org — defaults to algorand-testnet. */
  network?: string;
}

export class X402AvmService {
  private readonly facilitatorUrl: string;
  private readonly network: string;
  private readonly wrappedFetchPromise: Promise<typeof fetch>;

  constructor(opts: X402AvmServiceOptions) {
    this.facilitatorUrl = opts.facilitatorUrl ?? FACILITATOR_URL_DEFAULT;
    this.network = opts.network ?? "algorand-testnet";

    this.wrappedFetchPromise = (async () => {
      const seed = await seedFromMnemonic(opts.mnemonic);
      const signer = toClientAvmSigner(seed);
      const wrapped = wrapFetchWithPayment(globalThis.fetch.bind(globalThis), {
        signer,
        // Register the AVM "exact" scheme so the wrapper knows how to fulfill
        // a 402 with `scheme: "exact", network: "algorand-*"`.
        registerSchemes: (client) => registerExactAvmScheme(client, { signer }),
        facilitatorUrl: this.facilitatorUrl,
        preferredNetwork: this.network,
      });
      return wrapped as typeof fetch;
    })();
  }

  /** A fetch decorated with x402-AVM auto-payment. Use exactly like global fetch. */
  async wrappedFetch(): Promise<typeof fetch> {
    return this.wrappedFetchPromise;
  }

  /** Convenience — read the configured facilitator's /info. */
  async facilitatorInfo(): Promise<unknown> {
    const r = await fetch(`${this.facilitatorUrl.replace(/\/$/, "")}/info`);
    if (!r.ok) throw new X402AvmError(`facilitator /info ${r.status}`);
    return r.json();
  }

  /** Convenience — proxied via the mindX backend (bypasses CORS). */
  async backendFacilitatorInfo(): Promise<unknown> {
    const r = await fetch(`${API_BASE}/p2p/x402/facilitator-info`);
    if (!r.ok) throw new X402AvmError(`backend /p2p/x402/facilitator-info ${r.status}`);
    return r.json();
  }
}

/* ------------------------------------------------------------------ *
 * Server-side (Hono) — re-export with a thin factory.
 * ------------------------------------------------------------------ */

/**
 * Mount AVM-paid Hono routes. Importer must `npm install @x402-avm/hono`.
 *
 * Usage:
 *   import { paymentMiddleware } from "@x402-avm/hono";
 *   app.use("/paid/*", paymentMiddleware({
 *     payTo: "<58-char base32>",
 *     network: "algorand-testnet",
 *     facilitator: "https://mindx.pythai.net:4022",
 *     // … per @x402-avm/hono README
 *   }));
 *
 * This file intentionally does not pre-bind options — the caller knows
 * pricing per route. We just re-export the wire types and the AVM scheme
 * registration helper for consistency with the client side.
 */
export { registerExactAvmScheme } from "@x402-avm/avm";
