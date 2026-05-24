# bankoneth — ENSv2 Readiness

How bankoneth stays forward-compatible with [ENSv2](https://docs.ens.domains/web/ensv2-readiness)
(also tracked at [ensdomains/namechain](https://github.com/ensdomains/namechain) —
formerly `contracts-v2`).

## What ENSv2 changes

- **L2 native**: Namechain is a dedicated L2 for ENS state. Names will
  live on Namechain by default; mainnet stays as the resolution entry
  point.
- **Universal Resolver becomes the only path**. Direct PublicResolver
  reads break when names migrate to Namechain. dApps that call
  `resolver.text(node, key)` directly will silently see stale data.
- **CCIP-Read is mandatory**, not optional. Resolution may bounce off-
  chain (via L2 read or hosted gateway) and clients must handle the
  EIP-3668 handshake.
- **Reverse resolution gets multichain support** ([ENSIP-19](https://ensips.ethereum.org/ensips/19))
  — reverse records can live per-coinType (e.g. distinct names for
  Mainnet vs Base).

## What bankoneth did to stay ready

### 1. Universal Resolver everywhere
- Pinned `0xeEeEEEeE14D718C2B47D9923Deab1335E144EeEe` in
  [`packages/core/src/addresses.ts`](../packages/core/src/addresses.ts)
  (mainnet + Sepolia — same address).
- [`resolveProfile()`](../packages/core/src/universal-resolver.ts) is the
  default read path. CCIP-Read offchain resolvers (`*.base.eth`,
  `*.cb.id`) Just Work.
- [`lookupName()`](../packages/core/src/lookup.ts) — the helper that
  powers `<bankoneth-name-card>` — routes via UR.

### 2. viem ≥ 2.35 + `@ensdomains/ensjs` v4
- Both libraries already speak the UR + CCIP-Read protocol. The bump
  from viem 2.21 → 2.35 in Phase 1.1 was the minimum required for
  ENSv2-forward-compat (see [the official guidance](https://docs.ens.domains/web/ensv2-readiness)).
- ensjs ships the canonical subgraph helpers (`getNamesForAddress`,
  `getSubnames`, `getNameHistory`) — wrapped in
  [`packages/core/src/inventory.ts`](../packages/core/src/inventory.ts).

### 3. ENSIP-15 name normalization at every entry
- [`@adraffy/ens-normalize`](https://github.com/adraffy/ens-normalize.js)
  via [`packages/core/src/normalize.ts`](../packages/core/src/normalize.ts).
- Every public BankonethClient method runs user input through
  `normalize()` first; raw labels error.

### 4. ENSIP-10 wildcard resolver
- [`BankonSubnameResolverV2`](../contracts/BankonSubnameResolverV2.sol)
  implements `resolve(name, data)` — required for ENSv2 because direct
  per-record calls fall back through wildcard dispatch.

### 5. CCIP-Read off-chain mode
- [`BankonOffchainResolver`](../contracts/BankonOffchainResolver.sol) +
  [`BankonOffchainRegistrar`](../contracts/BankonOffchainRegistrar.sol) +
  the [Bun gateway](../services/offchain-gateway/) ship the EIP-3668
  pattern as a first-class issuance mode. The same handshake works
  whether bankoneth runs on L1, an L2, or Namechain.

### 6. ENSIP-15 immutable contract naming
- `setReverseName(rr, name)` admin method on all four registrars, wired
  by [`SetPrimaryNames.s.sol`](../script/SetPrimaryNames.s.sol). Block
  explorers + wallets that do reverse lookups display
  `registrar.bankon.eth`, `eth-registrar.bankon.eth`,
  `host.bankon.eth`, `offchain.bankon.eth` instead of raw addresses.

## What still requires action when ENSv2 lands

| Item | Action |
|---|---|
| Namechain L2 deploy | bankoneth currently deploys on L1. When ENSv2 ships an L2-native subname registrar pattern, fork the deploy script to target Namechain — the UR proxy will keep both sides working in parallel during the transition. |
| ENSIP-19 multichain reverse | bankoneth currently sets ENSIP-3 reverse records (the `addr.reverse` namespace). When ENSIP-19 multichain reverse stabilizes, add per-coinType reverse setup to `SetPrimaryNames.s.sol`. |
| Subgraph migration | The hosted ENS subgraph will likely move to a Namechain indexer. ensjs v4 already speaks both; minimal change required. |
| BankonInftAdapter cross-chain wiring | Currently L1 → 0G. Re-evaluate when Namechain bridging stabilizes — may simplify to L1 → Namechain → 0G via a single bridge. |

## Verification

```bash
# At any time, audit which records resolve via UR:
cd packages/core
pnpm exec node -e "
  const { createPublicClient, http } = require('viem');
  const { mainnet } = require('viem/chains');
  const { resolveProfile } = require('./dist/index.cjs');
  const client = createPublicClient({ chain: mainnet, transport: http() });
  resolveProfile({ client, name: 'jesse.base.eth' }).then(p => console.log(p));
"
# Expected: jesse.base.eth's CCIP-Read response served transparently
# through the Universal Resolver — even though jesse.base.eth lives
# off-chain on a Coinbase-run gateway.
```

## Further reading

- [ENSv2 Readiness](https://docs.ens.domains/web/ensv2-readiness) (canonical)
- [namechain](https://github.com/ensdomains/namechain) (formerly `contracts-v2`)
- [Universal Resolver](https://docs.ens.domains/resolvers/universal)
- [CCIP-Read](https://docs.ens.domains/resolvers/ccip-read)
- [ENSIP-15 name normalization](https://docs.ens.domains/ensip/15)
- [ENSIP-19 multichain reverse](https://ensips.ethereum.org/ensips/19)
- See [`ENSIP_COVERAGE.md`](ENSIP_COVERAGE.md) for the full implementation matrix.
