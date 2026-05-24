# X402Receipt

> Canonical on-chain attestation contract for HTTP 402 (x402) stablecoin payment receipts — verifies an EOA-or-ERC-1271 signature, enforces idempotency, emits a cross-chain-indexable event, and optionally cascades to `BankonPaymentRouter` for split accounting.

**SPDX:** MIT | **Pragma:** ^0.8.24 | **Source:** [`X402Receipt.sol`](./X402Receipt.sol)

## Role in bankoneth

`X402Receipt` is the EVM-side attestation layer for the **x402 protocol** — HTTP-native stablecoin payments where a resource server returns HTTP 402, the client pays via ERC-20 `transferWithAuthorization` (USDC EIP-3009), and a *receipt* is generated that both sides sign and anchor on chain for non-repudiation. This contract is one of the artifacts re-homed from `DAIO/` into the bankoneth tree.

It is **explicitly the attestation layer, not the settlement layer**. The token transfer itself has already happened via the facilitator's `transferWithAuthorization` call before this contract is invoked. What this contract does:

1. Verifies a signature over the receipt struct, supporting **both EOA (ECDSA) and multisig (ERC-1271 / Safe)** via OpenZeppelin's `SignatureChecker`.
2. Enforces **idempotency**: a `receiptHash` can only be recorded once across the contract's lifetime.
3. Emits a **flat indexable event** designed to be ABI-compatible with the Algorand counterpart at `daio/contracts/algorand/x402_receipt.algo.ts` — same field set, same event shape, so a unified indexer joins both chains by `(chainKind, chainId, receiptHash)` triples.
4. **Optionally cascades** to `IBankonPaymentRouter.recordReceipt(...)` if a router was wired at deploy time. This is the bridge from raw x402 events into BANKON's USDC/PYTHAI/ETH revenue split.

What this contract does **NOT** do:
- Move tokens. Settlement is the ERC-20 `transferWithAuthorization` already executed by the facilitator.
- Validate the economic content of the receipt struct. The signature is the trust boundary — the payer asserts these values are correct by signing them.

The Algorand pairing (`daio/contracts/algorand/x402_receipt.algo.ts`) exposes the same ABI signature and emits a structurally equivalent log; cross-chain indexers can join by `receiptHash`. (Note: the hashes themselves are NOT bit-identical across chains because EVM uses `keccak256(abi.encode(...))` while AVM uses `sha256` over a different encoding. The shared key is the receiptHash *per chain*.)

## Inheritance

```
X402Receipt
 └─ AccessControl                          (OZ; reserved for future admin paths)
        ↑ uses
   SignatureChecker                        (OZ; EOA + ERC-1271 dispatch)
   MessageHashUtils                        (OZ; EIP-191 prefix)
        ↓ depends on
   IBankonPaymentRouter                    (../interfaces/IBankon.sol)
```

Note: `AccessControl` is inherited but only `DEFAULT_ADMIN_ROLE` is wired up at construction. The contract currently has no role-gated functions besides what AccessControl exposes for grant/revoke. Future admin paths (pause, router rotation, signer-allow-list) would slot in here.

## Constructor

| arg | type | purpose |
| --- | --- | --- |
| `admin` | `address` | Receives `DEFAULT_ADMIN_ROLE` |
| `router_` | `IBankonPaymentRouter` | Optional downstream router; `address(0)` = no cascade |

`router` is **immutable** — it cannot be rotated. Operators wanting to switch routers must redeploy this contract. (This is a deliberate trust-minimization: the router is part of the deployed identity.)

If `router != 0x0`, the **operator must post-deploy grant `REGISTRAR_ROLE` on the router to this contract's address**. Without that grant, the cascade `router.recordReceipt(...)` would revert and `recordX402Receipt` would fail for every receipt. The router connection is configured at deploy but activated by a separate role grant on the *router* contract.

## Storage layout

| slot | type | description |
| --- | --- | --- |
| `router` | `IBankonPaymentRouter` (public, **immutable**) | Optional cascade target. Set at construction; cannot be changed |
| `seenReceipt` | `mapping(bytes32 => bool)` (public) | Anti-replay: `receiptHash → already-recorded` |

## Roles

| Role | keccak256 | Who holds | What they can do |
| --- | --- | --- | --- |
| `DEFAULT_ADMIN_ROLE` | OZ default | Constructor `admin` | Grant/revoke roles (no role-gated functions defined yet on this contract) |

No `REGISTRAR_ROLE` or similar is defined *on this contract*; the `REGISTRAR_ROLE` mentioned in code comments refers to the role on the *router*, not here.

## Events

