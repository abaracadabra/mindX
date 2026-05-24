// SPDX-License-Identifier: Apache-2.0
//
// @bankoneth/core — viem v2 typed client.
//
// Three issuance flows:
//   - claim()    Flow A: alice.bankon.eth
//   - purchase() Flow B: newdomain.eth via the canonical ENS controller wrapper
//   - host()     Flow C: enroll an external .eth and issue subnames under it
//
// Tri-rail payment:
//   - ETH    msg.value
//   - USDC   EIP-2612 permit (off-path; this client emits the permit, caller signs)
//   - x402   Algorand atomic group via @perawallet/connect; receipt arrives EIP-712-signed

import {
  type Address,
  type Hex,
  type WalletClient,
  type PublicClient,
  encodeFunctionData,
  namehash,
  labelhash,
  keccak256,
  toBytes,
  toHex,
  parseEther,
} from "viem";

import {
  BANKON_SUBNAME_REGISTRAR_ABI,
  BANKON_ETH_REGISTRAR_ABI,
  BANKON_DOMAIN_HOSTING_ABI,
  BANKON_PRICE_ORACLE_ABI,
  BANKON_SUBNAME_RESOLVER_ABI,
  BANKON_INFT_ADAPTER_ABI,
  BANKON_X402_ATTESTOR_ABI,
} from "./abis";

export interface BankonethAddresses {
  subnameRegistrar: Address;
  ethRegistrar:     Address;
  domainHosting:    Address;
  resolver:         Address;
  inftAdapter:      Address;
  x402Attestor:     Address;
  agenticPlaceHook: Address;
  priceOracle:      Address;
  paymentRouter:    Address;
}

export type PaymentRail = "eth" | "usdc-permit" | "x402-avm";

export interface ClaimParams {
  label: string;          // e.g. "alice" — without ".bankon.eth"
  owner: Address;
  durationYears: number;
  payment: PaymentRail;
  inftModeA: boolean;     // wrap as unified ERC-7857 on 0G + derive TBA
  listOnAgenticPlace: boolean;
  metadataURI?: string;
}

export interface PurchaseParams {
  label: string;          // e.g. "newdomain" — without ".eth"
  owner: Address;
  durationYears: number;
  resolver: Address;
  reverseRecord: boolean;
  ownerControlledFuses: number;
  payment: PaymentRail;
}

export interface HostIssueParams {
  parentNode: Hex;        // bytes32 namehash of e.g. "yourdomain.eth"
  label: string;          // e.g. "alice"
  owner: Address;
  payment: PaymentRail;
}

export interface X402Receipt {
  receiptHash: Hex;
  claimant: Address;
  usd6: bigint;
  nonce: bigint;
  expiresAt: bigint;
  signature: Hex;
}

export class BankonethClient {
  constructor(
    public readonly publicClient:  PublicClient,
    public readonly walletClient:  WalletClient | undefined,
    public readonly addresses:     BankonethAddresses,
    public readonly bankonEthNode: Hex,
  ) {}

  // ── Quotes ────────────────────────────────────────────────────────

  async quoteSubname(label: string, durationYears: number): Promise<{ usd6: bigint }> {
    const usd6 = await this.publicClient.readContract({
      address: this.addresses.priceOracle,
      abi:     BANKON_PRICE_ORACLE_ABI,
      functionName: "priceUSD",
      args:    [label, BigInt(durationYears)],
    }) as bigint;
    return { usd6 };
  }

  async quoteEthPurchase(
    label: string,
    durationYears: number,
  ): Promise<{ wei: bigint; usd6: bigint }> {
    const [wei_, usd6] = await this.publicClient.readContract({
      address: this.addresses.ethRegistrar,
      abi:     BANKON_ETH_REGISTRAR_ABI,
      functionName: "quote",
      args:    [label, BigInt(durationYears)],
    }) as [bigint, bigint];
    return { wei: wei_, usd6 };
  }

  // ── Flow A: claim *.bankon.eth ────────────────────────────────────

