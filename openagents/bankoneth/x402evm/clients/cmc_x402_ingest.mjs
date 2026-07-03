// SPDX-License-Identifier: Apache-2.0
//
// cmc_x402_ingest.mjs — the x402 PAYER for ingesting CoinMarketCap (or any x402-gated) data on the
// EVM/Base/Arc side. Implements the open x402 flow (Coinbase): GET → 402 challenge → sign an
// EIP-3009 USDC transferWithAuthorization → resend with the X-PAYMENT header → ingest the JSON.
// No CMC API key needed for the x402 path (pay-per-call in USDC). Key stays server-side for the
// keyed `cmc` CLI path (see cmc_cli.mjs).
//
// Usage:  X402_PK=0x… node cmc_x402_ingest.mjs "https://pro-api.coinmarketcap.com/x402/.../quotes?symbol=ETH"
// Confirm the exact CMC x402 endpoint + network against:
//   https://pro.coinmarketcap.com/api/documentation/ai-agent-hub/x402
import { ethers } from "../../packages/web/vendor/ethers.min.js";

const PK = process.env.X402_PK || "";
const MAX_USDC = BigInt(process.env.X402_MAX_USDC || "1000000"); // per-call cap (default $1, 6dp)
// network name (x402) → { chainId } for the EIP-3009 domain
const NETWORKS = { "base": 8453, "base-sepolia": 84532, "arc": 5042002, "optimism": 10, "ethereum": 1, "arbitrum": 42161, "polygon": 137 };

const b64 = (obj) => Buffer.from(JSON.stringify(obj)).toString("base64");

// Sign an EIP-3009 transferWithAuthorization for `asset` (USDC) → payTo.
async function signAuthorization({ wallet, asset, chainId, name, version, to, value, validForSec }) {
  const now = Math.floor(Date.now() / 1000);
  const authorization = {
    from: wallet.address, to, value: value.toString(),
    validAfter: "0", validBefore: String(now + (validForSec || 600)),
    nonce: ethers.hexlify(ethers.randomBytes(32)),
  };
  const domain = { name: name || "USD Coin", version: version || "2", chainId, verifyingContract: asset };
  const types = { TransferWithAuthorization: [
    { name: "from", type: "address" }, { name: "to", type: "address" }, { name: "value", type: "uint256" },
    { name: "validAfter", type: "uint256" }, { name: "validBefore", type: "uint256" }, { name: "nonce", type: "bytes32" },
  ] };
  const signature = await wallet.signTypedData(domain, types, authorization);
  return { signature, authorization };
}

// Fetch an x402 resource, paying if challenged. Returns the parsed JSON body.
export async function ingest(url, { pk = PK, maxUsdc = MAX_USDC } = {}) {
  if (!pk) throw new Error("X402_PK (a funded USDC wallet key) required for the x402 payer");
  const wallet = new ethers.Wallet(pk);

  let res = await fetch(url, { headers: { accept: "application/json" } });
  if (res.status !== 402) {
    if (!res.ok) throw new Error(`unexpected ${res.status}`);
    return res.json();                                  // not gated — just return
  }

  const challenge = await res.json();                   // { x402Version, accepts:[{scheme,network,maxAmountRequired,payTo,asset,extra,...}] }
  const offer = (challenge.accepts || []).find((a) => a.scheme === "exact") || challenge.accepts?.[0];
  if (!offer) throw new Error("no payable x402 offer in 402 challenge");
  const chainId = NETWORKS[offer.network];
  if (!chainId) throw new Error(`unsupported x402 network: ${offer.network}`);
  const value = BigInt(offer.maxAmountRequired);
  if (value > maxUsdc) throw new Error(`offer ${value} exceeds cap ${maxUsdc} — refusing to pay`);

  const { signature, authorization } = await signAuthorization({
    wallet, asset: offer.asset, chainId, name: offer.extra?.name, version: offer.extra?.version,
    to: offer.payTo, value, validForSec: offer.maxTimeoutSeconds,
  });
  const xPayment = b64({ x402Version: challenge.x402Version || 1, scheme: "exact", network: offer.network, payload: { signature, authorization } });

  res = await fetch(url, { headers: { accept: "application/json", "X-PAYMENT": xPayment } });
  if (!res.ok) throw new Error(`x402 retry failed ${res.status}: ${(await res.text()).slice(0, 160)}`);
  return res.json();
}

// CLI entrypoint
if (import.meta.url === `file://${process.argv[1]}`) {
  const url = process.argv[2];
  if (!url) { console.error("usage: X402_PK=0x… node cmc_x402_ingest.mjs <x402-url>"); process.exit(1); }
  ingest(url).then((d) => console.log(JSON.stringify(d, null, 2))).catch((e) => { console.error("x402 ingest failed:", e.message); process.exit(1); });
}
