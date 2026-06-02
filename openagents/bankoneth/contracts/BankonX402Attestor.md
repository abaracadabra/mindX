# BankonX402Attestor

> EIP-712 facilitator-key registry + nonce replay guard for x402-avm receipts from the GoPlausible Algorand facilitator.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`BankonX402Attestor.sol`](./BankonX402Attestor.sol)

## Role in bankoneth

`BankonX402Attestor` is the on-chain trust anchor for the **x402-avm payment rail**. When a customer pays for a registration on Algorand (USDC ASA `31566704`) through the GoPlausible facilitator, the facilitator returns an EIP-712-signed `X402Receipt`. The registrar (Flow A, B, or C) decodes the receipt from the `payment` byte payload and calls `verify(...)` on this attestor; the attestor reverts unless the signer is a registered facilitator EOA, the receipt has not expired, and the nonce is strictly monotonic per signer.

The attestor is the **only** L1 contract that knows what a valid x402-avm receipt looks like — registrars treat it as an opaque verifier. This isolation means new facilitators (additional chains, additional providers) can be onboarded by an admin call without redeploying registrars. The receipt-hash spent-set and the per-facilitator monotonic nonce ledger are both stored here, giving two independent replay-protection layers.

In the tri-rail design, x402-avm is the most off-chain payment path (settlement happens on Algorand, not Ethereum). The attestor makes that bridge trustless **up to** the trust placed in the facilitator's signing key — so the admin role guarding `setFacilitator` should be a multisig in production.

## Inheritance

- `IBankonX402Attestor` — public interface (struct + events + functions) defined in [`interfaces/IBankonExtensions.sol`](./interfaces/IBankonExtensions.sol).
- `EIP712` — provides `_hashTypedDataV4` with domain separator `("BankonX402Attestor", "1", chainId, address(this))`.
- `AccessControl` — `DEFAULT_ADMIN_ROLE` (facilitator + consumer admin) and `CONSUMER_ROLE` (who can call `verify`).

## Constructor

| arg    | type      | purpose                                                                                  |
|--------|-----------|------------------------------------------------------------------------------------------|
| `admin`| `address` | Granted `DEFAULT_ADMIN_ROLE` — can call `setFacilitator`, `grantConsumer`, role mgmt.    |

EIP712 domain: name `"BankonX402Attestor"`, version `"1"` — both immutables baked into the bytecode.

Roles granted at construction: `DEFAULT_ADMIN_ROLE` → `admin`. **No `CONSUMER_ROLE`** is granted at construction; the deploy script explicitly grants it to each registrar (lines 122-124 of `DeployEthereum.s.sol`).

## Storage layout

| name                   | type                              | purpose                                                                  | mutable? |
|------------------------|-----------------------------------|--------------------------------------------------------------------------|----------|
| `CONSUMER_ROLE`        | `bytes32 constant`                | `keccak256("CONSUMER_ROLE")`.                                            | no       |
| `_RECEIPT_TYPEHASH`    | `bytes32 constant private`        | EIP-712 typehash for the `X402Receipt` struct.                           | no       |
| `_facilitators`        | `mapping(address => bool)`        | Registered facilitator EOAs.                                             | yes (admin) |
| `_spent`               | `mapping(bytes32 => bool)`        | Spent receipt-hash set — first replay layer.                             | yes (consumer) |
| `lastNonce`            | `mapping(address => uint64)` public | Highest consumed nonce per facilitator — second replay layer.          | yes (consumer) |

(AccessControl `_roles` and EIP712 cached domain separator are also present.)

## Roles

| Role                 | keccak256                                | Who holds                                                       | What they can do                              |
|----------------------|------------------------------------------|------------------------------------------------------------------|-----------------------------------------------|
| `DEFAULT_ADMIN_ROLE` | OpenZeppelin default (`0x00…00`)         | `admin` (constructor arg)                                        | `setFacilitator`, `grantConsumer`, manage roles. |
| `CONSUMER_ROLE`      | `keccak256("CONSUMER_ROLE")`             | `BankonSubnameRegistrar`, `BankonEthRegistrar`, `BankonDomainHosting` (post-deploy) | Call `verify(X402Receipt)` (mutates spent-set + nonce). |