  async claim(p: ClaimParams, x402?: X402Receipt): Promise<Hex> {
    if (!this.walletClient) throw new Error("walletClient required for write");
    const labelh = labelhash(p.label) as Hex;
    const subnameNode = keccak256(
      ("0x" + this.bankonEthNode.slice(2) + labelh.slice(2)) as Hex,
    ) as Hex;
    const data = encodeFunctionData({
      abi: BANKON_SUBNAME_REGISTRAR_ABI,
      functionName: "register",
      args: [
        p.label,
        p.owner,
        BigInt(p.durationYears),
        p.payment === "eth" ? 0 : p.payment === "usdc-permit" ? 1 : 2,
        x402 ? encodeX402(x402) : "0x",
      ],
    });
    const account = this.walletClient.account!;
    const hash = await this.walletClient.sendTransaction({
      account,
      chain: this.walletClient.chain!,
      to:    this.addresses.subnameRegistrar,
      data,
      value: p.payment === "eth" ? await this.estimateEthValue(p.label, p.durationYears) : 0n,
    });
    return hash;
  }

  // ── Flow B: purchase newdomain.eth ────────────────────────────────

  async purchaseCommit(p: PurchaseParams): Promise<{ hash: Hex; commitment: Hex }> {
    if (!this.walletClient) throw new Error("walletClient required for write");
    const account = this.walletClient.account!;
    const secret = keccak256(toHex(`${p.label}|${p.owner}|${Date.now()}`)) as Hex;
    const commitParams = {
      label: p.label,
      owner: p.owner,
      durationYears: BigInt(p.durationYears),
      secret,
      resolver: p.resolver,
      reverseRecord: p.reverseRecord,
      ownerControlledFuses: p.ownerControlledFuses,
    };
    const data = encodeFunctionData({
      abi: BANKON_ETH_REGISTRAR_ABI,
      functionName: "commit",
      args: [commitParams],
    });
    const hash = await this.walletClient.sendTransaction({
      account,
      chain: this.walletClient.chain!,
      to:    this.addresses.ethRegistrar,
      data,
    });
    // Commitment is deterministic from params; recompute client-side for tracking.
    const commitment = keccak256(toBytes(JSON.stringify(commitParams))) as Hex;
    return { hash, commitment };
  }

  async purchaseReveal(p: PurchaseParams, secret: Hex, x402?: X402Receipt): Promise<Hex> {
    if (!this.walletClient) throw new Error("walletClient required for write");
    const account = this.walletClient.account!;
    const { wei } = await this.quoteEthPurchase(p.label, p.durationYears);
    const payment = (p.payment === "x402-avm" && x402)
      ? (("0x02" + encodeX402(x402).slice(2)) as Hex)
      : "0x" as Hex;
    const commitParams = {
      label: p.label,
      owner: p.owner,
      durationYears: BigInt(p.durationYears),
      secret,
      resolver: p.resolver,
      reverseRecord: p.reverseRecord,
      ownerControlledFuses: p.ownerControlledFuses,
    };
    const data = encodeFunctionData({
      abi: BANKON_ETH_REGISTRAR_ABI,
      functionName: "reveal",
      args: [commitParams, payment],
    });
    const hash = await this.walletClient.sendTransaction({
      account,
      chain: this.walletClient.chain!,
      to:    this.addresses.ethRegistrar,
      data,
      value: wei,
    });
    return hash;
  }

  // ── Flow C: host an existing .eth (issue subnames under it) ───────

  async issueUnderHosted(p: HostIssueParams, x402?: X402Receipt): Promise<Hex> {
    if (!this.walletClient) throw new Error("walletClient required for write");
    const account = this.walletClient.account!;
    const payment = (p.payment === "x402-avm" && x402)
      ? (("0x02" + encodeX402(x402).slice(2)) as Hex)
      : "0x" as Hex;
    const data = encodeFunctionData({
      abi: BANKON_DOMAIN_HOSTING_ABI,
      functionName: "issue",
      args: [p.parentNode, p.label, p.owner, payment],
    });
    const hash = await this.walletClient.sendTransaction({
      account,
      chain: this.walletClient.chain!,
      to:    this.addresses.domainHosting,
      data,
      value: p.payment === "eth" ? parseEther("0.01") : 0n,
    });
    return hash;
  }

  // ── Read helpers ──────────────────────────────────────────────────

  async resolveAddr(label: string, parent: "bankon.eth" | Hex = "bankon.eth"): Promise<Address> {
    const parentNode = parent === "bankon.eth" ? this.bankonEthNode : parent;
    const node = keccak256(
      ("0x" + parentNode.slice(2) + (labelhash(label) as Hex).slice(2)) as Hex,
    ) as Hex;
    const addr = await this.publicClient.readContract({
      address: this.addresses.resolver,
      abi:     BANKON_SUBNAME_RESOLVER_ABI,
      functionName: "addr",
      args:    [node],
    }) as Address;
    return addr;
  }

