# ITHOTCommitmentRegistry

> Cryptographic-substrate ABI for THOT4096 Merkle commitments — proves a canonical root has been issued, tracks censura revocation, exposes ternary-head and Matryoshka prefix lookups.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`ITHOTCommitmentRegistry.sol`](./ITHOTCommitmentRegistry.sol)

## Role in bankoneth

`ITHOTCommitmentRegistry` is the **cryptographic-substrate** half of the THOT registry split. The full architecture has two side-by-side registries:

| Registry | Purpose | File |
| --- | --- | --- |
| `ITHOTRegistry` | Discovery & rating: model name, parameter count, ratings, deployment count | `THOT/interfaces/ITHOTRegistry.sol` (outside this tree) |
| `ITHOTCommitmentRegistry` | Cryptographic anchor: canonical Merkle roots, ternary heads, Matryoshka prefix bindings, revocation | This file |

They are **intentionally distinct** — and the file header is explicit about this. The discovery registry says "this model exists, here's how it's rated." The commitment registry says "this exact 4096-dim THOT Merkle root has been canonically issued and not censura-revoked." Both are consulted by `AgenticPlace` and `iNFT_7857` for different purposes.

In bankoneth specifically, this interface is consumed by [`iNFT_7857.sol`](../iNFT_7857.sol) in two places:

1. **`attachThotRoot(tokenId, root)`** — checks `isRegistered(root) && !isRevoked(root)` before binding the root to the token. Privileged (MINTER_ROLE) because attaching is an admin assertion that the registered root corresponds to the sealed payload (the registry only proves the root *exists*).
2. **`transferWithSealedKey(...)`** — if the token has an attached root and a registry is configured, the transfer reverts when `isRevoked(root) == true`. This is the **post-mint revocation flow**: once a THOT4096 root is censura-revoked, sealed-key handoffs for tokens bound to it stop functioning, effectively quarantining the token's payload.

The concrete implementation lives at `THOT/commitment/THOTCommitmentRegistry.sol` (outside `bankoneth/`). bankoneth only imports the interface, keeping it agnostic about which registry instance is wired.

## Interfaces defined

### `ITHOTCommitmentRegistry`

A single, deliberately small read-only interface (all four functions are `view`). All write paths (`register`, `revoke`, `setPrefix`, `setTernaryHead`) live on the concrete implementation outside this ABI — consumers like `iNFT_7857` need only the read surface.

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `isRegistered(bytes32 root) external view returns (bool)` | yes | Returns `true` iff a canonical THOT4096 with this exact Merkle root has been issued (i.e. `register(root, …)` has been called on the implementation) |
| `isRevoked(bytes32 root) external view returns (bool)` | yes | Returns `true` iff the root has been censura-revoked. Independent of registration — a non-registered root returns `false` here too; consumers must check both for true validity |
| `ternaryHeadOf(bytes32 root) external view returns (bytes32)` | yes | Returns the ternary-head sub-leaf hash committed for this THOT4096, or `bytes32(0)` if not registered. The ternary head is the part of the THOT structure that encodes the {−1, 0, +1} ternary representation |
| `getPrefix(bytes32 parentRoot, uint16 prefixDim) external view returns (bytes32 prefixRoot, bool exists)` | yes | Matryoshka prefix lookup: given a canonical THOT4096 `parentRoot` and a `prefixDim` ∈ {768, 1024, 2048}, returns the prefix root and an existence flag. `exists == false` means "no prefix has been registered at that dim for this parent" |

**Defined events:**

None on the interface. Event emission is the concrete implementation's responsibility (the implementation at `THOT/commitment/THOTCommitmentRegistry.sol` is expected to emit `Registered`, `Revoked`, `PrefixSet`, `TernaryHeadSet`, etc., but those are not part of the consumer ABI).

**Defined structs/typedefs:**

None — all four functions return primitive types or `(bytes32, bool)` tuples.

**Implementers (concrete contracts in the bankoneth tree that implement this):**

- None within `bankoneth/contracts/`. The concrete implementation lives at `THOT/commitment/THOTCommitmentRegistry.sol` in the broader DAIO/THOT tree.

**Callers (contracts that hold an `ITHOTCommitmentRegistry` typed reference):**

- [`iNFT_7857.sol`](../iNFT_7857.sol) — holds `ITHOTCommitmentRegistry public commitmentRegistry`. Calls:
  - `isRegistered(root)` — inside `attachThotRoot`
  - `isRevoked(root)` — inside `attachThotRoot` AND inside `transferWithSealedKey` (revoke gate)
  - `ternaryHeadOf(...)` and `getPrefix(...)` are not called by bankoneth contracts but are part of the interface for completeness; off-chain consumers and other ecosystem contracts (in the wider THOT/AgenticPlace tree) use them

## See also

- [`iNFT_7857.sol`](../iNFT_7857.sol) — the consumer; `attachThotRoot` + `transferWithSealedKey` revoke gate
- `THOT/commitment/THOTCommitmentRegistry.sol` — concrete implementation (outside `bankoneth/`)
- `THOT/interfaces/ITHOTRegistry.sol` — the discovery/rating registry that coexists with this commitment registry
- Matryoshka representation learning — the source of the `{768, 1024, 2048}` prefix-dim whitelist
- THOT4096 spec — for the meaning of `ternaryHeadOf` and the canonical Merkle root structure
