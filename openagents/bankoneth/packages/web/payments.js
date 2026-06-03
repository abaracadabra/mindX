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
//
// REAL on-chain rails (no kit key, client-side): autoConvert() routes any token →
// settlement through bankon_autoconvert (Uniswap V3) charging the golden φ fee →
// RAKE; bridgeCollect() takes any asset on any chain through bridge_collect
// (LI.FI/GLMR) φ fee → RAKE. Both need the cp2048 treasury addresses (deploy.html).
import { CHAINS, SETTLEMENT_CHAIN_ID, usdcFor, ERC20_ABI } from "./chains.js";

// Minimal ABIs for the cp2048 collection rails (match contracts/cp2048/).
const AUTOCONVERT_ABI = [
  { type: "function", name: "convert", stateMutability: "nonpayable",
    inputs: [{ name: "tokenIn", type: "address" }, { name: "amountIn", type: "uint256" }, { name: "tokenOut", type: "address" }, { name: "poolFee", type: "uint24" }, { name: "minOut", type: "uint256" }, { name: "recipient", type: "address" }],
    outputs: [{ name: "amountOut", type: "uint256" }] },
];
const BRIDGE_COLLECT_ABI = [
  { type: "function", name: "collect_for_bridge", stateMutability: "nonpayable",
    inputs: [{ name: "asset", type: "address" }, { name: "amount", type: "uint256" }, { name: "dstChainId", type: "uint256" }, { name: "resource", type: "bytes32" }, { name: "recipient", type: "address" }],
    outputs: [{ name: "forwarded", type: "uint256" }] },
];

const BANKON_NODE = "0x79c178642317fc2d61d186f3b412440f06590d8314f126362d6a88929a6cbe1a";

// X402Receipt tuple, per contracts/BankonX402Attestor.sol.
const X402_RECEIPT_TUPLE =
  "tuple(bytes32 receiptHash,address claimant,uint256 usd6,uint64 nonce,uint64 expiresAt,bytes signature)";

export const RAILS = [
  { id: "eth", label: "ETH (direct)", always: true },
  { id: "x402", label: "USDC via x402", always: false },
  { id: "autoconvert", label: "Any token → settlement (φ fee → RAKE)", adapter: true, onchain: true },
  { id: "bridge", label: "Any chain → settlement (φ fee → RAKE)", adapter: true, onchain: true },
  { id: "swap", label: "Any token → USDC (Circle Kit)", adapter: true },
  { id: "arc", label: "Bridge from ARC / L2 (CCTP)", adapter: true },
];

/** REAL rail — route any ERC-20 → settlement token via bankon_autoconvert (Uniswap V3),
 *  charging the golden φ fee → RAKE → bankon.eth. Approves then converts. Returns the tx. */
export async function autoConvert({ signer, autoconvertAddr, tokenIn, amountIn, tokenOut, poolFee = 3000, minOut = 0n, recipient, ethers }) {
  const erc20 = new ethers.Contract(tokenIn, ERC20_ABI, signer);
  const a = await erc20.approve(autoconvertAddr, amountIn);
  await a.wait();
  const ac = new ethers.Contract(autoconvertAddr, AUTOCONVERT_ABI, signer);
  return ac.convert(tokenIn, amountIn, tokenOut, poolFee, minOut, recipient);
}

/** REAL rail — take any asset on this chain through bridge_collect (LI.FI/GLMR anchor),
 *  golden φ fee → RAKE, emit the bridge intent for the relayer. Approves then collects. */
export async function bridgeCollect({ signer, bridgeAddr, asset, amount, dstChainId, resource, recipient, ethers }) {
  const erc20 = new ethers.Contract(asset, ERC20_ABI, signer);
  const a = await erc20.approve(bridgeAddr, amount);
  await a.wait();
  const bc = new ethers.Contract(bridgeAddr, BRIDGE_COLLECT_ABI, signer);
  const res = typeof resource === "string" && !resource.startsWith("0x")
    ? ethers.encodeBytes32String(resource.slice(0, 31)) : resource;
  return bc.collect_for_bridge(asset, amount, BigInt(dstChainId), res, recipient);
}

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
  if (rail === "autoconvert" || rail === "bridge") {
    throw new Error(
      `${rail} is an on-chain rail — call ${rail === "autoconvert" ? "autoConvert()" : "bridgeCollect()"} ` +
      "with the deployed cp2048 address (deploy.html), then settle the resulting USDC via x402."
    );
  }
  if (rail === "swap") {
    throw new Error(
      "Swap rail (Circle Kit option): swap your token → USDC via Circle App/Swap Kit (kit key, swap-tokens " +
      "skill), then settle via x402. For a keyless on-chain path use the `autoconvert` rail / autoConvert()."
    );
  }
  if (rail === "arc") {
    throw new Error(
      "ARC rail (CCTP option): bridge USDC from ARC (chain 5042002, CCTP domain 26) or an L2 via CCTP " +
      "(bridge-stablecoin skill), then settle via x402. For a keyless on-chain path use the `bridge` rail."
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
