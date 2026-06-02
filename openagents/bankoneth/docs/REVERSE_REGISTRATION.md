# Reverse Registration (Primary Names) — Phase 2.3 + Phase 3.4

Two stories: **the contract's own primary name** (so block explorers
display `registrar.bankon.eth` instead of a raw address) and **the
end-user's primary name** (so wallets show `alice.bankon.eth`).

## Story A — contract primary name (ENSIP-15)

After deploy, the treasury runs [`script/SetPrimaryNames.s.sol`](../script/SetPrimaryNames.s.sol)
which calls `setReverseName(rr, name)` on each registrar contract:

| Contract | Primary set to |
|---|---|
| `BankonSubnameRegistrar`  | `registrar.bankon.eth` |
| `BankonEthRegistrar`      | `eth-registrar.bankon.eth` |
| `BankonDomainHosting`     | `host.bankon.eth` |
| `BankonOffchainRegistrar` | `offchain.bankon.eth` |

`setReverseName(IReverseRegistrar rr, string newName)` is admin-gated on
each registrar contract (see [Phase 2.3 commit](../docs/AUDIT.md)). It
calls `rr.setName(newName)` from the contract itself — the
ReverseRegistrar records the name against `[address(this)].addr.reverse`.

### Prerequisites

The reverse-target subname (e.g. `registrar.bankon.eth`) MUST be minted
under `bankon.eth` first — otherwise the reverse record points at a name
nobody owns and explorers will silently show the raw address. Use the
BankonSubnameRegistrar or the ENS app to mint the four reverse-target
subnames before running `SetPrimaryNames.s.sol`.

### Env vars

```bash
export DEPLOYER_PK=...                      # has DEFAULT_ADMIN_ROLE
export SUBNAME_REGISTRAR_ADDR=...
export ETH_REGISTRAR_ADDR=...
export DOMAIN_HOSTING_ADDR=...
export REVERSE_REGISTRAR_ADDR=0xa58E81fe9b61B5c3fE2AFD33CF304c454AbFc7Cb  # mainnet

# Optional overrides
export SUBNAME_REGISTRAR_NAME="registrar.bankon.eth"
export ETH_REGISTRAR_NAME="eth-registrar.bankon.eth"
export DOMAIN_HOSTING_NAME="host.bankon.eth"
```

### Run

```bash
forge script script/SetPrimaryNames.s.sol \
  --rpc-url $RPC \
  --broadcast -vvv
```

Output prints the reverse-node namehashes for the operator log.

## Story B — end-user primary name (ENSIP-3)

`<b-primary-name>` ([source](../packages/ui/src/manage/b-primary-name.ts))
calls `ReverseRegistrar.setName(name)` from the connected wallet. The
reverse record is recorded against `[walletAddr].addr.reverse`.

### User flow

1. Panel reads current primary via UR `reverse(addr, 60n)`. Shows
   `none` if unset.
2. User clicks **Use \<name\> as primary**.
3. Wallet calls `ReverseRegistrar.setName(name)`.
4. Panel updates to show the new primary.

Gas: ~95k (one resolver write + reverse record).

## Story C — ENSIP-19 multichain reverse (helpers shipped)

[ENSIP-19](https://ensips.ethereum.org/ensips/19) introduces per-coinType
reverse records (distinct names for Mainnet vs Base vs Optimism). The
namespace becomes `<addr>.<coinType-hex>.reverse` instead of
`<addr>.addr.reverse`.

bankoneth ships the derivation helpers + ReverseRegistrar address pins
in [`packages/core/src/contract-naming.ts`](../packages/core/src/contract-naming.ts):

```ts
import { reverseNamespace, l2ReverseRegistrarFor, evmCoinType } from "@bankoneth/core";

const optimismCoinType = evmCoinType(10);            // 0x8000000a
const { label, node } = reverseNamespace(addr, optimismCoinType);
// label === "<addr-lower>.8000000a.reverse"

const rr = l2ReverseRegistrarFor(10);                // L2 ReverseRegistrar on Optimism
// rr === null when the chain isn't pinned; operators populate
// L2_REVERSE_REGISTRARS against the canonical ensdomains/ens-contracts
// deployment artifact before broadcasting on that chain.
```

When bankoneth deploys on an L2, the equivalent of
`script/SetPrimaryNames.s.sol` is the same shape — only the
ReverseRegistrar address changes, sourced from `l2ReverseRegistrarFor()`.

L2 deploy + the L2 equivalent of `SetForwardNames` are out of scope for
this pass (no bankoneth registrar runs on an L2 today). The helpers are
forward-work-ready for the next phase. See
[`CONTRACT_NAMING_AUDIT.md`](CONTRACT_NAMING_AUDIT.md) for the full
status + the deferred items.

## Story D — Forward record duality

`setReverseName` records `<addr>.addr.reverse → name` but is only half
the story. Canonical resolvers (Etherscan, Rainbow, viem's
`getEnsName`) reject the reverse if the forward leg doesn't match —
they require `PublicResolver.addr(namehash(name)) === addr`.

bankoneth ships [`script/SetForwardNames.s.sol`](../script/SetForwardNames.s.sol)
to close that gap. Run it immediately after `SetPrimaryNames.s.sol`:

```bash
forge script script/SetForwardNames.s.sol \
  --rpc-url $RPC \
  --broadcast \
  -vvv
```

Idempotent — skips any `(name, addr)` pair already wired correctly.
Same env-var convention as `SetPrimaryNames.s.sol`. Requires the
deployer wallet to have REGISTRAR_ROLE on the PublicResolver (or own
`bankon.eth` sufficiently to set its child records).

## Story E — Round-trip verification

After Stories A + D, audit the wire-up:

```bash
forge script script/VerifyContractNames.s.sol -vv
```

Read-only. Prints a per-contract table with ✓/✗ for reverse, forward,
and round-trip. Reverts (non-zero exit) on any round-trip failure so
CI / the Sepolia rehearsal runbook can gate on the result.

In TypeScript:

```ts
import { verifyContractName } from "@bankoneth/core";

const status = await verifyContractName({
  client:       publicClient,
  address:      REGISTRAR_ADDR,
  expectedName: "registrar.bankon.eth",
});
console.log(status); // { reverseName, forwardAddr, roundTrip, gaps[] }
```

The `<b-contract-name-status>` Lit component mounted on
`packages/tauri-app/admin.html` calls this for every bankoneth contract
and renders the result as a status table. No wallet required.

## Failure modes

- **Subname unminted.** Reverse points at a non-existent name. Block
  explorers ignore + show raw address. Mint the subname first.
- **`setName` reverts.** The wallet doesn't own `[walletAddr].addr.reverse`.
  Unusual — typically self-owned by default.
- **Stale primary.** Some clients cache reverse records for 24h.

## Further reading

- [Contract naming guide](https://docs.ens.domains/web/naming-contracts)
- [`SetPrimaryNames.s.sol`](../script/SetPrimaryNames.s.sol)
- [`<b-primary-name>`](../packages/ui/src/manage/b-primary-name.ts)
- [ENSIP-3 reverse resolution](https://docs.ens.domains/ensip/3) (current default)
- [ENSIP-19 multichain reverse](https://ensips.ethereum.org/ensips/19)
