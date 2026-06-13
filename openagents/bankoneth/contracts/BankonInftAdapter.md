# BankonInftAdapter

> Mode A iNFT glue — receives wrapped ENS subnames, emits 0G-side mint requests, and binds (labelhash → 0G tokenId, ERC-6551 TBA) for the resolver to override.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`BankonInftAdapter.sol`](./BankonInftAdapter.sol)

## Role in bankoneth

`BankonInftAdapter` is the **unified-mode** bridge between Ethereum ENS NameWrapper subnames and 0G-hosted ERC-7857 iNFTs. The flow:

1. A registrar (Flow A `BankonSubnameRegistrar`) mints an ENS subname and (optionally) calls `requestMint(...)` on this adapter.
2. The adapter emits `RequestINFTMint(parentNode, labelhash, claimant, erc1155TokenId, metadataURI)`.
3. An off-chain 0G-side worker watches the event, mints the ERC-7857 on 0G (the AI-native chain with TEE attestation), derives the deterministic ERC-6551 TBA address, and calls `registerZeroGTokenId(labelhash, zeroGTokenId)` back on this adapter.
4. The adapter computes the ERC-6551 TBA via the singleton registry CREATE2 derivation, stores the binding, and emits `INFTBound`.
5. The resolver's `addr(node)` now overrides to the TBA when the adapter (or registrar) calls `BankonSubnameResolver.setINFTBinding(node, tba, tokenId)`.

The adapter is `ERC1155Holder` because NameWrapper subnames are ERC-1155 tokens — they can be transferred into this contract as collateral when the iNFT is meant to be unified-mode (subname custody locked to the iNFT). Until a real cross-chain bridge lands, the (labelhash → tokenId, TBA) registry is **operator-attested** via `WIRER_ROLE`.

## Inheritance

- `IBankonInftAdapter` — public interface in [`interfaces/IBankonExtensions.sol`](./interfaces/IBankonExtensions.sol).
- `ERC1155Holder` — accepts ERC-1155 subname transfers from NameWrapper (`onERC1155Received` hook).
- `AccessControl` — `DEFAULT_ADMIN_ROLE`, `REGISTRAR_ROLE` (mint requests), `WIRER_ROLE` (cross-chain bindings).

## Constructor

| arg         | type                       | purpose                                                       |
|-------------|----------------------------|---------------------------------------------------------------|
| `admin`     | `address`                  | Granted `DEFAULT_ADMIN_ROLE`.                                 |
| `_resolver` | `IBankonSubnameResolver`   | Initial resolver binding (used downstream for `setINFTBinding`).|

Roles granted at construction: `DEFAULT_ADMIN_ROLE` → `admin`.

## Storage layout

| name                      | type                              | purpose                                                                            | mutable? |
|---------------------------|-----------------------------------|------------------------------------------------------------------------------------|----------|
| `REGISTRAR_ROLE`          | `bytes32 constant`                | `keccak256("REGISTRAR_ROLE")`.                                                     | no       |
| `WIRER_ROLE`              | `bytes32 constant`                | `keccak256("WIRER_ROLE")`.                                                         | no       |
| `ERC6551_REGISTRY`        | `address constant`                | `0x000000006551c19487814612e58FE06813775758` (canonical singleton).                | no       |
| `resolver`                | `IBankonSubnameResolver` public   | Bound resolver — informational; the resolver does not callback during reads.       | yes (admin)|
| `agenticPlaceHook`        | `IBankonAgenticPlaceHook` public  | Optional listing hook for marketplace announcements.                               | yes (admin)|
| `zeroGiNFTContract`       | `address` public                  | The ERC-7857 contract address on 0G (set post-deploy).                             | yes (admin)|
| `zeroGChainId`            | `uint256` public                  | 0G chain id (used in `_computeTba`).                                               | yes (admin)|
| `erc6551Implementation`   | `address` public                  | ERC-6551 account contract implementation address.                                  | yes (admin)|
| `_tokenIdOf`              | `mapping(bytes32 => uint256)` private | labelhash → 0G iNFT tokenId.                                                   | yes (wirer)|
| `_tbaOf`                  | `mapping(bytes32 => address)` private | labelhash → derived TBA address on the iNFT chain.                              | yes (wirer)|

## Roles

| Role                 | keccak256                              | Who holds                                                       | What they can do                                              |
|----------------------|----------------------------------------|------------------------------------------------------------------|----------------------------------------------------------------|
| `DEFAULT_ADMIN_ROLE` | OpenZeppelin default                   | `admin` (constructor)                                            | All `set*` admin functions + role mgmt.                       |
| `REGISTRAR_ROLE`     | `keccak256("REGISTRAR_ROLE")`          | `BankonSubnameRegistrar` (granted by deploy script line 118)     | Call `requestMint(...)` to emit `RequestINFTMint`.            |
| `WIRER_ROLE`         | `keccak256("WIRER_ROLE")`              | Operator wirer EOA (off-chain 0G-side worker; granted post-deploy by admin) | Call `registerZeroGTokenId(...)` to bind labelhash → tokenId.|

