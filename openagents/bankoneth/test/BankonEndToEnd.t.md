# BankonEndToEnd.t

> Light end-to-end suite focusing on iNFT Mode A: subname mint → `BankonInftAdapter` receives → `RequestINFTMint` emitted → simulated wirer registers 0G tokenId → resolver `addr(node)` flips from claimant to TBA.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`BankonEndToEnd.t.sol`](./BankonEndToEnd.t.sol) | **Suite:** `BankonEndToEndTest`

## Role in bankoneth

This file is the **smoke-level** end-to-end for the new bankoneth-specific contracts (`BankonInftAdapter` + `BankonSubnameResolver` + `BankonAgenticPlaceHook`). It deliberately does NOT exercise the `BankonSubnameRegistrar` Flow A pipeline — that has its own comprehensive 34-test suite in [`BankonSubnameRegistrar.t.sol`](./BankonSubnameRegistrar.t.sol).

The two tests here cover the iNFT-Mode-A invariant: after a 0G tokenId is registered for a labelhash, the resolver's `addr(node)` view must transparently return the deterministic ERC-6551 TBA address instead of the raw claimant address.

Flow coverage: **Flow A** (iNFT Mode A) + **Flow C** (AgenticPlace listing emission).

## Fixture (`setUp()`)

All deploys happen inside a single `vm.startPrank(admin) … vm.stopPrank()` block:

1. `BankonSubnameResolver(admin, IBankonInftAdapter(address(0)))` — adapter-less shell first.
2. `BankonInftAdapter(admin, IBankonSubnameResolver(resolver))` — adapter points back at the live resolver.
3. `resolver.setInftAdapter(adapter)` — closes the back-reference.
4. `adapter.setZeroGiNFTContract(ZEROG_INFT, ZEROG_CHAIN_ID)` — cross-chain pointer to fake 0G iNFT.
5. `adapter.setErc6551Implementation(ERC6551_IMPL)` — required for deterministic TBA derivation.
6. `adapter.grantRegistrar(registrar)` — `registrar` EOA can call `requestMint`.
7. `adapter.grantWirer(wirer)` — `wirer` EOA can call `registerZeroGTokenId`.
8. `resolver.grantRegistrar(registrar)` — `registrar` can write resolver records.
9. `BankonX402Attestor(admin)`.
10. `BankonAgenticPlaceHook(admin, "https://agenticplace.pythai.net/api/listings")`.
11. `hook.grantLister(registrar)` — `registrar` can emit listings.

Constants:
- `PARENT_NODE = bytes32(uint256(0xba17_001e))`
- `LABEL_HASH = keccak256("alice")`
- `SUBNAME_NODE = keccak256(abi.encodePacked(PARENT_NODE, LABEL_HASH))`
- `ERC6551_IMPL = 0x1111…1111`
- `ZEROG_INFT = 0x2222…2222`
- `ZEROG_CHAIN_ID = 16601` (0G Galileo)

EOAs: `admin`, `registrar` (simulated registrar caller), `wirer` (off-chain 0G-side worker), `claimant` (the human/agent receiving the subname).

## Test inventory

| Test | What it asserts | Notable cheatcodes |
|---|---|---|
| `test_INFTModeA_HappyPath` | Full Mode-A chain: (1) registrar calls `resolver.setAddr(SUBNAME_NODE, claimant)` → `resolver.addr(...) == claimant`. (2) registrar calls `adapter.requestMint(parent, label, claimant, uint256(label), "ipfs://alice-meta")`. (3) wirer calls `adapter.registerZeroGTokenId(label, 0xc0de)` → asserts `adapter.zeroGTokenIdOf(label) == 0xc0de`. Asserts `adapter.tbaAddressOf(label) != address(0)`. (4) registrar calls `resolver.setINFTBinding(SUBNAME_NODE, tba, 0xc0de)`. (5) **invariant**: `resolver.addr(SUBNAME_NODE) == tba` — the addr-resolver override is in effect. | `vm.prank(registrar)` × 3 + `vm.prank(wirer)` |
| `test_AgenticPlaceListingEmitted` | After `requestMint` + `registerZeroGTokenId(tokenId=7)`, registrar calls `hook.list(PARENT_NODE, LABEL_HASH, tba, 7, "ipfs://m", claimant)`. Asserts `IBankonAgenticPlaceHook.AgenticPlaceListing(...)` event emits with full payload. | `vm.prank(registrar)` + `vm.expectEmit(true,true,true,true,address(hook))` |

