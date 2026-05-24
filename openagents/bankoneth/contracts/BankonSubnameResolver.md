# BankonSubnameResolver

> Minimal ENS-compatible resolver for `bankon.eth` subnames + enrolled `.eth` parents, with the BANKON text-record namespace and iNFT Mode A `addr(node)` TBA override.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`BankonSubnameResolver.sol`](./BankonSubnameResolver.sol)

## Role in bankoneth

`BankonSubnameResolver` is the on-chain identity surface every bankoneth subname points at. When a wallet queries `addr(node)` for a registered `*.bankon.eth` or an enrolled `*.<parent>.eth`, this resolver returns either:

1. The ERC-6551 Token-Bound Account address bound through `BankonInftAdapter` (Mode A iNFT), if any; or
2. The raw stored EVM address written by the registrar.

It also stores ENSIP-7 contenthash, ENSIP-9 multi-chain addresses (Base via `0x80002105`, Algorand via `0x8000011B`), and a text-record namespace specific to bankoneth (`mindx.endpoint`, `bonafide.attestation`, `agent.capabilities`, `inft.uri`, `agenticplace.listing`). All write paths are gated on `REGISTRAR_ROLE`, granted to `BankonSubnameRegistrar`, `BankonDomainHosting`, and (transitively) `BankonInftAdapter` post-deploy.

The contract is **self-contained** — it deliberately does NOT inherit from upstream ENS `PublicResolver` so the bankoneth module can compile without pulling in the `ens-contracts` submodule. It still satisfies the same shape that `BankonSubnameRegistrar` expects from `IPublicResolver` (defined in [`interfaces/IBankon.sol`](./interfaces/IBankon.sol)).

## Inheritance

- `IBankonSubnameResolver` — public interface in [`interfaces/IBankonExtensions.sol`](./interfaces/IBankonExtensions.sol).
- `AccessControl` — `DEFAULT_ADMIN_ROLE` (admin/wiring) + `REGISTRAR_ROLE` (write surface).

## Constructor

| arg       | type                       | purpose                                                              |
|-----------|----------------------------|----------------------------------------------------------------------|
| `admin`   | `address`                  | Granted `DEFAULT_ADMIN_ROLE`.                                        |
| `adapter` | `IBankonInftAdapter`       | Initial iNFT adapter binding (can be `address(0)` and set later).    |

Roles granted at construction: `DEFAULT_ADMIN_ROLE` → `admin`.

## Storage layout

| name              | type                                              | purpose                                                                  | mutable? |
|-------------------|---------------------------------------------------|--------------------------------------------------------------------------|----------|
| `REGISTRAR_ROLE`  | `bytes32 constant`                                | `keccak256("REGISTRAR_ROLE")`.                                           | no       |
| `_addr`           | `mapping(bytes32 => address)` private             | ENSIP-1 `addr(node)` storage.                                            | yes (registrar)|
| `_text`           | `mapping(bytes32 => mapping(string => string))` private | ENSIP-5 text records.                                              | yes (registrar)|
| `_coinAddr`       | `mapping(bytes32 => mapping(uint256 => bytes))` private | ENSIP-9 multi-chain addresses.                                     | yes (registrar)|
| `_contenthash`    | `mapping(bytes32 => bytes)` private               | ENSIP-7 contenthash.                                                     | yes (registrar)|
| `_tba`            | `mapping(bytes32 => address)` private             | iNFT Mode A binding: node → ERC-6551 TBA.                                | yes (registrar)|
| `_zeroGTokenId`   | `mapping(bytes32 => uint256)` private             | iNFT Mode A binding: node → 0G iNFT tokenId.                             | yes (registrar)|
| `inftAdapter`     | `IBankonInftAdapter` public                       | Current iNFT adapter reference.                                          | yes (admin)|

## Roles

| Role                 | keccak256                          | Who holds                                                                              | What they can do                                              |
|----------------------|------------------------------------|-----------------------------------------------------------------------------------------|----------------------------------------------------------------|
| `DEFAULT_ADMIN_ROLE` | OpenZeppelin default               | `admin` (constructor)                                                                   | `setInftAdapter`, `grantRegistrar`, `revokeRegistrar`, role mgmt.|
| `REGISTRAR_ROLE`     | `keccak256("REGISTRAR_ROLE")`      | `BankonSubnameRegistrar`, `BankonDomainHosting` (via deploy script `grantRegistrar`).  | `setAddr` (both overloads), `setText`, `setContenthash`, `setINFTBinding`.|

