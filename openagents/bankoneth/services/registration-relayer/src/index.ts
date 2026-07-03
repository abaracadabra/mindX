/**
 * BankonSubnameRegistrar — registration relayer (x402 → EIP-712 voucher).
 *
 * The missing L1 service piece for bankon.eth subname-as-a-service. The
 * on-chain `register()` is gated by a voucher signed by a key holding
 * GATEWAY_SIGNER_ROLE, binding (label, owner, expiry, paymentReceiptHash,
 * deadline). This relayer:
 *   1. GET  /quote?label=&years=   → price (USD, from BankonPriceOracle)
 *   2. POST /register              → x402-gated; on paid, returns the voucher
 *   3. POST /renew                 → same, Renewal typehash
 *   4. GET  /health
 *
 * The voucher matches the contract EXACTLY:
 *   domain  = EIP712("BankonSubnameRegistrar","1"), chainId, verifyingContract=registrar
 *   type    = Registration(string label,address owner,uint64 expiry,
 *                          bytes32 paymentReceiptHash,uint256 deadline)
 * The contract does `hasRole(GATEWAY_SIGNER_ROLE, digest.recover(gatewaySig))`,
 * so the relayer key must be granted GATEWAY_SIGNER_ROLE on the registrar
 * (script/GrantOwnerRoles.s.sol or the deploy).
 *
 * Single-file Bun + Hono + viem, mirroring services/offchain-gateway. The
 * private key stays in env / a vault mount, never on the wire.
 *
 * (c) 2026 BANKON — Apache-2.0.
 */
import { Hono } from "hono";
import { cors } from "hono/cors";
import {
  createPublicClient,
  http,
  keccak256,
  toHex,
  encodePacked,
  type Address,
  type Hex,
} from "viem";
import { privateKeyToAccount } from "viem/accounts";

// ── config ───────────────────────────────────────────────────────────
const PORT        = Number(process.env.RELAYER_PORT ?? 8890);
const CHAIN_ID    = Number(process.env.CHAIN_ID ?? 1);
const REGISTRAR   = (process.env.REGISTRAR_ADDR ?? "") as Address;   // verifyingContract
const SIGNER_PK   = (process.env.GATEWAY_SIGNER_PK ?? "") as Hex;     // holds GATEWAY_SIGNER_ROLE
const RPC_URL     = process.env.RPC_URL ?? "";
const PRICE_ORACLE = (process.env.PRICE_ORACLE_ADDR ?? "") as Address;
const VOUCHER_TTL = Number(process.env.VOUCHER_TTL ?? 900);          // 15 min
const DEFAULT_YEARS_SECONDS = 365n * 24n * 60n * 60n;
// x402: how a payment receipt is accepted. "facilitator" verifies against the
// x402 facilitator; "trusted-header" accepts a pre-settled receipt id from a
// trusted upstream (the x402 middleware / BankonX402Attestor flow). Never
// "none" in production.
const X402_MODE   = process.env.X402_MODE ?? "trusted-header";
const X402_FACILITATOR = process.env.X402_FACILITATOR ?? "https://facilitator.goplausible.xyz";
const X402_ASSET  = process.env.X402_ASSET ?? "31566704";           // USDC ASA (Algorand)
const X402_PAYTO  = process.env.X402_PAYTO ?? "";                   // BANKON treasury on the rail

if (!REGISTRAR || !SIGNER_PK) {
  console.error("Missing required env: REGISTRAR_ADDR, GATEWAY_SIGNER_PK.");
  process.exit(1);
}

const signer = privateKeyToAccount(SIGNER_PK);
const pub = RPC_URL ? createPublicClient({ transport: http(RPC_URL) }) : null;