## Coverage

**Covered:**
- `BankonSubnameResolver.setAddr / addr / setINFTBinding` happy paths.
- `BankonInftAdapter.requestMint / registerZeroGTokenId / zeroGTokenIdOf / tbaAddressOf` happy paths.
- `BankonAgenticPlaceHook.list` event shape (also covered in [`BankonAgenticPlaceHook.t.sol`](./BankonAgenticPlaceHook.t.sol)).
- The cross-contract back-reference plumbing (`resolver.setInftAdapter(adapter)` → `addr()` consults adapter).

**Not covered:**
- Reverts on wrong roles, duplicate bindings (covered by [`BankonInftAdapter.t.sol`](./BankonInftAdapter.t.sol)).
- `BankonX402Attestor` paths — deployed but unused.
- The actual `iNFT_7857` contract on 0G — out of scope; only the Ethereum-side pointer is exercised.
- Subname mint via `BankonSubnameRegistrar` — covered by [`BankonSubnameRegistrar.t.sol`](./BankonSubnameRegistrar.t.sol).
- Mainnet ENS `NameWrapper` interaction — no wrapper is deployed; the test treats the subname mint as already-done and only exercises post-mint resolver state.

## Notable patterns

- **Adapter ⇄ resolver chicken-and-egg**: the script deploy mirror in [`script/DeployEthereum.s.sol`](../script/DeployEthereum.s.sol) — resolver is constructed with `address(0)` adapter, adapter constructed with live resolver, then `setInftAdapter` patches. Same pattern here.
- **Mode-A invariant**: the resolver's `addr(node)` semantics are overridden once `setINFTBinding(node, tba, tokenId)` is called. This is the on-chain proof that an agent's wallet has migrated from a raw EOA to a token-bound account whose ownership is sovereign on 0G.
- **No `NameWrapper` mock** — the test deliberately skips ENS subnode creation, jumping straight to resolver records. The premise is that `BankonSubnameRegistrar` has minted the subname elsewhere; this file owns the post-mint resolver/iNFT chain.

## Known caveats

- The test simulates the off-chain wirer with a granted-role EOA — production has the wirer monitoring 0G iNFT mint events and proving them back via signed receipts, none of which is exercised here.
- `ERC6551_IMPL` and `ZEROG_INFT` are arbitrary addresses with no bytecode — `tbaAddressOf` returns a CREATE2-derived address that depends on the constants, but no actual TBA contract is deployed at that address. Tests only assert the derivation is non-zero and deterministic.
- `requestMint`'s `tokenId` argument is `uint256(LABEL_HASH)` here — production may set this differently; the test only requires consistency with the later `registerZeroGTokenId` call (and notably uses `0xc0de` as the actually-registered tokenId, not `uint256(LABEL_HASH)`, suggesting the labelhash-as-tokenId is just a placeholder).
- `MockNameWrapper` is not used; mainnet wrapper interactions aren't exercised.

## How to run

```bash
forge test --match-path test/BankonEndToEnd.t.sol -vvv
```

## See also

- [`BankonInftAdapter.t.sol`](./BankonInftAdapter.t.sol) — unit-level coverage of the adapter.
- [`BankonAgenticPlaceHook.t.sol`](./BankonAgenticPlaceHook.t.sol) — focused hook tests.
- [`BankonSubnameRegistrar.t.sol`](./BankonSubnameRegistrar.t.sol) — Flow A exhaustive coverage.
- [`../contracts/BankonInftAdapter.sol`](../contracts/BankonInftAdapter.sol).
- [`../contracts/BankonSubnameResolver.sol`](../contracts/BankonSubnameResolver.sol).
- `docs/INFT_MODE_A.md` — architecture explanation.
- `docs/FLOWS.md` — Flow A + Flow C definitions.
