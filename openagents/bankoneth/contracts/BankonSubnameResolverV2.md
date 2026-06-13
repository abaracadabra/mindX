# BankonSubnameResolverV2

`contracts/BankonSubnameResolverV2.sol` — Phase 2.1 of the bankoneth v2
plan. ENS-canonical resolver covering the full
[`PublicResolver` profile interface set](https://docs.ens.domains/resolvers/interfaces)
**plus** [ENSIP-10 wildcard resolution](https://ensips.ethereum.org/ensips/10),
which v1 lacked. Co-exists with v1 — both are deployed by
`script/DeployEthereum.s.sol`; new registrations should bind here,
legacy names keep v1 until explicit migration.

## What ships in V2

| Interface | InterfaceID | Spec |
|---|---|---|
| `IAddrResolver`         | `0x3b3b57de` | [ENSIP-1](https://ensips.ethereum.org/ensips/1) — `addr(node) → address` |
| `IAddressResolver`      | `0xf1cb7e06` | [ENSIP-9](https://ensips.ethereum.org/ensips/9) — `addr(node, coinType) → bytes` |
| `ITextResolver`         | `0x59d1d43c` | [ENSIP-5](https://ensips.ethereum.org/ensips/5) — `text(node, key) → string` |
| `IContentHashResolver`  | `0xbc1c58d1` | [ENSIP-7](https://ensips.ethereum.org/ensips/7) — `contenthash(node) → bytes` |
| `INameResolver`         | `0x691f3431` | reverse name — `name(node) → string` |
| `IExtendedResolver`     | `0x9061b923` | [ENSIP-10](https://ensips.ethereum.org/ensips/10) — wildcard `resolve(name, data) → bytes` |
| `IMulticallable`        | dynamic      | batch — `multicall(bytes[]) → bytes[]` |

## What's preserved from v1

- `REGISTRAR_ROLE` gate on every setter (`setAddr`, `setText`,
  `setContenthash`, `setName`, `setINFTBinding`)
- iNFT Mode A: `addr(node)` returns the TBA when bound, raw addr otherwise
- BANKON agentic text-record namespace works unchanged
- `multicall(bytes[])` via delegatecall preserves the caller's role check

## Why V2 alongside V1 (not in place)

Existing `.bankon.eth` subnames' resolver pointer is pinned at deploy time
inside `BankonSubnameRegistrar`. Replacing v1 in place would silently
detach every existing subname from its resolver. V2 ships as a fresh
deploy; new `BankonSubnameRegistrar` instances point at V2; the old
registrar + v1 resolver keep serving legacy names.

When the operator wants to migrate, run a one-shot `multicall` against
each subname's storage to mirror v1 → V2 state, then update the
registrar's `defaultResolver`. Tracked separately.

## ENSIP-10 wildcard dispatch — how it works

```solidity
function resolve(bytes memory dnsName, bytes memory data) external view returns (bytes memory)
```

The dispatcher:

1. Decodes the DNS-encoded name to a namehash via `_dnsNamehash()` (a
   recursive bottom-up walk — see below).
2. Reads the first 4 bytes of `data` as a selector.
3. Re-dispatches against the matching internal getter:
   - `0x3b3b57de` → `addr(bytes32)` → `abi.encode(address)`
   - `0xf1cb7e06` → `addr(bytes32,uint256)` → `abi.encode(bytes)`
   - `0x59d1d43c` → `text(bytes32,string)` → `abi.encode(string)`
   - `0xbc1c58d1` → `contenthash(bytes32)` → `abi.encode(bytes)`
   - `0x691f3431` → `name(bytes32)` → `abi.encode(string)`
4. Unknown selectors return `""` (per ENSIP-10).

The Universal Resolver (`0xeEeEEEeE…14EeEe`) uses this entry point when
following the resolver chain. Combined with our adapter at the
`bankon.eth` parent's resolver slot, every `*.bankon.eth` lookup the
canonical UR performs lands here.

### `_dnsNamehash(bytes name, uint256 idx)`

Recursive — reads a length byte at `name[idx]`, hashes the next
`labelLen` bytes, recurses on the rest, returns
`keccak256(parent || labelHash)`. ENS names are short (≤10 labels in
practice), so stack depth isn't a concern.

## Storage layout (parallel to v1, intentionally non-shared)

```
_addr           : node → address
_text           : node → key → string
_coinAddr       : node → coinType → bytes
_contenthash    : node → bytes
_name           : node → string         (new in V2)
_tba            : node → address        (iNFT Mode A — overrides _addr)
_zeroGTokenId   : node → uint256        (off-chain attribution only)
```

V2 does NOT migrate v1 storage. To move a subname over, run the
appropriate setters from the registrar — typically batched via
`multicall(bytes[])`.

## Tests — `test/BankonSubnameResolverV2.t.sol`

25 tests across 5 contracts:

- `V2SupportsInterfaceTest` (8) — every canonical interfaceId is
  advertised; unknown IDs reject.
- `V2AddrTest` (6) — `addr(bytes32)` + `addr(bytes32,uint256)` parity
  per ENSIP-1, TBA override, `setAddr(node,60,bytes)` mirror to
  `setAddr(node,address)`.
- `V2TextContentNameTest` (3) — round-trip on each profile.
- `V2WildcardResolveTest` (5) — DNS encoding → namehash via wildcard
  dispatch for addr/text/contenthash/name; unknown selector returns
  empty.
- `V2RoleGateTest` (3) — REGISTRAR_ROLE enforcement on setters.

## Deploy ordering

`script/DeployEthereum.s.sol` deploys V2 right after v1, sharing the
same `inftAdapter`. Both resolvers receive `REGISTRAR_ROLE` grants for
`subnameRegistrar` + `domainHosting` in the same broadcast — so
operators can flip the registrar's resolver pointer without a separate
role-granting transaction.

Console output:
```
BankonSubnameResolver   (v1) : 0x...
BankonSubnameResolverV2 (v2) : 0x...
```

Operators should record both addresses in `~/bankoneth-mainnet.env`.

## Not yet covered (Phase 2.2 / Phase 3)

- CCIP-Read (EIP-3668) `OffchainLookup` revert — that's the
  `BankonOffchainResolver` in Phase 2.2 (separate contract — V2 stays
  on-chain only).
- Authorisation-by-namehash hook for end-user multicall edits
  (`isAuthorised(node, sender)`) — added in Phase 3.1 when the records
  editor UI lands.
- V1 → V2 migration helper — a one-shot script that copies records
  across. Deferred.

## See also

- [`BankonSubnameResolver.md`](BankonSubnameResolver.md) — the v1 contract
- [`docs/ENSIP_COVERAGE.md`](../docs/ENSIP_COVERAGE.md) — full coverage map (Phase 4)
- [`docs/V2_READINESS.md`](../docs/V2_READINESS.md) — ENSv2/Namechain forward-compat (Phase 4)