| Event | When emitted | Indexer / UI use |
| --- | --- | --- |
| `X402ReceiptRecorded(bytes32 indexed receiptHash, bytes32 indexed resourceHash, address payer, address payee, address asset, uint256 amount, uint64 chainId, uint64 blockNumber)` | Inside `recordX402Receipt` AFTER signature verification AND seenReceipt mark, BEFORE the optional router cascade | Primary cross-chain indexable event; matches the AVM counterpart's log shape. `chainId` lets a single indexer dedupe across EVMs |

`chainId` is captured as `uint64(block.chainid)` and `blockNumber` as `uint64(block.number)` for tight packing. The truncation is safe for the foreseeable future (block.chainid fits in 64 bits for every known chain; block.number won't approach 2^64 in any plausible timeline).

## Errors

| Error | When reverted |
| --- | --- |
| `ReceiptAlreadyRecorded(bytes32 receiptHash)` | The hash is already in `seenReceipt` |
| `ReceiptHashMismatch(bytes32 expected, bytes32 computed)` | Caller-supplied `receiptHash` does not equal `canonicalReceiptHash(...)` of the same fields. Guards against malformed clients |
| `InvalidSignature()` | `SignatureChecker.isValidSignatureNow(payer, digest, signature) == false`. Covers both EOA recovery failure and ERC-1271 contract returning ≠ magic-value |
| `ZeroPayer()` | `payer == address(0)` |

## External / public API

### `canonicalReceiptHash(address payer, address payee, address asset, uint256 amount, bytes32 resourceHash, bytes32 nonce) public view → bytes32`
- **Access**: Open, pure-ish (depends only on `block.chainid` from EVM context).
- **Behaviour**: Returns `keccak256(abi.encode(bytes32("x402-receipt-v1"), block.chainid, payer, payee, asset, amount, resourceHash, nonce))`. Use this off-chain to pre-compute the hash you'll later pass to `recordX402Receipt`.
- **Encoding**: `abi.encode` (not `encodePacked`) — unambiguous and forge-friendly. The leading version tag (`"x402-receipt-v1"`) protects against future-version replay across redeploys.

### `recordX402Receipt(bytes32 receiptHash, address payer, address payee, address asset, uint256 amount, bytes32 resourceHash, bytes32 nonce, bytes calldata signature)`
- **Access**: Open (anyone can submit — the trust boundary is the signature).
- **Behaviour**:
  1. Revert `ZeroPayer` if `payer == 0x0`.
  2. Revert `ReceiptAlreadyRecorded` if already seen.
  3. Recompute `expected = canonicalReceiptHash(...)` and revert `ReceiptHashMismatch` if mismatched.
  4. Compute the EIP-191 `personal_sign` digest: `receiptHash.toEthSignedMessageHash()`.
  5. Verify via `SignatureChecker.isValidSignatureNow(payer, digest, signature)` — handles EOA (ECDSA recover) and ERC-1271 contract callback uniformly. Revert `InvalidSignature` on failure.
  6. Mark `seenReceipt[receiptHash] = true`.
  7. Emit `X402ReceiptRecorded(...)`.
  8. If `router != 0x0`, call `router.recordReceipt(receiptHash, amount, asset)`. The router enforces its own anti-replay (independent mapping). **`amount` is the asset's base units (USDC = 6 dp)**; non-USDC rails need a wrapper that converts before cascading.
- **Why `personal_sign` and not EIP-712**: lets wallets sign with the everyday wallet API rather than needing typed-data infra. The leading version-tag inside the abi-encoded hash provides the same domain separation that EIP-712 would.

### Inherited from AccessControl
`hasRole`, `getRoleAdmin`, `grantRole`, `revokeRole`, `renounceRole`, etc.

## Internal helpers

None defined locally; logic is small enough that all of it lives in the public functions.

## Invariants

1. **One-shot per receiptHash**: `seenReceipt[hash]` is monotonic. The same `receiptHash` can never be recorded twice across the contract's lifetime, regardless of how many distinct clients submit it.
2. **Hash binds chain**: `block.chainid` is in the encoding, so a signature valid on chain A is not valid on chain B (no cross-chain replay).
3. **Hash binds version**: `bytes32("x402-receipt-v1")` is in the encoding, so a future v2 format cannot collide with v1.
4. **Router is immutable**: once set at construction, `router` cannot be rotated. Operators wanting a different cascade target must redeploy.
5. **Caller can submit on behalf of payer**: anyone holding a valid signature from `payer` can record. The submitter pays gas; the payer's signature is the authority.

## Security considerations

- **Trust boundary is the signature**: this contract does not validate that `amount` matches an actual ERC-20 transfer, that `asset` is even a real token, or that `payee` ever received funds. The payer asserts these values by signing. A misbehaving payer can sign garbage; downstream consumers (router, indexers) must verify economic content independently.
- **`recordReceipt` cascade trust**: the router executes immediately after `seenReceipt[hash] = true`. A reverting router blocks recording — there is no graceful degradation. If the router's `REGISTRAR_ROLE` is not granted to this contract, every `recordX402Receipt` call fails. This is recoverable only by granting the role on the router.
- **No reentrancy guard**: not needed for this surface — `seenReceipt[hash] = true` is set BEFORE the external `router.recordReceipt` call, so a malicious router cannot cause double-record. Event emission is also pre-call. The router is the only external interaction.
- **ERC-1271 callback gas**: `SignatureChecker.isValidSignatureNow` invokes the payer contract's `isValidSignature` when `payer` is a contract. A poorly-written ERC-1271 implementation could burn a lot of gas. Submitters should over-provide gas when paying for Safe / multisig.
- **`personal_sign` vs `EIP-712`**: this contract uses EIP-191. That means wallets can sign with `eth_sign` / `personal_sign` directly. Hardware-wallet-only `eth_signTypedData` flows are NOT how this is signed — different signing UX, but cryptographically equivalent given the version tag inside the hash.
- **Truncating chainId / blockNumber to `uint64`**: safe for any realistic chain; not safe if a chain ever exposes a chainid > 2^64-1 (none do).
- **No admin pause / emergency stop**: the contract cannot be paused. Once deployed, every valid signature records. Operators wanting kill-switch behaviour must redeploy.
- **Front-running**: a watcher who sees a `(receiptHash, signature)` tuple in mempool can submit it themselves and pay gas. This denies the original submitter their gas refund pattern, but does not break correctness — the receipt is still recorded against `payer`. No financial impact.
- **`amount` decimals depend on `asset`**: cascading `amount` directly to the router assumes USDC (6 dp). Wrapping required for non-USDC rails — see the `recordReceipt` cascade comment.

## Integration patterns

**Off-chain hash construction (TypeScript pseudo):**
```ts
const receiptHash = await x402.canonicalReceiptHash(
    payer, payee, USDC_ADDRESS, amount6dp, resourceHashKeccak, randomNonce
);
const digest = ethers.hashMessage(ethers.getBytes(receiptHash));   // EIP-191 prefix
const signature = await payerWallet.signMessage(ethers.getBytes(receiptHash));
await x402.recordX402Receipt(
    receiptHash, payer, payee, USDC_ADDRESS, amount6dp,
    resourceHashKeccak, randomNonce, signature
);
```

**Multisig (Safe) signer flow:**
```ts
// 1. Safe owners individually sign the digest.
// 2. Concatenate signatures per Safe's signature format.
// 3. Submit to recordX402Receipt; SignatureChecker invokes Safe.isValidSignature(digest, sigs).
```

**Wiring the router (post-deploy):**
```solidity
// Constructor: deploy with router
X402Receipt x402 = new X402Receipt(admin, IBankonPaymentRouter(routerAddr));
// On the router (separate contract), grant the registrar role:
router.grantRole(router.REGISTRAR_ROLE(), address(x402));
```

**Reading historical receipts:**
```solidity
bool wasRecorded = x402.seenReceipt(receiptHash);
// Full struct lives in the event log; query via getLogs(X402ReceiptRecorded).
```

## Known gotchas

- **`router` is immutable** — set at construction, set forever. Redeploy required to rotate.
- **The router needs `REGISTRAR_ROLE` granted to this contract's address** — not the deployer, not the admin, *this contract*. Without it, every record reverts.
- **Receipt-hash domain includes `block.chainid` AND the version tag `"x402-receipt-v1"`** — both must match across producer and verifier or the receipt rejects.
- **No `nonReentrant`** — intentionally; state is checkpointed before external call.
- **`canonicalReceiptHash` is `view`, not `pure`** — depends on `block.chainid`. Don't expect deterministic output across forks.
- **EOA OR ERC-1271** via `SignatureChecker`. There's no separate path for the two — submitters don't need to know which one `payer` is.
- **`payee` is informational** in this contract — does not authorize, does not gate the cascade. Off-chain consumers correlate `payee` with the actual settlement via `transferWithAuthorization` events.
- **`amount` is asset-relative base units** — passing wei when `asset` expects 18-dp confuses indexers but does not revert.

## See also

- [`IBankon.sol`](../interfaces/IBankon.sol) — defines `IBankonPaymentRouter` (the cascade target)
- `daio/contracts/algorand/x402_receipt.algo.ts` — Algorand counterpart, same field set, same event shape
- EIP-3009 — `transferWithAuthorization` (the actual settlement primitive)
- EIP-191 — `personal_sign` digest format
- ERC-1271 — Standard Signature Validation Method for Contracts
- OpenZeppelin `SignatureChecker` — the EOA + ERC-1271 unifying primitive
- `BankonPaymentRouter` (concrete implementation outside this tree) — the cascade target
