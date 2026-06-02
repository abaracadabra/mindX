# bankoneth — Contract Naming Audit

Deep review of how bankoneth's four registrar contracts (`BankonSubnameRegistrar`,
`BankonEthRegistrar`, `BankonDomainHosting`, `BankonOffchainRegistrar`) are
named on ENS, gap analysis vs ENS canon, and the tooling shipped in this
pass to close those gaps. Companion doc to
[`REVERSE_REGISTRATION.md`](REVERSE_REGISTRATION.md) and
[`ENSIP_COVERAGE.md`](ENSIP_COVERAGE.md).

## ENS canon — what "proper" contract naming looks like

ENS contract naming is a two-sided story: a **reverse** record so block
explorers display `registrar.bankon.eth` instead of `0xabcd…`, and a
**forward** record so client libraries can resolve `registrar.bankon.eth`
back to the contract address. The two together let a verifier round-trip:

```
addr ──reverse──► name        forwards must round-trip:
name ──forward──► addr        resolveAddr(resolveName(addr)) == addr
```

Resolvers that follow the canonical round-trip pattern (Etherscan,
Rainbow, viem's `getEnsName`) **reject the reverse if the forward
doesn't match** — a security measure against impostor names. Setting
only the reverse is insufficient; the forward must also point back.

Canonical references:

- [ENSIP-1 — addr resolution](https://ensips.ethereum.org/ensips/1)
- [ENSIP-3 — reverse resolution (mainnet `addr.reverse`)](https://ensips.ethereum.org/ensips/3)
- [ENSIP-15 — immutable contract naming](https://docs.ens.domains/web/naming-contracts)
- [ENSIP-19 — multichain reverse (draft)](https://ensips.ethereum.org/ensips/19)
- [ens-contracts `ReverseClaimer.sol`](https://github.com/ensdomains/ens-contracts/blob/staging/contracts/reverseRegistrar/ReverseClaimer.sol)
- [ENS Universal Resolver](https://docs.ens.domains/resolvers/universal)

## bankoneth coverage matrix

| Canon pattern | Status | Path |
|---|---|---|
| ReverseRegistrar.setName from inside contract       | ✓ Phase 2.3 | `setReverseName(rr, name)` admin method |
| Operator-driven post-deploy wire-up                 | ✓ Phase 2.3 | `script/SetPrimaryNames.s.sol` |
| **Forward addr record (`name.eth → addr`)**         | ✓ Phase C   | `script/SetForwardNames.s.sol` (new) |
| **Round-trip verification**                         | ✓ Phase B/C | `verifyContractName()` + `script/VerifyContractNames.s.sol` |
| **ENSIP-19 multichain reverse**                     | ✓ helpers   | `reverseNamespace(addr, coinType)` + `L2_REVERSE_REGISTRARS` map |
| Ownable-aware (`ReverseRegistrar` reads `Ownable.owner()`) | ✗ N/A   | bankoneth registrars use `AccessControl`; `setReverseName` is the equivalent path |
| `ReverseClaimer` constructor mixin                  | ✗ deferred  | constructor changes would break existing deploys; not worth the churn |
| **Tests on `setReverseName`**                       | ✓ Phase D   | `test/ContractNaming.t.sol` (12 tests) |
| **UI inspector**                                    | ✓ Phase E   | `<b-contract-name-status>` + `/admin.html` |
| UI inspector / dashboard surface                    | ✓ Phase E   | `/admin.html` |

Bold rows = gaps the audit closed in this pass.

## Gaps closed in this pass

### Gap 1 — Forward record duality

`setReverseName` wrote `<addr>.addr.reverse → name` but never set
`PublicResolver.addr(namehash(name)) = addr`. Etherscan / viem
`getEnsName` rejected the reverse because the forward leg was absent.

**Fix**: new operator-broadcast script
[`script/SetForwardNames.s.sol`](../script/SetForwardNames.s.sol). For
each `(name, contractAddr)` env pair, calls `PublicResolver.setAddr(namehash(name),
contractAddr)`. Idempotent — re-running is safe. Prerequisite: deployer
wallet must hold REGISTRAR_ROLE on the resolver (or own `bankon.eth`
sufficiently to set its child records).

### Gap 2 — Round-trip verification

Operators had to verify each contract's name configuration manually via
`cast`. No CI / runbook gate.

**Fix**:
- TypeScript: [`verifyContractName()`](../packages/core/src/contract-naming.ts) in
  `@bankoneth/core`. Returns `{ reverseName, forwardAddr, roundTrip,
  gaps }`. Used by the UI inspector + by integrators in code.
- Solidity: [`script/VerifyContractNames.s.sol`](../script/VerifyContractNames.s.sol).
  Read-only audit. Reverts on round-trip failure → CI / Sepolia runbook
  can gate on `forge script` exit code.

### Gap 3 — ENSIP-19 multichain reverse

bankoneth currently deploys on L1 only, but the v2 plan calls for L2
deploys. ENSIP-19 changes the reverse namespace per-coinType:
`<addr>.<coinType-hex>.reverse`. Without helpers operators would
hand-derive the namespace every L2 deploy.

**Fix**:
- [`reverseNamespace(addr, coinType)`](../packages/core/src/contract-naming.ts)
  exports the label + namehash. Defaults to coinType 60 (ENSIP-3); any
  other coinType triggers ENSIP-19 derivation.
- [`L2_REVERSE_REGISTRARS`](../packages/core/src/contract-naming.ts) const
  map for Optimism / Base / Arbitrum / Scroll / Linea. Addresses
  populated with zero placeholders — **operators must verify against
  the canonical `ensdomains/ens-contracts` deployments before L2
  broadcast**.
- Parity tests in
  [`test/ContractNaming.t.sol:Ensip19NamespaceTest`](../test/ContractNaming.t.sol)
  confirm the Solidity-side derivation matches the TS export for the
  four target chains.

### Gap 4 — Ownable-aware path

ENS docs recommend the Ownable pattern: deploy `Ownable` contracts, the
ReverseRegistrar recognizes `Ownable.owner()` and lets that EOA set the
contract's name via `setNameForAddr`. bankoneth registrars use
`AccessControl` (multi-role + future-proof for DAIO governance), so the
Ownable shortcut doesn't apply directly.

**Resolution**: the `setReverseName(rr, name)` admin method **is** the
equivalent — it forwards `rr.setName(name)` from inside the contract,
which the ReverseRegistrar records against `msg.sender`'s reverse node.
Same outcome, slightly different idiom. Documented here; not changed.

### Gap 5 — `setReverseName` had zero tests

Phase 2.3 shipped the 4 admin methods without coverage. Coverage gap.

**Fix**: [`test/ContractNaming.t.sol`](../test/ContractNaming.t.sol)
+ [`test/mocks/MockReverseRegistrar.sol`](../test/mocks/MockReverseRegistrar.sol)
ship 12 tests covering each registrar's admin gate + happy path + the
ENSIP-19 namespace derivation.

### Gap 6 — UI inspector

No visual surface for the operator to confirm everything's wired post-
deploy. They had to read each address into Etherscan manually.

**Fix**: `<b-contract-name-status>` Lit Web Component
([`packages/ui/src/manage/b-contract-name-status.ts`](../packages/ui/src/manage/b-contract-name-status.ts))
mounted on a new `/admin.html` entry point in `packages/tauri-app/`.
Read-only — uses the publicClient, no wallet required. Shows a status
table with green / amber / red pills per the canonical round-trip;
click-to-expand reveals actual values + gap list per row.

### Gap 7 — No audit doc

You're reading it.

## Deferred (out of scope this pass)

- **`ReverseClaimer` constructor mixin.** Would auto-claim the
  contract's reverse to the deployer at construction time without a
  separate post-deploy script. Requires breaking the 4 registrars'
  constructor signatures + cascading every test setUp. Existing
  `setReverseName` admin method covers the same use case at the cost of
  one extra tx. Defer until the next major version that's already
  breaking constructors.
- **Refactor 4 registrars from AccessControl to Ownable.** Would unlock
  the ReverseRegistrar's built-in Ownable recognition. Same trade-off
  as ReverseClaimer — invasive constructor + role-API change. Defer.
- **Per-multisig name disambiguation.** No canon pattern; defer.
- **L2 deploy itself.** This pass ships the helpers + tests; actually
  deploying any bankoneth registrar on an L2 is a separate workstream.
- **Server-side automation.** Operators broadcast `SetPrimaryNames` /
  `SetForwardNames` manually from the rehearsal runbook.

## Operator runbook delta

After Phase 0.5's Sepolia rehearsal runbook completes:

```bash
# 1. (existing) — wire reverse records
forge script script/SetPrimaryNames.s.sol --broadcast …

# 2. (NEW) — set forward addr records so round-trip works
forge script script/SetForwardNames.s.sol --broadcast …

# 3. (NEW) — assert round-trip
forge script script/VerifyContractNames.s.sol -vv
#    Exits non-zero if any contract fails round-trip.

# 4. (NEW) — visual smoke
#    Open http://127.0.0.1:5173/admin.html
#    Expect all rows green (reverse + forward + roundtrip).
```

## See also

- [`REVERSE_REGISTRATION.md`](REVERSE_REGISTRATION.md) — Stories A–E of
  primary-name setup (contract + user + multichain + forward + verify)
- [`ENSIP_COVERAGE.md`](ENSIP_COVERAGE.md) — full ENSIP implementation
  matrix
- [`V2_READINESS.md`](V2_READINESS.md) — ENSv2 / Namechain forward-compat
- [`AUDIT.md`](AUDIT.md) — security-side audit findings