## Events

### `AddrSet(bytes32 indexed node, address a)`

Emitted on `setAddr(bytes32,address)`. Indexers should treat this as the canonical primary-address signal — but consult `addr(node)` (which may override with a TBA) for the value actually returned to ENS clients.

### `TextSet(bytes32 indexed node, string key, string value)`

Emitted on `setText`. `key` and `value` are unhashed (string params can't be indexed, so off-chain consumers filter on `node`).

### `INFTBindingSet(bytes32 indexed node, address tbaAddress, uint256 zeroGTokenId)`

Emitted on `setINFTBinding`. Marks the moment iNFT Mode A is activated for a node — `addr(node)` will start returning `tbaAddress` from this point forward.

### `InftAdapterUpdated(address indexed oldAdapter, address indexed newAdapter)`

Emitted on `setInftAdapter`.

## Errors

This contract defines no custom errors. Reverts come from OpenZeppelin's `AccessControl` (role checks) and a hand-rolled `require(ok, "BankonSubnameResolver: multicall element failed")` inside `multicall`.

## External / public API

### `setInftAdapter(IBankonInftAdapter newAdapter) external`

Updates the cached adapter reference. Access: `DEFAULT_ADMIN_ROLE`. Emits `InftAdapterUpdated`. Note: the resolver does **not** call into the adapter during reads — bindings are stored locally via `setINFTBinding`.

### `grantRegistrar(address registrar) external`

Convenience grant for `REGISTRAR_ROLE`. Access: `DEFAULT_ADMIN_ROLE`. Used by `DeployEthereum.s.sol` lines 116-117 for `BankonSubnameRegistrar` and `BankonDomainHosting`.

### `revokeRegistrar(address registrar) external`

Convenience revoke. Access: `DEFAULT_ADMIN_ROLE`.

### `addr(bytes32 node) external view returns (address)`

ENSIP-1 primary-address resolver. **iNFT Mode A override**: if `_tba[node]` is non-zero, returns the TBA. Otherwise returns `_addr[node]`. ENS clients will follow this transparently — agent wallets that own iNFTs become reachable at their TBA.

### `text(bytes32 node, string calldata key) external view returns (string memory)`

ENSIP-5 text record reader.

### `coinAddr(bytes32 node, uint256 coinType) external view returns (bytes memory)`

ENSIP-9 multi-chain address reader. Use coinType `0x80002105` for Base, `0x8000011B` for Algorand (per the constants in `BankonSubnameRegistrar`).

### `contenthash(bytes32 node) external view returns (bytes memory)`

ENSIP-7 reader. Returns raw bytes; UI is responsible for decoding (ipfs://, bzz://, etc).

### `setAddr(bytes32 node, address a) external`

ENSIP-1 primary-address setter. Access: `REGISTRAR_ROLE`. Emits `AddrSet`. The stored `_addr` is **not** the value `addr(node)` returns when an iNFT binding exists.

### `setAddr(bytes32 node, uint256 coinType, bytes calldata a) external`

ENSIP-9 multi-chain setter. Access: `REGISTRAR_ROLE`. Does NOT emit an event (intentional gas savings; indexers should follow the transaction trace).

### `setText(bytes32 node, string calldata key, string calldata value) external`

ENSIP-5 setter. Access: `REGISTRAR_ROLE`. Emits `TextSet`.

### `setContenthash(bytes32 node, bytes calldata h) external`

ENSIP-7 setter. Access: `REGISTRAR_ROLE`. No event.

### `setINFTBinding(bytes32 node, address tbaAddress, uint256 zeroGTokenId) external`

Activates Mode A binding for the given node. Access: `REGISTRAR_ROLE`. Emits `INFTBindingSet`. Idempotent — re-calling overwrites both slots.

### `multicall(bytes[] calldata data) external returns (bytes[] memory results)`

Batches the above setters into one tx via `address(this).delegatecall`. `BankonSubnameRegistrar._writeAgentRecords` uses this to atomically write up to 7 records per registration. Reverts the whole batch on any element failure with `"BankonSubnameResolver: multicall element failed"`.

### `supportsInterface(bytes4 interfaceId) public view returns (bool)`

Advertises `type(IBankonSubnameResolver).interfaceId` in addition to `AccessControl`'s ERC-165.

## Internal helpers

—

## Invariants

- Once `setINFTBinding(node, tba, tokenId)` is called with `tba != address(0)`, `addr(node) == tba` until the binding is cleared (set to zero).
- `setAddr(bytes32, address)` and the iNFT binding are independent: writing one does not clear the other; the binding takes precedence on read.
- `multicall` is all-or-nothing: any sub-call revert reverts the whole batch.
- Holds no funds. No `receive()`.

## Security considerations

- **`multicall` + `delegatecall` re-entry**: `multicall` delegates into the same contract, so each sub-call runs with the same access-control context (`msg.sender` is preserved through delegatecall). A non-registrar caller cannot escalate by wrapping `setAddr` in a multicall.
- **TBA override hijack**: anyone holding `REGISTRAR_ROLE` can flip a name's TBA via `setINFTBinding`. This is the intended escape hatch for migrations but means a compromised registrar can re-point any name. Mitigation: never grant `REGISTRAR_ROLE` to untrusted contracts.
- **No event for `setAddr(uint256 coinType)` or `setContenthash`**: indexers must follow tx traces. Add explicit events if you need cheap event filtering.
- **String storage**: text records can be arbitrarily long; gas-bounded by the caller.
- **No pause**: in an emergency, revoke `REGISTRAR_ROLE` to halt writes.
- **Cross-contract trust**: the adapter reference is informational; this resolver never calls back into `inftAdapter` during reads.
- **Reentrancy**: no external calls during reads; writes are storage-only except `multicall` (delegatecall into self).
- **ERC-165 surface**: only advertises `IBankonSubnameResolver`. Wallets that expect ENS PublicResolver's larger interface set (e.g., `IExtendedResolver` for CCIP-Read) will not detect support.

## Integration patterns

- `BankonSubnameRegistrar._writeAgentRecords` builds a `bytes[]` of selector-encoded calls (setAddr / setText / setContenthash / multichain setAddr) and invokes `defaultResolver.multicall(calls)` — see [`BankonSubnameRegistrar.sol:384-435`](./BankonSubnameRegistrar.sol). The registrar deliberately downsizes the array to skip empty fields, avoiding wasted gas.
- `BankonDomainHosting.issue` uses the resolver indirectly: it sets the resolver address on `nameWrapper.setSubnodeRecord(..., address(resolver), ...)`, then optional follow-up writes happen via the same multicall pattern.
- `BankonInftAdapter._computeTba(...)` derives the TBA address that an off-chain wirer eventually passes to `setINFTBinding` on this resolver.
- Deployed via [`script/DeployEthereum.s.sol`](../script/DeployEthereum.s.sol) line 81: `new BankonSubnameResolver(treasury, IBankonInftAdapter(address(0)))` — adapter initially unset, wired later by `setInftAdapter`.

## Known gotchas

- The adapter reference is **never read** by the resolver for resolution — it's pure metadata. The TBA used in `addr(node)` comes from the local `_tba` mapping, populated only via `setINFTBinding`.
- `multicall` element failures return a generic string. If you're debugging a multi-call, replay the sub-calls one-by-one to find the culprit.
- `setAddr(node, coinType, bytes)` accepts arbitrary bytes for the address; clients must encode according to SLIP-44 + chain conventions. For Base (EVM), pass `abi.encodePacked(addr)` (20 bytes). For Algorand, pass the 32-byte public-key form.
- `revokeRegistrar` is wired but **not** auto-called during contract upgrades; ops must explicitly revoke old registrar addresses.
- The contract is self-contained and intentionally does NOT match the upstream ENS PublicResolver interface 1:1 — wallet apps may need to call `addr(node)` explicitly rather than going through `Resolver.resolve(...)`.

## See also

- [`interfaces/IBankonExtensions.md`](./interfaces/IBankonExtensions.md) — `IBankonSubnameResolver` interface.
- [`interfaces/IBankon.md`](./interfaces/IBankon.md) — `IPublicResolver` (the registrar-side compat interface).
- [`BankonSubnameRegistrar.md`](./BankonSubnameRegistrar.md) — primary writer via `multicall`.
- [`BankonDomainHosting.md`](./BankonDomainHosting.md) — Flow C writer.
- [`BankonInftAdapter.md`](./BankonInftAdapter.md) — supplies TBA addresses for `setINFTBinding`.