## Events

### `RequestINFTMint(bytes32 indexed parentNode, bytes32 indexed labelhash, address indexed claimant, uint256 erc1155TokenId, string metadataURI)` (from interface)

Emitted by `requestMint`. Off-chain 0G worker watches this and mints the ERC-7857.

### `INFTBound(bytes32 indexed labelhash, uint256 indexed zeroGTokenId, address indexed tbaAddress)` (from interface)

Emitted by `registerZeroGTokenId` after computing the deterministic TBA. The marketplace listing emitted via `BankonAgenticPlaceHook.list(...)` should reference the same `tbaAddress`.

### `ZeroGiNFTContractUpdated(address indexed contractAddr, uint256 chainId)`

Emitted on `setZeroGiNFTContract`.

### `Erc6551ImplementationUpdated(address indexed implementation)`

Emitted on `setErc6551Implementation`.

### `ResolverUpdated(address indexed resolver)`

Emitted on `setResolver`.

### `AgenticPlaceHookUpdated(address indexed hook)`

Emitted on `setAgenticPlaceHook`.

## Errors

### `LabelAlreadyBound(bytes32 labelhash)`

Reverted by `requestMint` when `_tokenIdOf[labelhash] != 0` — the label already has a registered 0G tokenId. (Note: this also means tokenId `0` cannot be represented as "bound"; the 0G mint should start from id 1.)

### `LabelUnbound(bytes32 labelhash)`

Declared but **not used** in the current implementation — reserved for future "unbind" / "must be bound first" paths.

### `ZeroGiNFTContractUnset()`

Reverted by `requestMint` and `registerZeroGTokenId` when `zeroGiNFTContract == address(0)`. Admin must call `setZeroGiNFTContract` first.

### `Erc6551ImplementationUnset()`

Reverted by `requestMint` and `registerZeroGTokenId` when `erc6551Implementation == address(0)`. Admin must call `setErc6551Implementation` first.

## External / public API

### `setZeroGiNFTContract(address contractAddr, uint256 chainId) external`

Sets the 0G ERC-7857 contract address and the chain id used in TBA derivation. Access: `DEFAULT_ADMIN_ROLE`. Emits `ZeroGiNFTContractUpdated`.

### `setErc6551Implementation(address implementation) external`

Sets the ERC-6551 account implementation contract used to derive TBA addresses. Access: `DEFAULT_ADMIN_ROLE`. Emits `Erc6551ImplementationUpdated`.

### `setResolver(IBankonSubnameResolver newResolver) external`

Rebinds the local resolver reference. Access: `DEFAULT_ADMIN_ROLE`. Emits `ResolverUpdated`.

### `setAgenticPlaceHook(IBankonAgenticPlaceHook newHook) external`

Rebinds the marketplace hook reference. Access: `DEFAULT_ADMIN_ROLE`. Emits `AgenticPlaceHookUpdated`.

### `grantRegistrar(address registrar) external`

Grants `REGISTRAR_ROLE`. Access: `DEFAULT_ADMIN_ROLE`.

### `grantWirer(address wirer) external`

Grants `WIRER_ROLE`. Access: `DEFAULT_ADMIN_ROLE`. The off-chain 0G worker EOA gets this.

### `requestMint(bytes32 parentNode, bytes32 labelhash, address claimant, uint256 erc1155TokenId, string calldata metadataURI) external`

Validates the label is not already bound and the iNFT/ERC-6551 implementation addresses are set, then emits `RequestINFTMint`. Access: `REGISTRAR_ROLE`. **Pure event emitter — no state mutation.**

### `registerZeroGTokenId(bytes32 labelhash, uint256 zeroGTokenId) external`

Stores the cross-chain binding: `_tokenIdOf[labelhash] = zeroGTokenId`, computes the TBA via `_computeTba(zeroGTokenId)`, stores it in `_tbaOf[labelhash]`, and emits `INFTBound`. Access: `WIRER_ROLE`. Reverts if either configuration address is unset.

### `zeroGTokenIdOf(bytes32 labelhash) external view returns (uint256)`

Returns the bound 0G tokenId for a labelhash. Returns `0` if unbound.

### `tbaAddressOf(bytes32 labelhash) external view returns (address)`

Returns the derived TBA address. Returns `address(0)` if unbound.

### `supportsInterface(bytes4 interfaceId) public view returns (bool)`

ERC-165 — advertises `IBankonInftAdapter` plus `AccessControl` and `ERC1155Holder` (the inherited surfaces).

## Internal helpers

### `_computeTba(uint256 tokenId) internal view returns (address)`

Reimplements the ERC-6551 singleton registry's CREATE2 derivation **off the canonical registry's helper** to avoid an external call:
- Constructs the standard minimal-proxy creation code with `erc6551Implementation` baked in.
- Hashes `(salt=0, zeroGChainId, zeroGiNFTContract, tokenId)`.
- CREATE2 address = `keccak256(0xff || ERC6551_REGISTRY || salt || keccak256(creationCode || data))[12:]`.

