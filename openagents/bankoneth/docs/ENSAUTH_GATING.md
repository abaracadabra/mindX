# bankoneth — ENS-gated Authentication (`BankonAuthGate`)

Phase 2.4 — on-chain SIWE / EIP-4361 verifier that lets downstream services
gate access on "must hold *.bankon.eth" (or any custom predicate).

## Why on-chain

[mDeisen/ensauth](https://github.com/mDeisen/ensauth) showed how to gate
access via ENS subname ownership using off-chain text records as a
permission registry. bankoneth's approach is more direct: the gate is a
contract, the predicate is `NameWrapper.ownerOf(namehash(label.bankon.eth))`,
no external indexer required.

## Two modes

### Mode 1 — NameWrapper-ownership

```solidity
function verifyOwnsLabel(
    string calldata siweMessage,
    bytes  calldata signature,
    string calldata label
) external view returns (bool);
```

Recovers the signer from a personal_sign signature over the SIWE message.
Asserts `NameWrapper.ownerOf(namehash(label + ".bankon.eth")) == signer`.

Use when: "must hold `<anything>`.bankon.eth" — gating access to mindx
endpoints, AgenticPlace listings, etc.

### Mode 2 — Resolver text-record claim

```solidity
function verifyTextClaim(
    string calldata siweMessage,
    bytes  calldata signature,
    IAuthGateResolver resolver,
    bytes32 node,
    string calldata key
) external view returns (bool);
```

Recovers the signer. Asserts `resolver.text(node, key)` equals the
lowercased hex address of the signer. Case-insensitive comparison so
EIP-55 / lowercased / mixed-case all work.

Use when: a name is owned by a multi-sig but routes auth to a delegate
EOA. The owner sets `resolver.text(node, "authz.signer") = "0x..."` and
the delegate signs SIWE bundles on the multi-sig's behalf.

Both modes also expose a `verify*Digest` variant that takes a raw 32-byte
digest — useful for EIP-712 typed-data callers.

## Client integration

`@bankoneth/core` ships [`signInWithBankoneth`](../packages/core/src/auth.ts)
that builds the SIWE bundle:

```ts
import { signInWithBankoneth } from "@bankoneth/core";

const bundle = await signInWithBankoneth({
  walletClient,
  address,
  domain:    "mindx.pythai.net",
  statement: "Sign in to access your agent",
  resources: ["mindx.endpoint"],
});

// bundle.message    — the EIP-4361 message the user signed
// bundle.signature  — personal_sign signature
// bundle.address    — signer

// Either verify on-chain via BankonAuthGate, OR send to your backend.
```

The UI primitive [`<b-siwe-signin>`](../packages/ui/src/manage/b-siwe-signin.ts)
wraps this in a one-click button + status states.

## Backend verification

Two paths, both feasible:

### A. On-chain (most secure)
Your service calls `BankonAuthGate.verifyOwnsLabel(message, signature, label)`
as a `staticcall`. The gate is stateless — no gas cost beyond eth_call.

```ts
const ok = await publicClient.readContract({
  address: AUTH_GATE_ADDR,
  abi:     AUTH_GATE_ABI,
  functionName: "verifyOwnsLabel",
  args: [bundle.message, bundle.signature, "alice"],
}) as boolean;
```

### B. Off-chain (cheapest)
Recover the signer locally via viem's `verifyMessage`, then read
`NameWrapper.ownerOf` directly. Skips the gate contract entirely but
duplicates the gate's logic in your service code.

```ts
import { verifyMessage } from "viem";

const valid = await verifyMessage({
  address: bundle.address,
  message: bundle.message,
  signature: bundle.signature,
});
if (!valid) return null;

const node = namehash(`alice.bankon.eth`);
const owner = await publicClient.readContract({
  address: NAME_WRAPPER,
  abi:     NAME_WRAPPER_ABI,
  functionName: "ownerOf",
  args:    [BigInt(node)],
}) as Address;

if (owner.toLowerCase() !== bundle.address.toLowerCase()) return null;
```

Recommend A for new services — keeps the predicate logic in one place,
easier to migrate when ENSv2 changes the ownerOf shape.

## SIWE bundle anatomy

Per [EIP-4361](https://eips.ethereum.org/EIPS/eip-4361):

```
mindx.pythai.net wants you to sign in with your Ethereum account:
0xabc...

Sign in to verify your bankoneth identity.

URI: https://mindx.pythai.net/auth
Version: 1
Chain ID: 1
Nonce: a1b2c3d4e5f6...
Issued At: 2026-05-24T18:34:00.000Z
Resources:
- mindx.endpoint
```

Replay defence lives in **your service**, not the gate. Persist
`(address, nonce)` pairs; reject duplicates. The gate is stateless on
purpose — replay is a per-service concern.

## Differences from ensauth

| Concern | ensauth | bankoneth |
|---|---|---|
| Auth store | ENS text records (off-chain) | NameWrapper ownership OR text record |
| Verification | Off-chain (frontend reads records) | On-chain (BankonAuthGate.verify) |
| Signature scheme | None (record-presence is the gate) | EIP-4361 SIWE |
| Replay defence | Frontend-managed | Service-managed (per-nonce) |
| Multi-signer | Off-chain group lookup | Per-name resolver text key |

ensauth is permission *registry*. bankoneth is permission *predicate
verifier*. The two compose: store group membership via text records
(ensauth's pattern), verify each session via SIWE + bankoneth's gate.

## Further reading

- [EIP-4361 SIWE](https://eips.ethereum.org/EIPS/eip-4361)
- [CAIP-122 (chain-agnostic SIWE)](https://chainagnostic.org/CAIPs/caip-122)
- [BankonAuthGate.sol](../contracts/identity/BankonAuthGate.sol)
- [auth.ts](../packages/core/src/auth.ts)
- [`<b-siwe-signin>` UI](../packages/ui/src/manage/b-siwe-signin.ts)
- [mDeisen/ensauth](https://github.com/mDeisen/ensauth) — inspiration
- [docs/ENSIP_COVERAGE.md](ENSIP_COVERAGE.md) — full ENS surface map
