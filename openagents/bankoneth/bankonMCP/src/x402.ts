// SPDX-License-Identifier: Apache-2.0
//
// x402.ts — the x402 PAYER for the MCP proxy. When a remote MCP tool returns HTTP 402, this builds
// an EIP-3009 USDC `transferWithAuthorization` and the `X-PAYMENT` header so the request can be
// retried and settled. Open x402 standard (Coinbase); USDC on Base / Arc / any registered rail.
import { ethers } from "ethers";

export interface X402Offer {
  scheme: string; network: string; maxAmountRequired: string;
  payTo: string; asset: string; resource?: string; maxTimeoutSeconds?: number;
  extra?: { name?: string; version?: string };
}
export interface X402Challenge { x402Version?: number; accepts: X402Offer[] }

const NETWORK_CHAIN_ID: Record<string, number> = {
  base: 8453, "base-sepolia": 84532, arc: 5042002, optimism: 10, ethereum: 1, arbitrum: 42161, polygon: 137,
};

/** Build the X-PAYMENT header value for an x402 offer, signing an EIP-3009 USDC authorization. */
export async function buildPayment(wallet: ethers.Wallet, challenge: X402Challenge, offer: X402Offer): Promise<string> {
  const chainId = NETWORK_CHAIN_ID[offer.network];
  if (!chainId) throw new Error(`unsupported x402 network: ${offer.network}`);
  const now = Math.floor(Date.now() / 1000);
  const authorization = {
    from: wallet.address, to: offer.payTo, value: offer.maxAmountRequired,
    validAfter: "0", validBefore: String(now + (offer.maxTimeoutSeconds || 600)),
    nonce: ethers.hexlify(ethers.randomBytes(32)),
  };
  const domain = { name: offer.extra?.name || "USD Coin", version: offer.extra?.version || "2", chainId, verifyingContract: offer.asset };
  const types = { TransferWithAuthorization: [
    { name: "from", type: "address" }, { name: "to", type: "address" }, { name: "value", type: "uint256" },
    { name: "validAfter", type: "uint256" }, { name: "validBefore", type: "uint256" }, { name: "nonce", type: "bytes32" },
  ] };
  const signature = await wallet.signTypedData(domain, types, authorization);
  const payload = { x402Version: challenge.x402Version || 1, scheme: "exact", network: offer.network, payload: { signature, authorization } };
  return Buffer.from(JSON.stringify(payload)).toString("base64");
}

/** Fetch with automatic x402 payment + retry. `pickOffer` chooses a rail (see rails.ts). */
export async function fetchWithX402(
  url: string, init: RequestInit, wallet: ethers.Wallet,
  pickOffer: (offers: X402Offer[]) => X402Offer,
): Promise<Response> {
  const res = await fetch(url, init);
  if (res.status !== 402) return res;
  const challenge = (await res.json()) as X402Challenge;
  const offer = pickOffer(challenge.accepts || []);
  const xPayment = await buildPayment(wallet, challenge, offer);
  const headers = new Headers(init.headers); headers.set("X-PAYMENT", xPayment);
  return fetch(url, { ...init, headers });
}