Inline comment notes: "For real deployment we'd call `ERC6551Registry.account(...)` instead." The local computation is a hackathon-ship simplification — the canonical helper costs one extra cross-contract call but is the authoritative source.

## Invariants

- For each `labelhash`, `_tokenIdOf[labelhash]` is set at most once via `registerZeroGTokenId` (subsequent calls revert `LabelAlreadyBound`).
- `_tbaOf[labelhash] != address(0)` iff `_tokenIdOf[labelhash] != 0` (because both are set in the same call).
- `ERC6551_REGISTRY` is fixed at `0x000000006551c19487814612e58FE06813775758` — same on every EVM chain.
- Holds ERC-1155 subnames if they are transferred to it; does not actively pull them.
- No native funds; no `receive()`.

## Security considerations

- **TBA derivation drift**: `_computeTba` uses an inlined creation-code template. If the ERC-6551 reference implementation changes, this derivation breaks. **Production should call `ERC6551Registry.account(...)` directly** to be future-proof.
- **Operator-attested wiring**: `WIRER_ROLE` is the trust root for the cross-chain binding. A malicious wirer can bind any labelhash to a tokenId of their choice — and the resolver will start routing `addr(node)` to that TBA. Use a multisig or a hardware-attested EOA.
- **Single binding**: `LabelAlreadyBound` prevents rebinding. To migrate, you would need a new method (not currently exposed) or a redeploy with state replay.
- **Resolver wiring**: this adapter never calls `setINFTBinding` on the resolver itself — that's done by a separate call (currently by registrar logic or by an off-chain script). Make sure your wiring scripts include the `setINFTBinding` step or the resolver override won't activate.
- **ERC1155Holder**: accepts ALL ERC-1155 transfers from any contract. If accidentally sent NFTs from unrelated collections, they're stuck unless an admin-rescue method is added (not currently present).
- **`zeroGiNFTContract` and `erc6551Implementation` unset**: hardened — both `requestMint` and `registerZeroGTokenId` revert with explicit errors. Wirer cannot create bogus zero-address TBAs.
- **TokenId=0 representation gap**: the `_tokenIdOf != 0` check used as "bound" sentinel means tokenId 0 cannot mark "bound". The 0G ERC-7857 must mint from id ≥ 1.
- **No reentrancy**: no external calls in state-mutating paths.

## Integration patterns

- `BankonSubnameRegistrar` is expected to call `inftAdapter.requestMint(...)` after mint to trigger the off-chain 0G mint. (Current registrar code does not invoke this directly — wiring happens via off-chain orchestration consuming `SubnameRegistered`.)
- Off-chain 0G worker pseudo-code:
  ```
  on RequestINFTMint(parent, labelhash, claimant, erc1155Id, uri):
      tokenId = zeroGContract.mint(claimant, uri)
      adapter.registerZeroGTokenId(labelhash, tokenId)   # signs as WIRER
      node = keccak256(parent || labelhash)
      resolver.setINFTBinding(node, adapter.tbaAddressOf(labelhash), tokenId)
      agenticPlaceHook.list(parent, labelhash, tba, tokenId, uri, claimant)
  ```
- Deployed via [`script/DeployEthereum.s.sol`](../script/DeployEthereum.s.sol) line 82, then `grantRegistrar(d.subnameRegistrar)` line 118.

## Known gotchas

- `_computeTba` will return a meaningless address if `zeroGiNFTContract` or `erc6551Implementation` is wrong. Both guards revert before storage write but **read-only** queries of `tbaAddressOf` for an already-bound label after later changing implementation will still return the stale value.
- The adapter does NOT call the resolver's `setINFTBinding`; the wiring lives in the off-chain orchestrator. If you observe `INFTBound` but `addr(node)` still returns the EOA, the off-chain script missed the resolver call.
- `LabelUnbound` error is declared but unused — present for future API expansion. Don't rely on it.
- `setZeroGiNFTContract` does NOT validate the address is a contract or that it implements ERC-7857. Operator must double-check.
- `agenticPlaceHook` is settable but never called from this contract — it's wired here only for off-chain consumers reading the adapter's storage.

## See also

- [`interfaces/IBankonExtensions.md`](./interfaces/IBankonExtensions.md) — `IBankonInftAdapter` interface + events.
- [`BankonSubnameResolver.md`](./BankonSubnameResolver.md) — consumes the `tbaAddress` via `setINFTBinding`.
- [`BankonSubnameRegistrar.md`](./BankonSubnameRegistrar.md) — expected to call `requestMint`.
- [`BankonAgenticPlaceHook.md`](./BankonAgenticPlaceHook.md) — marketplace announcement using the same TBA.
- [`inft/iNFT_7857.md`](./inft/iNFT_7857.md) — the ERC-7857 reference implementation on 0G.