  async tbaOfLabel(label: string): Promise<Address> {
    const lh = labelhash(label) as Hex;
    const tba = await this.publicClient.readContract({
      address: this.addresses.inftAdapter,
      abi:     BANKON_INFT_ADAPTER_ABI,
      functionName: "tbaAddressOf",
      args:    [lh],
    }) as Address;
    return tba;
  }

  async isX402ReceiptSpent(receiptHash: Hex): Promise<boolean> {
    return await this.publicClient.readContract({
      address: this.addresses.x402Attestor,
      abi:     BANKON_X402_ATTESTOR_ABI,
      functionName: "isReceiptSpent",
      args:    [receiptHash],
    }) as boolean;
  }

  // ── Internal ──────────────────────────────────────────────────────

  private async estimateEthValue(label: string, durationYears: number): Promise<bigint> {
    // For Flow A, the registrar prices in USD and converts via the oracle on-chain;
    // the client doesn't need to send msg.value for non-ETH rails. For ETH rail
    // we leave the upstream registrar to compute on-chain pricing — this stub
    // sends a generous bound; the contract should refund.
    return parseEther("0.01");
  }
}

// ── x402 receipt encoding helper ──────────────────────────────────

export function encodeX402(r: X402Receipt): Hex {
  // EIP-712 tuple encoding — matches the BankonX402Attestor.X402Receipt struct.
  // For now this is a simple abi.encode-style payload; consumers should use
  // viem's encodeAbiParameters for production code.
  return ("0x" +
    r.receiptHash.slice(2).padStart(64, "0") +
    r.claimant.slice(2).padStart(64, "0") +
    r.usd6.toString(16).padStart(64, "0") +
    r.nonce.toString(16).padStart(16, "0") +
    r.expiresAt.toString(16).padStart(16, "0") +
    r.signature.slice(2)) as Hex;
}

export { BANKON_SUBNAME_REGISTRAR_ABI, BANKON_ETH_REGISTRAR_ABI, BANKON_DOMAIN_HOSTING_ABI } from "./abis";

// UI helpers — the @bankoneth/ui package leans on these for the
// pre-sign TBA preview, the in-tab availability pill, and the label-taken
// suggestion cards.
export {
  ERC6551_REGISTRY,
  previewTba,
  labelToTokenId,
  bankonSubnameNode,
  shortHex,
  type PreviewTbaArgs,
} from "./inft";
export {
  checkAvailability,
  createDebouncedAvailabilityChecker,
  type AvailabilityResult,
  type AvailabilityCallback,
  type AvailabilityHandle,
  type CheckAvailabilityArgs,
} from "./availability";
export {
  generateAlternatives,
  suggestAlternatives,
  reasonFor,
  type Suggestion,
  type SuggestionsArgs,
} from "./suggestions";
export {
  lookupName,
  hasFuse,
  formatExpiry,
  BANKON_RECORD_KEYS,
  FUSE,
  type NameLookup,
  type LookupArgs,
  type RecordKey,
  type FuseName,
} from "./lookup";

// ── v2 — ENS foundations (Phase 1) ────────────────────────────────
export {
  MAINNET,
  SEPOLIA,
  ENS_BY_CHAIN,
  ensAddressesFor,
  ZERO_ADDR,
  type EnsAddresses,
} from "./addresses";

export {
  normalize,
  normalizeLabel,
  splitLabels,
  isNormalized,
  EnsNormalizeError,
} from "./normalize";

export {
  evmCoinType,
  chainIdFromCoinType,
  isEvmCoinType,
  COIN_TYPE,
  COIN_TYPES,
  metaFor,
  metaForCoinType,
  type CoinTypeName,
  type CoinTypeMeta,
} from "./coin-types";

export {
  UNIVERSAL_RESOLVER_MAINNET,
  UNIVERSAL_RESOLVER_SEPOLIA,
  resolveProfile,
  resolveReverse,
  type ProfileLookup,
  type ProfileLookupArgs,
  type ReverseLookup,
  type ReverseLookupArgs,
} from "./universal-resolver";

export {
  getNamesForAddress,
  getSubnames,
  getNameHistory,
  type OwnedName,
  type SubnameEntry,
  type NameHistoryEvent,
} from "./inventory";

// Re-exports for convenience.
export { namehash, labelhash };