## Events

### `FacilitatorRegistered(address indexed facilitator, bool active)`

Defined on the interface. Emitted by `setFacilitator(...)`. Off-chain ops dashboards should treat this as the canonical facilitator allow-list mirror. `active=false` revokes a key without deleting the storage slot, allowing audit-trail continuity.

### `ReceiptConsumed(bytes32 indexed receiptHash, address indexed claimant, uint64 nonce)`

Emitted by `verify(...)` on success. Indexers can join this event with the registrar's `SubnameRegistered`/`Registered`/`SubnameIssued` event (which shares the same `paymentReceiptHash`) to reconstruct the full x402-avm settlement timeline.

## Errors

### `ReceiptExpired()`

Reverted when `block.timestamp > r.expiresAt`. Caller should re-fetch a fresh receipt from the facilitator.

### `ReceiptAlreadyConsumed(bytes32 receiptHash)`

Reverted when `_spent[receiptHash]` is already true. Caller has hit the first replay layer — the receipt was already used in a prior registration. Hash echoed for off-chain forensics.

### `FacilitatorNotRegistered(address facilitator)`

Reverted when `ECDSA.recover(digest, r.signature)` returns an address that is not in `_facilitators`. Indicates either (a) facilitator key rotated and admin has not yet `setFacilitator(newKey, true)`, or (b) forged signature. The recovered (untrusted) address is included for ops triage.

### `NonceTooOld(uint64 supplied, uint64 last)`

Reverted when `r.nonce <= lastNonce[signer]`. The second replay layer — even if `receiptHash` collisions were possible, a stale nonce will still bounce.

## External / public API

### `setFacilitator(address facilitator, bool active) external`

Adds or removes a facilitator EOA. Access: `DEFAULT_ADMIN_ROLE`. Emits `FacilitatorRegistered(facilitator, active)`. No effect on `lastNonce[facilitator]` — deactivating and reactivating preserves the monotonic counter to prevent replay across key cycles.

### `grantConsumer(address consumer) external`

Convenience wrapper. Grants `CONSUMER_ROLE` to `consumer`. Access: `DEFAULT_ADMIN_ROLE`. Used by `DeployEthereum.s.sol` for the three registrars.

### `verify(X402Receipt calldata r) external returns (bool)`

The hot-path. Behaviour, in order:

1. Revert `ReceiptExpired` if `block.timestamp > r.expiresAt`.
2. Revert `ReceiptAlreadyConsumed` if `_spent[r.receiptHash]`.
3. Build EIP-712 struct hash over `_RECEIPT_TYPEHASH` + the receipt fields, hash with `_hashTypedDataV4`.
4. `ECDSA.recover` the signer.
5. Revert `FacilitatorNotRegistered` if signer is not in `_facilitators`.
6. Revert `NonceTooOld` if `r.nonce <= lastNonce[signer]`.
7. Update `lastNonce[signer] = r.nonce`.
8. Set `_spent[r.receiptHash] = true`.
9. Emit `ReceiptConsumed(r.receiptHash, r.claimant, r.nonce)`.
10. Return `true`.

Access: `CONSUMER_ROLE`. **State-mutating** despite `verify` naming — registrars rely on the mutation to enforce one-shot replay protection. Returns `true` on success (always; on failure the function reverts before returning).

### `isReceiptSpent(bytes32 receiptHash) external view returns (bool)`

Returns `_spent[receiptHash]`. Pure view; safe to call from anywhere.

### `isFacilitatorActive(address facilitator) external view returns (bool)`

Returns `_facilitators[facilitator]`. Pure view.

## Internal helpers

Only `EIP712._hashTypedDataV4` and `ECDSA.recover` from OpenZeppelin — no custom internals.