// ── EIP-712 (must match BankonSubnameRegistrar exactly) ──────────────
const DOMAIN = {
  name: "BankonSubnameRegistrar",
  version: "1",
  chainId: CHAIN_ID,
  verifyingContract: REGISTRAR,
} as const;
const REGISTRATION_TYPES = {
  Registration: [
    { name: "label", type: "string" },
    { name: "owner", type: "address" },
    { name: "expiry", type: "uint64" },
    { name: "paymentReceiptHash", type: "bytes32" },
    { name: "deadline", type: "uint256" },
  ],
} as const;
const RENEWAL_TYPES = {
  Renewal: [
    { name: "label", type: "string" },
    { name: "newExpiry", type: "uint64" },
    { name: "paymentReceiptHash", type: "bytes32" },
    { name: "deadline", type: "uint256" },
  ],
} as const;

// ── pricing ──────────────────────────────────────────────────────────
// length-tiered USD/year, matching BankonPriceOracle (3=$320,4=$80,5=$5,6=$3,7+=$1)
const TIER_USD: Record<number, number> = { 3: 320, 4: 80, 5: 5, 6: 3 };
function tierUsd(label: string, years: number): number {
  const n = [...label].length;
  const per = n <= 2 ? 320 : (TIER_USD[n] ?? 1);
  return per * Math.max(1, years);
}
const ORACLE_ABI = [{
  type: "function", name: "priceUSD", stateMutability: "view",
  inputs: [{ name: "label", type: "string" }, { name: "years_", type: "uint256" }],
  outputs: [{ name: "", type: "uint256" }],
}] as const;
async function priceUsd6(label: string, years: number): Promise<bigint> {
  if (pub && PRICE_ORACLE) {
    try {
      return await pub.readContract({ address: PRICE_ORACLE, abi: ORACLE_ABI, functionName: "priceUSD", args: [label, BigInt(years)] }) as bigint;
    } catch { /* fall through to tiers */ }
  }
  return BigInt(Math.round(tierUsd(label, years) * 1_000_000)); // 6-dec USD
}

// ── label validation (ENS rules) ─────────────────────────────────────
function labelError(label: string): string | null {
  if (!label) return "label required";
  if (!/^[a-z0-9-]{1,63}$/.test(label)) return "lowercase a-z 0-9 hyphen, 1-63";
  if (label.startsWith("-") || label.endsWith("-")) return "no leading/trailing hyphen";
  return null;
}

// ── payment: verify an x402 receipt → a bytes32 paymentReceiptHash ───
// Replay is enforced on-chain (usedReceipts); we also refuse to re-issue for
// a receipt we've already vouched, to avoid handing out two vouchers.
const issued = new Set<string>();
async function verifyPayment(req: { receiptId?: string; header?: string | null }): Promise<{ ok: boolean; hash?: Hex; reason?: string }> {
  const receiptId = req.receiptId || req.header || "";
  if (!receiptId) return { ok: false, reason: "no payment receipt" };
  if (X402_MODE === "facilitator") {
    // Verify the receipt against the x402 facilitator (settled + unspent).
    try {
      const r = await fetch(`${X402_FACILITATOR}/verify`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ receipt: receiptId, asset: X402_ASSET, payTo: X402_PAYTO }),
      });
      if (!r.ok) return { ok: false, reason: `facilitator ${r.status}` };
      const j: any = await r.json();
      if (!j.settled) return { ok: false, reason: "not settled" };
    } catch (e: any) { return { ok: false, reason: `facilitator error: ${e.message}` }; }
  } else if (X402_MODE !== "trusted-header") {
    return { ok: false, reason: `X402_MODE=${X402_MODE} not allowed` };
  }
  const hash = keccak256(encodePacked(["string"], [receiptId]));
  if (issued.has(hash)) return { ok: false, reason: "receipt already vouched" };
  return { ok: true, hash };
}

