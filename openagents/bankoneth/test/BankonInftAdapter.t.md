# BankonInftAdapter.t

> Unit suite for `BankonInftAdapter` — `RequestINFTMint` event shape, duplicate-bind protection, TBA-determinism property, wirer role gate.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`BankonInftAdapter.t.sol`](./BankonInftAdapter.t.sol) | **Suite:** `BankonInftAdapterTest`

## Role in bankoneth

Exercises [`contracts/BankonInftAdapter.sol`](../contracts/BankonInftAdapter.sol) — the Ethereum-side adapter that bridges subname-mint events to the 0G `iNFT_7857` contract. The adapter records the (labelhash → 0G tokenId) binding and computes deterministic ERC-6551 token-bound account addresses.

Four focused unit tests; **not** end-to-end (use [`BankonEndToEnd.t.sol`](./BankonEndToEnd.t.sol) for the full flow). Covers the request-mint event, the labelhash uniqueness invariant, TBA determinism, and the wirer access gate.

Flow coverage: **Flow A** unit-level slice (iNFT Mode A).

## Fixture (`setUp()`)

Mirrors [`BankonEndToEnd.t.sol`](./BankonEndToEnd.t.sol) — same chicken-and-egg pattern between resolver and adapter:

1. `vm.startPrank(admin)`.
2. `BankonSubnameResolver(admin, IBankonInftAdapter(address(0)))` — adapter-less.
3. `BankonInftAdapter(admin, IBankonSubnameResolver(resolver))` — adapter points at resolver.
4. `resolver.setInftAdapter(adapter)` — back-ref wired.
5. `adapter.setZeroGiNFTContract(ZEROG_INFT, ZEROG_CHAIN_ID)`.
6. `adapter.setErc6551Implementation(ERC6551_IMPL)`.
7. `adapter.grantRegistrar(registrar)`.
8. `adapter.grantWirer(wirer)`.
9. `vm.stopPrank()`.

Constants:
- `ERC6551_IMPL = 0x1111…1111`
- `ZEROG_INFT = 0x2222…2222`
- `ZEROG_CHAIN_ID = 16601`

EOAs: `admin`, `registrar`, `wirer`, `claimant`.

## Test inventory

| Test | What it asserts | Notable cheatcodes |
|---|---|---|
| `test_RequestMintEmits` | `registrar` calls `adapter.requestMint(parent, label=keccak256("alice"), claimant, tokenId=uint256(label), "ipfs://meta")`. Asserts `IBankonInftAdapter.RequestINFTMint(parent, label, claimant, uint256(label), "ipfs://meta")` event emits exactly. | `vm.prank(registrar)` + `vm.expectEmit(true,true,true,true,address(adapter))` |
| `test_RequestMintTwiceForSameLabelReverts` | After a successful `requestMint(label)` + `wirer.registerZeroGTokenId(label, 999)`, a second `requestMint(label, …)` with a fresh meta URI reverts with `BankonInftAdapter.LabelAlreadyBound(label)`. Validates the labelhash uniqueness guard *after* tokenId binding. | `vm.prank(registrar)` × 2 + `vm.prank(wirer)` + `vm.expectRevert(abi.encodeWithSelector(…, label))` |
| `test_TbaIsDeterministic` | `wirer.registerZeroGTokenId(keccak256("deterministic"), 1)` → TBA1. Then `wirer.registerZeroGTokenId(keccak256("other"), 1)` → TBA2. Asserts `TBA2 == TBA1` because TBA derivation depends only on `tokenId` (when `chainId` + `implementation` + `iNFTcontract` + `salt` are all constant). | `vm.prank(wirer)` × 2 |
| `test_NonWirerCannotRegister` | `claimant` (no role) calling `registerZeroGTokenId(keccak256("nope"), 1)` reverts (bare `vm.expectRevert()`). | `vm.prank(claimant)` + `vm.expectRevert()` |

## Coverage

**Covered:**
- `requestMint(bytes32,bytes32,address,uint256,string)` — happy path + duplicate guard.
- `registerZeroGTokenId(bytes32,uint256)` — happy path + access gate.
- `tbaAddressOf(bytes32)` view — determinism property.
- `zeroGTokenIdOf(bytes32)` view (used indirectly via the binding).
- `RequestINFTMint` event shape.
- Custom error: `LabelAlreadyBound(bytes32)`.

**Not covered:**
- `requestMint` access control for non-registrars (only the wirer access gate is tested).
- The `BankonSubnameResolver` flip semantics (`addr(node)` override) — that's in [`BankonEndToEnd.t.sol`](./BankonEndToEnd.t.sol).
- `setZeroGiNFTContract` / `setErc6551Implementation` admin paths (covered by setUp only).
- Direct interaction with the 0G iNFT — out of scope.
- Multi-binding edge cases (e.g., what if `chainId` or `implementation` rotate mid-flight).

## Notable patterns

- **TBA determinism as a property test**: rather than asserting an exact derived address (which would lock the test to a specific ERC-6551 CREATE2 algorithm), it asserts the *invariant* that two distinct labelhashes mapped to the same tokenId yield the same TBA. This survives any underlying derivation change as long as the property holds.
- **Duplicate-bind protection sequencing**: the test must first call `registerZeroGTokenId` before the second `requestMint` triggers `LabelAlreadyBound` — the guard checks the bound `tokenId != 0` slot, so an un-registered request leaves the slot zero and is replayable. This is documented inline.

## Known caveats

- `test_NonWirerCannotRegister` uses bare `vm.expectRevert()` — won't distinguish access-control reverts from any other revert.
- `ZEROG_INFT` and `ERC6551_IMPL` are EOAs with no bytecode; the test never deploys real ERC-6551 implementation, so `tbaAddressOf` only proves the *deterministic-derivation* property, not that anyone can actually deploy a TBA at that address.
- The "labelhash uniqueness after binding only" semantic is subtle and easy to regress — if the guard were tightened to forbid `requestMint` reruns *before* binding, this test would still pass. A negative test for that case is absent.
- `RequestINFTMint`'s `tokenId` field is set by the registrar in `requestMint` — the test passes `uint256(label)` but real production may use a different value (the wirer then binds an actual 0G tokenId via `registerZeroGTokenId`).

## How to run

```bash
forge test --match-path test/BankonInftAdapter.t.sol -vvv
```

## See also

- [`../contracts/BankonInftAdapter.sol`](../contracts/BankonInftAdapter.sol) — system under test.
- [`../contracts/BankonSubnameResolver.sol`](../contracts/BankonSubnameResolver.sol) — paired resolver.
- [`BankonEndToEnd.t.sol`](./BankonEndToEnd.t.sol) — exercises the adapter in full Mode-A flow.
- `docs/INFT_MODE_A.md` — architecture: TBA derivation, cross-chain pointer.
- `docs/FLOWS.md` — Flow A definition.
