# MockResolver

> Minimal ENS Public Resolver stand-in. Records every write so tests can verify exactly which records the BANKON registrar wrote.

**SPDX:** MIT | **Pragma:** ^0.8.24 | **Source:** [`MockResolver.sol`](./MockResolver.sol)

## What it mocks

Stands in for the production ENS [`PublicResolver`](https://github.com/ensdomains/ens-contracts/blob/master/contracts/resolvers/PublicResolver.sol). Implements the [`IPublicResolver`](../../contracts/interfaces/IBankon.sol) interface as defined in bankoneth.

**Faithfulness:** record-keeping faithful, semantics-poor.
- ✓ `setAddr`, `setAddr(node,coinType,bytes)`, `setText`, `setContenthash` all store correctly.
- ✓ `multicall` correctly `delegatecall`s each sub-call (essential for the registrar's batched-record write pattern).
- ✗ No access control — anyone can write any record.
- ✗ No events (`AddrChanged`, `TextChanged`, `ContenthashChanged`, etc.).
- ✗ No ENSIP-10 (CCIP-Read) wildcard resolution.
- ✗ No `addr(node)` reverse-of-`setAddr(node,coinType=60)` — coinType-60 (ETH) and the plain `setAddr` are stored in *different* mappings here.

The mock's value is observability: every record write is reflected in a public mapping the tests can read back.

## Storage / state

| Field | Type | Purpose / how tests use it |
|---|---|---|
| `addrOf` | `mapping(bytes32 => address)` (public) | node → `address` set via the legacy `setAddr(bytes32, address)`. Tests assert `resolver.addrOf(node) == alice` after register. |
| `addrOfChain` | `mapping(bytes32 => mapping(uint256 => bytes))` (public) | node → coinType → raw bytes. Used by ENSIP-9 multi-chain addr. Tests assert `resolver.addrOfChain(node, COIN_TYPE_BASE) == abi.encodePacked(m.baseAddress)` and similarly for Algorand. |
| `textOf` | `mapping(bytes32 => mapping(string => string))` (public) | node → key → value text record. Tests assert keys: `"url"` (mindx endpoint), `"x402.endpoint"`, `"algoid.did"`, `"agent.card"`. |
| `contenthashOf` | `mapping(bytes32 => bytes)` (public) | node → contenthash bytes (typically EIP-1577 multihash). Tests assert `keccak256(resolver.contenthashOf(node)) == keccak256(m.contenthash)`. |
| `multicallCount` | `uint256` (public) | Counts `multicall(...)` invocations. Tests assert `resolver.multicallCount() == 1` to confirm all records were written in a single batched call (the registrar's gas-optimized write path). |

## Implemented methods

| Method | Production behaviour | Mock behaviour | Notes |
|---|---|---|---|
| `setAddr(bytes32 node, address a)` | Legacy ETH-only setter. Access-controlled to node owner. Emits `AddrChanged`. | `addrOf[node] = a;`. | No access control, no event. |
| `setAddr(bytes32 node, uint256 coinType, bytes a)` | ENSIP-9 multi-chain addr. Access-controlled. Emits `AddressChanged`. | `addrOfChain[node][coinType] = a;`. | Note: setting coinType=60 here does NOT update `addrOf` (the two paths are independent in this mock). |
| `setText(bytes32 node, string key, string value)` | ENSIP-5 text record. Access-controlled. Emits `TextChanged`. | `textOf[node][key] = value;`. | No access control. |
| `setContenthash(bytes32 node, bytes hash)` | EIP-1577 contenthash. Access-controlled. Emits `ContenthashChanged`. | `contenthashOf[node] = hash;`. | No access control. |
| `multicall(bytes[] datas) → bytes[]` | Solady-style batched delegatecall, atomic. | Increments `multicallCount`, allocates `results[]`, loops `address(this).delegatecall(datas[i])`, `require(ok, "resolver multicall sub-call failed")`, captures each return. | **Faithful** — the delegatecall pattern correctly mutates this contract's storage (delegatecall preserves storage context). |

## Admin / test helpers

**None.** All read-back is via the public auto-generated getters on the storage mappings.

## Limitations

- **No access control** — production resolver gates writes on `isAuthorised(node)` (which checks ENS node owner or operator approval). Mock accepts any caller. Tests can't verify the registrar's *authorisation* path against the resolver, only that the call shape is right.
- **No events** — `AddrChanged`, `AddressChanged`, `TextChanged`, `ContenthashChanged` all silent. `expectEmit` against the mock is impossible.
- **`setAddr(node, address)` and `setAddr(node, 60, bytes)` are decoupled** — production has these synced; here they're in different mappings. Tests must read whichever path matches.
- **No `addr(node) view`** — only the storage getter `addrOf(bytes32) → address` is auto-generated; tests can't simulate a real resolver-read query.
- **No CCIP-Read / ENSIP-10** — `resolve(bytes name, bytes data)` not implemented.
- **`multicall` error message** is a string `"resolver multicall sub-call failed"` rather than bubbling the inner revert. Diagnostic info from a sub-call's revert reason is lost.
- **No ABI record, no name record, no pubkey record, no DNSSec record** — the niche resolver records aren't mocked.

## Used by

- [`../BankonSubnameRegistrar.t.sol`](../BankonSubnameRegistrar.t.sol) — primary consumer; `test_PaidRegister_writesAllResolverRecords` asserts the full record bundle plus `multicallCount == 1`.
- [`../BankonDomainHosting.t.sol`](../BankonDomainHosting.t.sol) — deployed in fixture; tests don't currently read resolver state but the resolver is wired into the hosting contract for production parity.

Not directly used by `BankonInftAdapter.t.sol`, `BankonEndToEnd.t.sol`, `BankonAgenticPlaceHook.t.sol`, `BankonX402Attestor.t.sol` (those use the real `BankonSubnameResolver` since iNFT Mode-A overrides `addr(node)` behavior that the mock can't replicate).

## See also

- [`../../contracts/interfaces/IBankon.sol`](../../contracts/interfaces/IBankon.sol) — `IPublicResolver` interface this implements.
- [`../../contracts/BankonSubnameResolver.sol`](../../contracts/BankonSubnameResolver.sol) — production BANKON resolver that wraps a real Public Resolver with Mode-A iNFT semantics.
- [Production ENS PublicResolver](https://github.com/ensdomains/ens-contracts/blob/master/contracts/resolvers/PublicResolver.sol) — reference.
- [`MockNameWrapper.sol`](./MockNameWrapper.sol), [`MockIdentityRegistry.sol`](./MockIdentityRegistry.sol) — sibling test mocks.
- ENSIP-5 (text), ENSIP-9 (addr multi-chain), EIP-1577 (contenthash) — the standards being recorded.