## Invariants

- For each `facilitator` in `_facilitators`, `lastNonce[facilitator]` is monotonically non-decreasing across `verify` calls.
- Once `_spent[h] == true`, it never reverts to `false`.
- A `verify` call that returns `true` always emits exactly one `ReceiptConsumed` event with matching fields.
- The contract holds no funds and has no `receive()`/`fallback()`.

## Security considerations

- **Trust root**: the safety of the entire x402-avm rail rests on the facilitator EOA's signing key. Compromise of that key allows the attacker to mint arbitrary receipts up to the nonce ceiling. Use a hardware-backed signer in production and a multisig-controlled `DEFAULT_ADMIN_ROLE`.
- **Replay**: double-protected — spent-hash set + monotonic nonce per facilitator. Defeating both requires the facilitator's key.
- **Signature malleability**: `ECDSA.recover` from OpenZeppelin rejects high-s signatures, so EIP-2 malleability is closed.
- **Reentrancy**: `verify` writes state before emitting the event but has no external calls. Safe to be called inside other `nonReentrant` flows (the registrars use it that way).
- **Front-running**: an attacker observing the receipt in mempool *cannot* re-submit because the receipt's `claimant` is fixed in the signature — the recovered signer changes if anyone tampers with any field.
- **Gas griefing**: an attacker holding `CONSUMER_ROLE` could spam invalid receipts; mitigated by the role being limited to three deployed registrars.
- **Key revocation flow**: when rotating a facilitator key, call `setFacilitator(oldKey, false)` then `setFacilitator(newKey, true)`. Don't reuse keys — the per-facilitator nonce is not reset.
- **Pause**: contract is not pausable. To halt x402 ingestion in an emergency, revoke `CONSUMER_ROLE` from all registrars (rolled back via `grantConsumer`).

## Integration patterns

- Registrars decode the `payment` byte payload, peel off the rail byte (`0x02` = x402-avm), `abi.decode` the remainder into an `X402Receipt`, and call `attestor.verify(r)`. The receipt is also referenced in the registrar's own `paymentReceiptHash` field and in `BankonPaymentRouter.recordReceipt` for the audit trail.
- See `BankonEthRegistrar.reveal` (lines 187-194) and `BankonDomainHosting.issue` (lines 138-147) for the canonical caller pattern.
- Grants done in [`script/DeployEthereum.s.sol`](../script/DeployEthereum.s.sol) lines 122-124.

## Known gotchas

- `verify(...)` is not idempotent — calling it twice on the same receipt reverts the second time with `ReceiptAlreadyConsumed`. Registrars must not call it in a try/catch that swallows the revert.
- `lastNonce[signer]` is keyed by **recovered signer**, not by facilitator allow-list slot. If a deactivated facilitator's key is later reactivated, the existing nonce state is preserved (deliberate). Don't try to "reset" by clearing storage; just rotate to a new EOA.
- EIP-712 domain includes `chainId` — receipts are not portable across chains, which is correct for an L1-anchored attestor.
- The receipt's `expiresAt` is in unix seconds, the same as `block.timestamp`. The facilitator must clock-sync with Ethereum block time; a 1-2 minute window is typical.

## See also

- [`interfaces/IBankonExtensions.md`](./interfaces/IBankonExtensions.md) — `IBankonX402Attestor` interface + `X402Receipt` struct.
- [`x402/X402Receipt.md`](./x402/X402Receipt.md) — companion on-chain receipt store (if present).
- [`BankonSubnameRegistrar.md`](./BankonSubnameRegistrar.md) — Flow A consumer.
- [`BankonEthRegistrar.md`](./BankonEthRegistrar.md) — Flow B consumer.
- [`BankonDomainHosting.md`](./BankonDomainHosting.md) — Flow C consumer.
- [`BankonPaymentRouter.md`](./BankonPaymentRouter.md) — companion L1 accounting record for the same receipt hash.
