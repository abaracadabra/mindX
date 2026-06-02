// SPDX-License-Identifier: Apache-2.0
//
// auth.ts — Phase 2.4 — SIWE / EIP-4361 + bankoneth gate bundles.
//
// Constructs the human-signable EIP-4361 message, gets the signature via a
// viem WalletClient, hands the bundle to either:
//   - BankonAuthGate.verifyOwnsLabel(message, signature, label)
//   - BankonAuthGate.verifyTextClaim(message, signature, resolver, node, key)
//
// SIWE message format (EIP-4361):
//   <domain> wants you to sign in with your Ethereum account:
//   <address>
//
//   <statement>
//
//   URI: <uri>
//   Version: 1
//   Chain ID: <chainId>
//   Nonce: <nonce>
//   Issued At: <issuedAt ISO-8601>
//   [Expiration Time: <ISO-8601>]
//   [Not Before: <ISO-8601>]
//   [Request ID: <id>]
//   [Resources:
//   - <r1>
//   - <r2>]

import type { Address, Hex, WalletClient } from "viem";

/** Args to construct an EIP-4361 message. */
export interface SiweMessageArgs {
  /** The EOA signing in (the connected wallet). */
  address: Address;
  /** RFC-3986 host (no scheme) — e.g. "mindx.pythai.net" or "localhost:3000". */
  domain: string;
  /** Full URI of the resource being requested — e.g. "https://mindx.pythai.net/auth". */
  uri: string;
  /** Chain ID the signature should be scoped to. */
  chainId: number;
  /** Cryptographically random nonce, ≥8 chars. Caller supplies + persists. */
  nonce: string;
  /** Optional human-readable statement shown above the metadata block. */
  statement?: string;
  /** Optional expiry. */
  expirationTime?: Date;
  /** Optional not-before. */
  notBefore?: Date;
  /** Optional opaque correlation ID. */
  requestId?: string;
  /** Optional resource URIs (one per line). */
  resources?: readonly string[];
  /** Defaults to `new Date()`. Override for deterministic testing. */
  issuedAt?: Date;
  /** Defaults to "1". */
  version?: "1";
}

/** Build an EIP-4361 (SIWE) message string. */
export function siweMessage(args: SiweMessageArgs): string {
  const issuedAt = (args.issuedAt ?? new Date()).toISOString();
  const version  = args.version ?? "1";

  const header = `${args.domain} wants you to sign in with your Ethereum account:\n${args.address}`;
  const stmt   = args.statement ? `\n\n${args.statement}` : "";
  const meta: string[] = [
    `URI: ${args.uri}`,
    `Version: ${version}`,
    `Chain ID: ${args.chainId}`,
    `Nonce: ${args.nonce}`,
    `Issued At: ${issuedAt}`,
  ];
  if (args.expirationTime) meta.push(`Expiration Time: ${args.expirationTime.toISOString()}`);
  if (args.notBefore)      meta.push(`Not Before: ${args.notBefore.toISOString()}`);
  if (args.requestId)      meta.push(`Request ID: ${args.requestId}`);
  if (args.resources?.length) {
    meta.push("Resources:");
    for (const r of args.resources) meta.push(`- ${r}`);
  }

  return `${header}${stmt}\n\n${meta.join("\n")}`;
}

/** Result of `signInWithBankoneth`. */
export interface SiweBundle {
  /** The EIP-4361 message that was signed (verbatim what the user saw). */
  message: string;
  /** The EIP-191 personal_sign signature. */
  signature: Hex;
  /** The signer address. */
  address: Address;
}

/** Args to `signInWithBankoneth`. */
export interface SignInArgs {
  walletClient: WalletClient;
  address: Address;
  /** Defaults pulled from `walletClient.chain` + window.location when not set. */
  domain?: string;
  uri?: string;
  chainId?: number;
  /** Optional human-readable statement shown to the signer. */
  statement?: string;
  /** Optional expiry. */
  expirationTime?: Date;
  /** Optional opaque correlation ID. */
  requestId?: string;
  /** Optional resource URIs. */
  resources?: readonly string[];
  /** Defaults to a 16-char hex nonce. Override only for testing. */
  nonce?: string;
}

/**
 * Produce a SIWE bundle (message + signature) via the connected wallet's
 * personal_sign. Caller hands the bundle to BankonAuthGate.
 */
export async function signInWithBankoneth(args: SignInArgs): Promise<SiweBundle> {
  const chainId  = args.chainId ?? args.walletClient.chain?.id ?? 1;
  const domain   = args.domain ?? (typeof window !== "undefined" ? window.location.host : "bankon.eth");
  const uri      = args.uri    ?? (typeof window !== "undefined" ? window.location.href : `https://${domain}`);
  const nonce    = args.nonce  ?? _nonce();

  const message = siweMessage({
    address:         args.address,
    domain,
    uri,
    chainId,
    nonce,
    statement:       args.statement,
    expirationTime:  args.expirationTime,
    requestId:       args.requestId,
    resources:       args.resources,
  });

  const signature = await args.walletClient.signMessage({
    account: args.address,
    message,
  });

  return { message, signature, address: args.address };
}

/** Generate a 16-char hex nonce via the WebCrypto-or-Math fallback. */
function _nonce(): string {
  // Browser: crypto.getRandomValues. Node: globalThis.crypto.
  const g: any = globalThis as any;
  if (g.crypto && typeof g.crypto.getRandomValues === "function") {
    const bytes = new Uint8Array(8);
    g.crypto.getRandomValues(bytes);
    return Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");
  }
  // Fallback — non-cryptographic, fine for prototype dev.
  return Math.random().toString(16).slice(2, 18).padEnd(16, "0");
}

/** Optional client-side recovery — verify the signer locally before submission. */
export async function recoverSiweSigner(bundle: SiweBundle): Promise<Address> {
  const { recoverMessageAddress } = await import("viem");
  return recoverMessageAddress({ message: bundle.message, signature: bundle.signature });
}
