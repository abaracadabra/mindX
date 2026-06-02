# `THOT/commitment/` — cryptographic substrate

This directory holds the **content-addressable + Matryoshka-prefix-bound +
censurable** registry for canonical THOT4096 Merkle roots. It is the
cryptographic substrate that consumers (`iNFT_7857.attachThotRoot`,
`AgenticPlace` filters, audit tooling) rely on to assert "this sealed
payload corresponds to a known, non-revoked THOT4096."

## Two registries, separate concerns

`daio/contracts/THOT/` ships **two** registry surfaces. They are
intentionally distinct and **must not be confused**:

| Surface | Interface | Concrete impl | Purpose |
|---|---|---|---|
| Discovery | `interfaces/ITHOTRegistry.sol` | (not yet shipped) | Model name, parameter count, ratings, deployment counts. The "Yelp" of THOTs. |
| **Cryptographic** | **`interfaces/ITHOTCommitmentRegistry.sol`** | **`commitment/THOTCommitmentRegistry.sol`** | **Canonical Merkle roots, Matryoshka prefix bindings, diagonal lineage edges, censura revocation.** |

If you want to ask "what models exist matching this architecture?" you
want the discovery registry. If you want to ask "is this specific Merkle
root a real, registered, non-revoked THOT4096?" you want the commitment
registry.

This directory is the latter.

## What this registry stores

- **Canonical THOT4096 records.** Keyed by Merkle root. Each entry binds
  the root to its `ternaryHead` (the dedicated THOT8 sub-leaf), its CID,
  metadata URI, issuer address, and issuance timestamp.
- **Matryoshka prefix records.** Verified via
  [`THOTLib.verifyPrefix`](../libraries/THOTLib.sol) — the
  cryptographic prefix-binding theorem (THOTS.md §9.5). Once a prefix
  (THOT768 / THOT1024 / THOT2048) is registered for a parent, anyone
  can look it up.
- **Diagonal edges** — a DAG of distillation / projection / federation
  relationships between THOTs. Authorized-only writes prevent spam.
- **Revocation flags.** A `CENSURA_ROLE` can revoke a root in response
  to a backdoor finding, licensing violation, or constitutional review.
  Revocation does not delete the registration; it flips a flag that
  downstream consumers (notably `iNFT_7857.transferWithSealedKey`)
  honour to block trust flows tied to the revoked root.

## How `iNFT_7857` consumes the registry

After deployment, an admin calls:

```solidity
iNFT_7857.setCommitmentRegistry(ITHOTCommitmentRegistry(registryAddr));
```

This wires the registry into the iNFT. From then on:

1. A `MINTER_ROLE` can call `attachThotRoot(tokenId, root)` to bind a
   freshly-minted token to a registered THOT4096 root. The registry's
   `isRegistered` and `isRevoked` are consulted before the binding
   sticks. The binding is **immutable** once set — a token's THOT root
   never changes.
2. On `transferWithSealedKey`, if the token has an attached root and
   that root has since been revoked, the transfer reverts. This is the
   load-bearing security property described in
   `docs/operations/THOT,…md` §C: an INFT whose underlying weights are
   discovered to contain a backdoor cannot be quietly moved to a
   new owner.

Tokens minted without `attachThotRoot` behave exactly as before — the
registry binding is opt-in.

## Roles

| Role | Held by | Capabilities |
|---|---|---|
| `DEFAULT_ADMIN_ROLE` | 3-of-5 multisig (prod) | Grant/revoke any role; rotate the BANKON gate. |
| `CENSURA_ROLE` | The same multisig in v1; a 2-of-3 Censura sub-quorum later | `revoke(root, reason)` and `unrevoke(root)`. |
| Authorized issuer | EOAs / multisigs the BANKON gate has authorized | `issueTHOT4096(...)` and `recordEdge(...)`. |
| BANKON identity gate | An EOA or multisig bound to a BANKON AlgoIDNFT | `authorizeIssuer(addr)` and `revokeIssuer(addr)`. |

## Operator install

See [`../../script/README.md`](../../script/README.md) — the
`DeployTHOTCommitment.s.sol` Sepolia → mainnet runbook with the 7–14 day
soak checklist and six promotion criteria.

## Python reference codec

The off-chain side that produces the roots, ternary heads, and prefix
proofs that this registry verifies lives at
[`../python/`](../python/README.md). The two sides MUST produce
byte-identical hashes — there's a Solidity ↔ Python parity test in
[`../../test/thot/THOTLib.t.sol`](../../test/thot/THOTLib.t.sol)
pinning a known-good fixture.

## Where this comes from

Adapted from `docs/operations/thotconsiderations.zip` (zip's
`THOTRegistry.sol` + `THOTLib.sol`), with security patches:

- `AccessControl` with `CENSURA_ROLE`.
- `revoke()` / `unrevoke()` / `isRegistered()` / `isRevoked()` /
  `ternaryHeadOf()` view surface matching the architecture doc's
  `MindXCheckpointRegistry` interface.
- `recordEdge` access-control + no-overwrite check.
- `registerPrefix` upfront length validation via
  `THOTLib.assertPrefixLeavesLength`.
- RFC-6962 internal-node `0x01` prefix in `THOTLib.merkleRoot` and
  the climb paths (closes the leaf-vs-internal-node confusion vector).
- Test compile bug in zip's `THOTRegistry.t.sol` fixed
  (5-arg `registerPrefix` → 6-arg, matching the actual contract).

## License

Apache-2.0. See `../LICENSE` (or repo root if absent).
