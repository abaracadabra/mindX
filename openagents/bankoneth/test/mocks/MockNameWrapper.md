# MockNameWrapper

> Minimal ENS NameWrapper stand-in for testing the BANKON registrar — tracks subnode owners + fuses + expiry per `(parentNode, label)`, and exposes the surface the registrar actually calls.

**SPDX:** MIT | **Pragma:** ^0.8.24 | **Source:** [`MockNameWrapper.sol`](./MockNameWrapper.sol)

## What it mocks

Stands in for the production ENS [`NameWrapper`](https://github.com/ensdomains/ens-contracts/blob/master/contracts/wrapper/NameWrapper.sol) (mainnet `0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401`). Implements the [`INameWrapper`](../../contracts/interfaces/IBankon.sol) interface as defined in bankoneth.

**Faithfulness:** partial.
- ✓ Tracks owner / fuses / expiry per node.
- ✓ `extendExpiry` correctly caps child expiry to the parent's expiry.
- ✓ `setSubnodeRecord` and `setSubnodeOwner` use the canonical ENS subnode derivation `keccak256(abi.encodePacked(parentNode, keccak256(bytes(label))))`.
- ✗ No actual ENS registry interaction (`ENSRegistry.setSubnodeOwner`).
- ✗ No fuse-burn enforcement — `setFuses` ORs the new fuses in but never rejects a write because `PARENT_CANNOT_CONTROL` isn't burned.
- ✗ No `isWrapped` semantic faithfulness — just `owner != address(0)`.
- ✗ `setResolver(node, resolver)` is a no-op (`pure`).
- ✗ No CCIP-Read, no `ownerOf`-from-ERC1155 semantics, no upgrade-controller logic.

The mock exists to verify the registrar's *call pattern* (three-step register-records-transfer, expiry-cap behavior, renewal via `extendExpiry`, event reachability), NOT to faithfully reimplement ENS fuse semantics.

## Storage / state

| Field | Type | Purpose / how tests use it |
|---|---|---|
| `data` | `mapping(uint256 => Data)` (public) where `Data = (address owner, uint32 fuses, uint64 expiry)` | Per-node storage. Tests read via `getData(uint256(node))` to confirm post-mint state (owner, fuses, expiry). |
| `lastSubnodeRecord` | `mapping(bytes32 => bytes32)` (public) | Parent → most-recently-minted subnode. Records the last subnode produced by `setSubnodeRecord`. Tests read for sanity but most use `data[expectedNode]` instead. |
| `approvals` | `mapping(uint256 => address)` (public) | ERC-721-shape approval (tokenId → operator). Set by `approve`. Not read by current tests. |
| `approvalForAll` | `mapping(address => mapping(address => bool))` (public) | ERC-721-shape operator approval. Set by `setApprovalForAll`. Not read by current tests. |

## Implemented methods

| Method | Production behaviour | Mock behaviour | Notes |
|---|---|---|---|
| `ownerOf(uint256 id) view → address` | Returns owner from wrapper / underlying registry. | `data[id].owner`. | Identity-preserving. |
| `getData(uint256 id) view → (address, uint32, uint64)` | Returns wrapped-node data (owner, fuses, expiry). | Reads `data[id]`. | Identity-preserving. |
| `setSubnodeOwner(parent, label, owner, fuses, expiry) → bytes32 subnode` | Wraps + transfers a subnode, validates fuses, requires `parentControlled` etc. | Derives subnode via canonical keccak, stores `(owner, fuses, expiry)`. Returns subnode. | No fuse validation. |
| `setSubnodeRecord(parent, label, owner, resolver, ttl, fuses, expiry) → bytes32 subnode` | As above plus sets resolver + TTL on the underlying registry. | Same as `setSubnodeOwner`, additionally records `lastSubnodeRecord[parent] = subnode`. Ignores `resolver`/`ttl`. | Ignores resolver+ttl args. |
| `setChildFuses(parent, labelhash, fuses, expiry)` | Updates fuses + expiry of a child, with permission check. | Direct overwrite of `data[node].fuses` and `data[node].expiry`. | No permission check. |
| `setFuses(node, ownerControlledFuses) → uint32` | Adds owner-controlled fuses with `CAN_DO_EVERYTHING` semantics. | ORs `uint32(ownerControlledFuses)` into `data[node].fuses`. Returns updated fuses. | No `PARENT_CANNOT_CONTROL` precondition check. |
| `setResolver(node, resolver)` | Sets resolver on the underlying registry. | `pure` no-op. | Silently swallows. |
| `extendExpiry(parent, labelhash, expiry) → uint64` | Extends child expiry, requires `CAN_EXTEND_EXPIRY` or parent control, caps at parent expiry. | Derives node, caps `expiry` at `parent.expiry` if non-zero, writes, returns. | **Cap behavior faithful** (essential for the `test_PaidRegister_capsExpiryToParent` test). No fuse check. |
| `isWrapped(node) view → bool` | Returns whether the node is currently wrapped in the NameWrapper. | `data[node].owner != address(0)`. | **Lossy** — conflates "is wrapped" with "has owner". |
| `setApprovalForAll(operator, approved)` | ERC-1155 operator approval. | `approvalForAll[msg.sender][operator] = approved`. | Stored, never read by registrar code paths. |
| `approve(to, tokenId)` | ERC-1155/ERC-721 approve. | `approvals[tokenId] = to`. | Stored, never read by registrar code paths. |

## Admin / test helpers

| Helper | Purpose |
|---|---|
| `adminSetParent(bytes32 parentNode, address owner, uint32 fuses, uint64 expiry)` | **Test-only.** Pre-seeds the wrapped state of a parent node — used by tests to: (a) declare `parentNode = admin, fuses=0, expiry=now+10y` so child mints succeed; (b) declare a parent with `CANNOT_UNWRAP` (fuse=1) burned for `BankonDomainHosting` enrollment; (c) tighten parent expiry to test the child-expiry-cap path. Not present on the production interface — it's the mock's only escape hatch. |

## Limitations

- **No fuse-burn enforcement** — production NameWrapper requires `PARENT_CANNOT_CONTROL` burned on the parent before child-owner-controlled writes. Mock skips this entirely.
- **No `CANNOT_UNWRAP` ↔ `isWrapped` link** — production unwraps when fuses allow it; the mock has no `unwrap` method.
- **`isWrapped == (owner != 0)`** — a parent that's wrapped, then transferred to a non-zero EOA after unwrap, would still report `isWrapped = true` in the mock. Real wrapper distinguishes wrap state from ownership.
- **No ERC-1155 transfer semantics** — wrapped names are ERC-1155 in production; the mock has no `safeTransferFrom` / `balanceOf` / batch APIs.
- **No events** — `NameWrapped`, `NameUnwrapped`, `FusesSet`, `ExpiryExtended` all silent. Tests can't use `expectEmit` against the mock.
- **No upgrade controller** — production has an upgrade-contract pointer; not present here.
- **No CCIP-Read** — `resolve(bytes name, bytes data)` not implemented.

## Used by

- [`../BankonSubnameRegistrar.t.sol`](../BankonSubnameRegistrar.t.sol) — primary consumer; full 34-test exhaustive coverage.
- [`../BankonDomainHosting.t.sol`](../BankonDomainHosting.t.sol) — secondary; uses `adminSetParent` to seed `CANNOT_UNWRAP` parents.

Not used by `BankonInftAdapter.t.sol`, `BankonEndToEnd.t.sol`, `BankonAgenticPlaceHook.t.sol`, or `BankonX402Attestor.t.sol` (those test post-mint flows and don't need an ENS wrapper).

## See also

- [`../../contracts/interfaces/IBankon.sol`](../../contracts/interfaces/IBankon.sol) — `INameWrapper` interface this implements.
- [Production ENS NameWrapper](https://github.com/ensdomains/ens-contracts/blob/master/contracts/wrapper/NameWrapper.sol) — full reference.
- [`MockResolver.sol`](./MockResolver.sol), [`MockIdentityRegistry.sol`](./MockIdentityRegistry.sol) — sibling test mocks.
- `docs/ADDR_REFERENCE.md` — mainnet NameWrapper address: `0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401`.
