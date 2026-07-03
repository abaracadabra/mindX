// SPDX-License-Identifier: Apache-2.0
//
// @openagents/overlord — identity.ts
//
// Identity = a public wallet key proven by signature. Proven two ways, in the
// w3d / OpenZeppelin SignatureChecker spirit (pure viem):
//   1. ECDSA EOA recovery — recoverMessageAddress() must return the claimed
//      address (mirrors mindx_backend_service/bankon_vault/shadow_overlord.py
//      recover → constant-time compare).
//   2. ERC-1271 — for smart-contract accounts, call isValidSignature() on-chain
//      and check the 0x1626ba7e magic value.

import {
  getAddress,
  hashMessage,
  recoverMessageAddress,
  parseAbi,
  type Address,
  type Hex,
  type PublicClient,
} from "viem";

/** ERC-1271 magic value returned by a valid isValidSignature(bytes32,bytes). */
export const ERC1271_MAGIC = "0x1626ba7e" as const;

const ERC1271_ABI = parseAbi([
  "function isValidSignature(bytes32 hash, bytes signature) view returns (bytes4)",
]);

export interface ChallengeArgs {
  domain: string;
  address: Address;
  scope: string;
  nonce: string;
  /** Unix seconds; defaults to now. Override for deterministic tests. */
  issuedAt?: number;
  /** Challenge lifetime in seconds. Default 300. */
  ttlSec?: number;
}

/**
 * The canonical login challenge. Server-built, deterministic from (domain,
 * address, scope, nonce) so the wallet endorses exactly what the server will
 * enforce — the scope/param-binding discipline from the shadow-overlord design.
 */
export function buildChallenge(a: ChallengeArgs): string {
  const issued = a.issuedAt ?? Math.floor(Date.now() / 1000);
  const exp = issued + (a.ttlSec ?? 300);
  return [
    "OVERLORD-LOGIN",
    `domain: ${a.domain}`,
    `wallet: ${getAddress(a.address)}`,
    `scope: ${a.scope}`,
    `nonce: ${a.nonce}`,
    `issued_at: ${issued}`,
    `exp: ${exp}`,
  ].join("\n");
}

/** Checksum-normalized equality; false on any malformed input. */
export function addrEq(a: string, b: string): boolean {
  try {
    return getAddress(a) === getAddress(b);
  } catch {
    return false;
  }
}

export type IdentityMethod = "ecdsa" | "erc1271" | "none";

export interface IdentityProof {
  proven: boolean;
  method: IdentityMethod;
  recovered?: Address;
}

/**
 * Prove that `claimed` signed `message`. EOA first (offline-verifiable); falls
 * back to on-chain ERC-1271 when a publicClient is supplied (smart accounts).
 * Never throws.
 */
export async function proveIdentity(args: {
  claimed: Address;
  message: string;
  signature: Hex;
  publicClient?: PublicClient;
}): Promise<IdentityProof> {
  // 1. ECDSA EOA recovery.
  try {
    const recovered = await recoverMessageAddress({
      message: args.message,
      signature: args.signature,
    });
    if (addrEq(recovered, args.claimed)) {
      return { proven: true, method: "ecdsa", recovered };
    }
  } catch {
    /* fall through to ERC-1271 */
  }

  // 2. ERC-1271 smart-account verification.
  if (args.publicClient) {
    try {
      const hash = hashMessage(args.message);
      const res = (await args.publicClient.readContract({
        address: getAddress(args.claimed),
        abi: ERC1271_ABI,
        functionName: "isValidSignature",
        args: [hash, args.signature],
      })) as Hex;
      if (typeof res === "string" && res.toLowerCase().startsWith(ERC1271_MAGIC)) {
        return { proven: true, method: "erc1271", recovered: getAddress(args.claimed) };
      }
    } catch {
      /* not a 1271 account / call failed */
    }
  }

  return { proven: false, method: "none" };
}
