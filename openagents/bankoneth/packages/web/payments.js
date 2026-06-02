// SPDX-License-Identifier: Apache-2.0
//
// payments.js — "accept any denomination, convert it" orchestration for buying
// *.bankon.eth. Normalizes any input into the `payment` bytes DomainHosting.issue
// expects (rail 0x00 = ETH msg.value, rail 0x02 = x402 receipt). The conversion
// adapters (swap any token → USDC; bridge across chains incl. ARC via CCTP) feed
// the x402 rail. On-chain price/fee is admin-set; this layer only routes funds.
//
// Adapters:
//   eth   — pay ETH directly (msg.value). Always available.
//   x402  — settle USDC off-chain; the facilitator signs an X402Receipt the
//           registrar consumes (rail 0x02). Backend: POST /x402/settle.
//   swap  — swap any ERC-20 → USDC via Circle App/Swap Kit, then x402. (adapter)
//   arc   — bridge USDC from ARC/Base/… → settlement chain via CCTP, then x402. (adapter)
import { CHAINS, SETTLEMENT_CHAIN_ID, usdcFor } from "./chains.js";

const BANKON_NODE = "0x79c178642317fc2d61d186f3b412440f06590d8314f126362d6a88929a6cbe1a";

// X402Receipt tuple, per contracts/BankonX402Attestor.sol.
const X402_RECEIPT_TUPLE =
  "tuple(bytes32 receiptHash,address claimant,uint256 usd6,uint64 nonce,uint64 expiresAt,bytes signature)";

export const RAILS = [
  { id: "eth", label: "ETH (direct)", always: true },
  { id: "x402", label: "USDC via x402", always: false },
  { id: "swap", label: "Any token → USDC", adapter: true },
  { id: "arc", label: "Bridge from ARC / L2 (CCTP)", adapter: true },
];

/** Read the admin-set hosting price for bankon.eth (ETH wei + USD6). */
export async function quoteFor({ provider, address, abi, ethers }) {
  const c = new ethers.Contract(address, abi, provider);
  const parent = await c.parentOf(BANKON_NODE);
  return {
    active: parent.active ?? parent[6],
    priceEthWei: parent.priceEthWei ?? parent[2],
    pricePerLabel6: parent.pricePerLabel6 ?? parent[1],
  };
}

/** Produce { value, paymentBytes } for DomainHosting.issue given a rail. */
export async function preparePayment({ rail, label, payer, quote, ethers, facilitatorUrl = "/x402/settle" }) {
  if (rail === "eth") {
    return { value: quote.priceEthWei, paymentBytes: "0x" };
  }
  if (rail === "x402") {
    const receipt = await requestX402Receipt({ payer, usd6: quote.pricePerLabel6, label, facilitatorUrl });
    const coder = ethers.AbiCoder.defaultAbiCoder();
    const encoded = coder.encode([X402_RECEIPT_TUPLE], [receipt]);
    // rail prefix 0x02 || abi.encode(receipt)
    return { value: 0n, paymentBytes: "0x02" + encoded.slice(2) };
  }
  if (rail === "swap") {
    throw new Error(
      "Swap rail: swap your token → USDC via Circle App/Swap Kit, then settle via x402. " +
      "Wire @circle-fin/app-kit (swap-tokens skill) + a kit key, then route the USDC to /x402/settle."
    );
  }
  if (rail === "arc") {
    throw new Error(
      "ARC rail: bridge USDC from ARC (chain 5042002, CCTP domain 26) or an L2 to the settlement " +
      "chain via CCTP (bridge-stablecoin skill), then settle via x402. Fund from faucet.circle.com on testnet."
    );
  }
  throw new Error("unknown rail: " + rail);
}

/** Ask the gate's facilitator to sign an X402Receipt for a settled USDC payment.
 *  In production the facilitator verifies the on-chain/x402 settlement first. */
async function requestX402Receipt({ payer, usd6, label, facilitatorUrl }) {
  const r = await fetch(facilitatorUrl, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ payer, usd6: usd6.toString(), resource: `${label}.bankon.eth`, chainId: SETTLEMENT_CHAIN_ID }),
  });
  if (!r.ok) throw new Error("facilitator: " + (await r.text()).slice(0, 140));
  const j = await r.json();
  // {receiptHash, claimant, usd6, nonce, expiresAt, signature}
  return [j.receiptHash, j.claimant, BigInt(j.usd6), BigInt(j.nonce), BigInt(j.expiresAt), j.signature];
}

export { CHAINS, usdcFor };