// ── x402 payment requirements (the 402 challenge body) ───────────────
function paymentRequired(usd6: bigint) {
  return {
    x402Version: 1,
    accepts: [{
      scheme: "exact",
      network: `algorand:mainnet`,
      asset: X402_ASSET,
      payTo: X402_PAYTO,
      maxAmountRequired: usd6.toString(),         // 6-dec USDC
      resource: "bankon.eth subname registration",
      description: "Pay to receive a registration voucher, then submit register() on L1.",
      facilitator: X402_FACILITATOR,
    }],
  };
}

// ── app ──────────────────────────────────────────────────────────────
const app = new Hono();
app.use("*", cors());

app.get("/health", (c) => c.json({
  ok: true, service: "bankon-registration-relayer", chainId: CHAIN_ID,
  registrar: REGISTRAR, gatewaySigner: signer.address, x402Mode: X402_MODE,
}));

app.get("/quote", async (c) => {
  const label = (c.req.query("label") ?? "").toLowerCase();
  const years = Math.max(1, Number(c.req.query("years") ?? 1));
  const err = labelError(label);
  if (err) return c.json({ error: err }, 400);
  const usd6 = await priceUsd6(label, years);
  return c.json({ label, years, priceUsd6: usd6.toString(), priceUsd: Number(usd6) / 1e6, payTo: X402_PAYTO, asset: X402_ASSET });
});

async function issueVoucher(c: any, kind: "register" | "renew") {
  const body = await c.req.json().catch(() => ({}));
  const label = (body.label ?? "").toLowerCase();
  const years = Math.max(1, Number(body.years ?? 1));
  const err = labelError(label);
  if (err) return c.json({ error: err }, 400);
  const owner = body.owner as Address;
  if (kind === "register" && !/^0x[0-9a-fA-F]{40}$/.test(owner ?? "")) return c.json({ error: "owner address required" }, 400);

  // ── x402 gate ──
  const pay = await verifyPayment({ receiptId: body.paymentReceiptId, header: c.req.header("X-PAYMENT") });
  if (!pay.ok) {
    const usd6 = await priceUsd6(label, years);
    return c.json(paymentRequired(usd6), 402);
  }

  const now = Math.floor(Date.now() / 1000);
  const deadline = BigInt(now + VOUCHER_TTL);
  const expiry = BigInt(now) + DEFAULT_YEARS_SECONDS * BigInt(years);
  const paymentReceiptHash = pay.hash!;

  let signature: Hex;
  if (kind === "register") {
    signature = await signer.signTypedData({
      domain: DOMAIN, types: REGISTRATION_TYPES, primaryType: "Registration",
      message: { label, owner, expiry, paymentReceiptHash, deadline },
    });
  } else {
    signature = await signer.signTypedData({
      domain: DOMAIN, types: RENEWAL_TYPES, primaryType: "Renewal",
      message: { label, newExpiry: expiry, paymentReceiptHash, deadline },
    });
  }
  issued.add(paymentReceiptHash);

  return c.json({
    kind, label, owner: kind === "register" ? owner : undefined,
    expiry: expiry.toString(),
    paymentReceiptHash, deadline: deadline.toString(),
    gatewaySig: signature, gatewaySigner: signer.address,
    registrar: REGISTRAR, chainId: CHAIN_ID,
    // the exact call the client submits on L1:
    call: kind === "register"
      ? "register(label, owner, expiry, paymentReceiptHash, deadline, gatewaySig, meta)"
      : "renew(label, newExpiry, paymentReceiptHash, deadline, gatewaySig)",
  });
}

app.post("/register", (c) => issueVoucher(c, "register"));
app.post("/renew", (c) => issueVoucher(c, "renew"));

console.log(`bankon registration-relayer :${PORT} · chain ${CHAIN_ID} · registrar ${REGISTRAR} · gateway signer ${signer.address} · x402 ${X402_MODE}`);
export default { port: PORT, fetch: app.fetch };

// Exported for tests (voucher construction is the load-bearing part).
export const _internal = { DOMAIN, REGISTRATION_TYPES, RENEWAL_TYPES, signer, priceUsd6, labelError, verifyPayment };
