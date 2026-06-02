// SPDX-License-Identifier: Apache-2.0
//
// Client-side ERC-6551 TBA address derivation.
//
// Matches the on-chain computation in
// openagents/bankoneth/contracts/BankonInftAdapter.sol:_computeTba(): the
// singleton ERC-6551 registry at 0x000000006551c19487814612e58FE06813775758
// derives TBAs via CREATE2 against:
//
//     keccak256(0xff || registry || salt || keccak256(initCode))
//
// where initCode = (proxy bytecode || account abi-encoded args). Computing
// this locally lets the UI preview the agent's wallet address before the
// user signs anything — the headline UX-win #1 in the bankoneth design.

import {
  type Address,
  type Hex,
  encodePacked,
  keccak256,
  getCreate2Address,
  labelhash,
  pad,
  toHex,
} from "viem";

/** Canonical ERC-6551 registry address (same on every EVM chain). */
export const ERC6551_REGISTRY: Address = "0x000000006551c19487814612e58FE06813775758";

/** The proxy code template used by BankonInftAdapter (matches contract source). */
function proxyCreationCode(implementation: Address): Hex {
  return ("0x3d60ad80600a3d3981f3363d3d373d3d3d363d73" +
    implementation.slice(2).toLowerCase() +
    "5af43d82803e903d91602b57fd5bf3") as Hex;
}

export interface PreviewTbaArgs {
  /** ERC-6551 account-implementation contract on the chain where the iNFT lives. */
  implementation: Address;
  /** Chain id of the iNFT (e.g. 0G Galileo = 16601). */
  chainId: bigint | number;
  /** The iNFT contract address on `chainId`. */
  tokenContract: Address;
  /** Deterministic tokenId. For Mode A we use uint256(labelhash). */
  tokenId: bigint;
  /** Optional CREATE2 salt — defaults to bytes32(0) to match the contract. */
  salt?: Hex;
}

/**
 * Compute the ERC-6551 TBA address deterministically, off-chain.
 *
 * Use this in the UI to render a TBA preview the moment the user has typed
 * a label, no RPC round-trip needed. The on-chain `tbaAddressOf(labelhash)`
 * view will return the same address once the iNFT is minted on 0G and the
 * cross-chain binding is registered.
 */
export function previewTba(args: PreviewTbaArgs): Address {
  const salt = args.salt ?? ("0x" + "00".repeat(32) as Hex);
  const proxyCode = proxyCreationCode(args.implementation);
  const encodedArgs = encodePacked(
    ["bytes32", "uint256", "address", "uint256"],
    [salt, BigInt(args.chainId), args.tokenContract, args.tokenId],
  );
  const initCode = (proxyCode + encodedArgs.slice(2)) as Hex;
  return getCreate2Address({
    from: ERC6551_REGISTRY,
    salt,
    bytecodeHash: keccak256(initCode),
  });
}

/**
 * Derive (labelhash, tokenId) from a human-readable subname label.
 *
 * For Flow A subnames (alice.bankon.eth), the registrar uses
 * `uint256(keccak256(bytes("alice")))` as the iNFT tokenId on 0G. This
 * helper matches that exactly so previewTba() and the on-chain mint agree.
 */
export function labelToTokenId(label: string): { labelhash: Hex; tokenId: bigint } {
  const lh = labelhash(label) as Hex;
  return { labelhash: lh, tokenId: BigInt(lh) };
}

/** Convenience: the full ENS namehash of `${label}.bankon.eth`. */
export function bankonSubnameNode(label: string, bankonEthNode: Hex): Hex {
  const lh = labelhash(label) as Hex;
  return keccak256(
    encodePacked(["bytes32", "bytes32"], [pad(bankonEthNode, { size: 32 }), lh]),
  );
}

/** Used by the UI for the visible "bytes32 namehash" preview card. */
export function shortHex(h: Hex, head = 6, tail = 4): string {
  if (h.length <= head + tail + 2) return h;
  return `${h.slice(0, head + 2)}…${h.slice(-tail)}`;
}

// Re-export `toHex` for consumers that want it; keeps the @bankoneth/core
// surface predictable.
export { toHex };
