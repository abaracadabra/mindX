/**
 * pay2play (p2p) frontend client — talks to the mindX backend's /agenticplace/p2p/*
 * proxy routes which forward to the pay2play C9 gateway on Arc testnet.
 *
 * Used by AgenticPlace marketplace UI for:
 *   - viewing gateway health (/health, /info)
 *   - reading ERC-8183 job state (/job/:id)
 *   - paying for ERC-8004 agent registration ($0.002)
 *   - paying for full ERC-8183 job lifecycle ($0.002)
 *
 * Payment flow (browser):
 *   1. Call createAgent or createJob without _payment.
 *   2. Backend proxies to gateway, which returns 402 + PAYMENT-REQUIRED.
 *   3. Frontend decodes the challenge, signs EIP-3009 auth with the user's
 *      browser wallet (e.g. MetaMask, WalletConnect, Privy).
 *   4. Frontend re-calls with the signed payload as _payment.
 *   5. Gateway verifies, settles via Circle Gateway batch, returns the result.
 *
 * The signing step is intentionally NOT bundled here — UI code chooses which
 * wallet adapter to use. See the eip3009Sign helper signature below.
 */

const API_BASE =
  (typeof process !== "undefined" && process.env?.MINDX_API_BASE) ||
  "/api/agenticplace";

/** -- Types matching pay2play core ----------------------------------- */

export interface P2pHealth {
  ok: boolean;
  checks: Record<string, { ok: boolean; detail?: string }>;
}

export interface P2pInfo {
  service: string;
  chain: string;
  chainId: number;
  contracts: {
    identityRegistry: string;
    reputationRegistry?: string;
    jobEscrow: string;
  };
}

export interface P2pJobInfo {
  jobId: string;
  client: `0x${string}`;
  provider: `0x${string}`;
  evaluator: `0x${string}`;
  amount: string;
  expiry: string;
  state: "OPEN" | "FUNDED" | "SUBMITTED" | "COMPLETED" | "DISPUTED" | string;
  deliverableHash?: string;
}

export interface RegisterAgentArgs {
  ownerKey: `0x${string}`;
  validatorKey?: `0x${string}`;
  metadataURI: string;
  initialScore?: number;
}

export interface RegisterAgentResult {
  agentId?: string;
  owner: `0x${string}`;
  registerTx?: string;
  feedbackTx?: string;
  reputationScore?: number;
  dryRun: boolean;
}

export interface CreateJobArgs {
  clientKey: `0x${string}`;
  providerKey: `0x${string}`;
  evaluatorKey?: `0x${string}`;
  descText: string;
  budgetUsdc: number;
  deliverable?: string;
}

export interface CreateJobResult {
  jobId: string;
  createTx: string;
  fundTx: string;
  submitTx: string;
  completeTx: string;
  finalState: string;
}

/** Browser-wallet signature provider — caller injects this. */
export type Eip3009Signer = (challengeBase64: string) => Promise<string>;

export class PaymentRequiredError extends Error {
  constructor(public readonly challengeBase64: string) {
    super("payment required");
    this.name = "PaymentRequiredError";
  }
}

/** -- Service ---------------------------------------------------------- */

class Pay2PlayService {
  constructor(private base: string = API_BASE) {}

  async health(): Promise<P2pHealth> {
    const r = await fetch(`${this.base}/p2p/health`);
    if (!r.ok) throw new Error(`p2p health failed: ${r.status}`);
    return r.json();
  }

  async info(): Promise<P2pInfo> {
    const r = await fetch(`${this.base}/p2p/info`);
    if (!r.ok) throw new Error(`p2p info failed: ${r.status}`);
    return r.json();
  }

  async getJob(jobId: string | bigint): Promise<P2pJobInfo> {
    const r = await fetch(`${this.base}/p2p/job/${String(jobId)}`);
    if (!r.ok) throw new Error(`p2p getJob failed: ${r.status}`);
    return r.json();
  }

  /**
   * Register an ERC-8004 agent. Two-step flow:
   *   1. First call without `signer` returns PaymentRequiredError carrying the challenge.
   *   2. Second call with `signer` (or a precomputed _payment) settles and runs.
   */
  async registerAgent(
    args: RegisterAgentArgs,
    signer?: Eip3009Signer,
  ): Promise<RegisterAgentResult> {
    return this._paid("/p2p/agent/register", args, signer);
  }

  async createJob(
    args: CreateJobArgs,
    signer?: Eip3009Signer,
  ): Promise<CreateJobResult> {
    return this._paid("/p2p/job/create", args, signer);
  }

  // ------------------------------------------------------------------- //

  private async _paid<T>(
    path: string,
    body: Record<string, unknown>,
    signer?: Eip3009Signer,
    precomputedPayment?: string,
  ): Promise<T> {
    const payload = precomputedPayment ? { ...body, _payment: precomputedPayment } : body;
    const r = await fetch(`${this.base}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (r.status === 402) {
      const detail = (await r.json().catch(() => ({}))) as {
        detail?: { ["PAYMENT-REQUIRED"]?: string };
      };
      const challenge =
        detail?.detail?.["PAYMENT-REQUIRED"] ??
        r.headers.get("PAYMENT-REQUIRED") ??
        r.headers.get("payment-required") ??
        "";
      if (!challenge) throw new Error("402 returned but no PAYMENT-REQUIRED challenge");

      if (!signer) throw new PaymentRequiredError(challenge);

      // Sign and retry once.
      const payment = await signer(challenge);
      return this._paid<T>(path, body, undefined, payment);
    }

    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`p2p ${path} failed: ${r.status} ${txt}`);
    }
    return r.json() as Promise<T>;
  }
}

export const p2p = new Pay2PlayService();
export default p2p;
