# CCIP-Read Off-Chain Subname Registrar

Phase 2.2 — full spec for the bankoneth off-chain subname stack: the
on-chain `BankonOffchainResolver` + `BankonOffchainRegistrar` contracts
+ the Bun gateway at `services/offchain-gateway/`. Cost model: ~$0.01
per mint amortized vs ~$2.50 on-chain (NameWrapper slot + storage),
trading the on-chain write for a permanent dependency on the operator-
run gateway.

## Why off-chain

bankon.eth issuance scales linearly in gas per mint when using
NameWrapper. The market is on-chain ~12 mints/day at $2.50/mint = ~$30/
day. To unlock commercial issuance volume (thousands of subnames),
CCIP-Read offers the same UX (Universal Resolver follows the EIP-3668
handshake transparently) at near-zero per-mint cost.

Coinbase use this pattern for `*.cb.id`. Base name service uses it for
`*.base.eth`. ENS Labs published [a reference implementation](
https://github.com/gskril/ens-offchain-registrar). The trade-off
([docs.ens.domains/resolvers/ccip-read](https://docs.ens.domains/resolvers/ccip-read)):
records depend on the gateway's uptime; censoring or losing the gateway
means records are unreachable until restored. Operators must commit to
running a redundant gateway + persistent record store (IPFS mirror).

## On-chain components

### `BankonOffchainResolver`
- Implements `IExtendedResolver.resolve(name, data)` → reverts with
  the EIP-3668 `OffchainLookup` error.
- Verifies signed responses via `resolveWithProof` (EIP-712 over
  `OffchainLookupResponse(bytes result, uint64 expires, address
  sender, bytes32 callHash)`).
- `SIGNER_ROLE` allowlist on the gateway's signing key, rotation-
  friendly via `grantSigner` / `revokeSigner`.
- Admin-settable gateway URL list (`setUrls`), so a future migration
  to a different gateway provider doesn't require a re-deploy.

### `BankonOffchainRegistrar`
- Same shape as Flow A's `BankonSubnameRegistrar.claim()`, but no
  NameWrapper write. Emits `OffchainSubnameClaimed(parentNode,
  labelhash, label, owner, recordsCid, paidUsd6)` for the gateway's
  event watcher to persist.
- Tri-rail payment (ETH / USDC permit / x402-avm).
- HIGH-3-pattern `sweep()` (fund-then-distribute).
- ENSIP-15 `setReverseName` admin (Phase 2.3).
- Duplicate guard on `claimed[keccak256(parent || labelhash)]`.

## Off-chain components

### Gateway (`services/offchain-gateway/`)
- Bun + Hono single-file service.
- `POST /` — EIP-3668 entry. Validates `sender == RESOLVER_ADDR`,
  decodes the four supported resolver selectors (`addr(node)`,
  `addr(node,coinType)`, `text(node,key)`, `contenthash(node)`),
  looks up the record, EIP-712-signs the response.
- `GET /health` — uptime probe.
- `POST /admin/claims` — bearer-auth endpoint the event watcher hits.
- Store: rehearsal-grade JSON file (`gateway-records.json`).
  Production: SQLite + Lighthouse-mirrored IPFS bundles.

### Event watcher (out of scope; operator builds)
A separate process listens for `OffchainSubnameClaimed` events from
`BankonOffchainRegistrar` and POSTs them to `/admin/claims`. Reference
shape:

```ts
import { watchContractEvent } from "viem";

watchContractEvent(client, {
  address: REGISTRAR,
  abi:     OFFCHAIN_REGISTRAR_ABI,
  eventName: "OffchainSubnameClaimed",
  onLogs: async (logs) => {
    for (const log of logs) {
      const { label, owner, recordsCid } = log.args!;
      await fetch(`${GATEWAY}/admin/claims`, {
        method: "POST",
        headers: { Authorization: `Bearer ${ADMIN_SECRET}` },
        body: JSON.stringify({ label, owner, recordsCid }),
      });
    }
  },
});
```

## The EIP-3668 handshake

```
┌─────────┐   ① resolve(name, data)                ┌────────────────────┐
│ Client  │ ─────────────────────────────────────► │ OffchainResolver   │
└─────────┘                                        └────────────────────┘
                                                          │
              ② revert OffchainLookup(                    │
                  sender, urls, callData,                 │
                  resolveWithProof.selector, extraData)   │
     ◄────────────────────────────────────────────────────┘

┌─────────┐  ③ POST { sender, data }              ┌────────────────────┐
│ Client  │ ─────────────────────────────────────► │  Bun Gateway       │
└─────────┘                                        └────────────────────┘
                                                          │
                          ④ lookup record                 │
                          ⑤ EIP-712 sign                  │
                   { data: 0x<abi(result, expires, sig)> }│
     ◄────────────────────────────────────────────────────┘

┌─────────┐  ⑥ resolveWithProof(response, extraData)  ┌────────────────────┐
│ Client  │ ─────────────────────────────────────► │ OffchainResolver   │
└─────────┘                                        └────────────────────┘
                                                          │
                      ⑦ verify sig + expiry + callHash    │
                         binding, return result           │
     ◄────────────────────────────────────────────────────┘
```

Steps ②–⑥ are handled transparently by viem / ethers / the Universal
Resolver — application code calls `client.getEnsAddress({ name: "alice.bankon.eth" })`
and gets the resolved address. The off-chain hop is invisible.

## EIP-712 binding

```
OffchainLookupResponse(
  bytes   result,
  uint64  expires,
  address sender,
  bytes32 callHash
)
```

- `result`: ABI-encoded answer (an `address`, `bytes`, or `string`
  depending on the resolver method invoked).
- `expires`: gateway-defined TTL. Default 1 hour. Beyond this the
  contract rejects the proof.
- `sender`: pin to the resolver address. Prevents cross-deploy reuse.
- `callHash`: `keccak256(data)`. Binds the proof to a specific query —
  the gateway can't substitute a response for a different question.

## Signer rotation

Each new gateway key:

1. Admin calls `resolver.grantSigner(newAddr)`.
2. Gateway operator updates `SIGNER_PK` env, restarts.
3. After a TTL window (default 1h), admin calls
   `resolver.revokeSigner(oldAddr)`.

The 1-hour window lets in-flight signed responses bleed off without
client-visible disruption.

## Production deploy

Operator-driven. Outline:

1. `forge script script/DeployOffchain.s.sol` (operator writes — not
   bundled in this commit; deploy resolver + registrar with the
   parent node + signer + URL list).
2. Configure `bankon.eth`'s resolver in ENS to point at the new
   `BankonOffchainResolver` (parallel to v1 + V2 — they cover the
   on-chain subname legacy + V2 modes; the offchain resolver handles
   ENSIP-10 wildcard for the new high-volume mints).
3. Stand up the gateway behind TLS, mount the SQLite + IPFS store.
4. Run the event watcher as a separate Bun process.
5. Test end-to-end: `viem.getEnsAddress({ name: "test.bankon.eth" })`
   should round-trip through the gateway without any caller-visible
   difference from on-chain Flow A.

## Cost model (mainnet, gas at 25 gwei)

| Operation | On-chain (Flow A) | Off-chain (Phase 2.2) |
|---|---|---|
| Mint subname | ~$2.50 (NameWrapper + resolver writes) | ~$0.01 amortized (gateway compute + IPFS pin) |
| Resolve subname | One `staticcall` to PublicResolver | One `staticcall` + one HTTP round-trip |
| Edit records | $0.10 per setText (resolver write) | Free (gateway mutation) |
| Reverse lookup | Same | Same (only forward is off-chain) |

## Known limitations

- **Gateway is a trust point.** Records depend on the operator
  publishing valid signatures. Mitigations: multiple signers, IPFS
  mirror of every record bundle, public auditability via the
  on-chain `OffchainSubnameClaimed` event log.
- **Signed responses are stateful.** Clients cache signatures up to
  `expires`. Rapid record edits may show stale data until the next
  refresh.
- **Not an ENSv2 native pattern.** Namechain may obsolete this layer
  in favour of native L2 reads (the Universal Resolver will be
  upgraded). Until then, CCIP-Read is the production-ready scaling
  path for ENS-on-L1.

## References

- [EIP-3668: CCIP Read](https://eips.ethereum.org/EIPS/eip-3668)
- [ENSIP-10: Wildcard Resolution](https://ensips.ethereum.org/ensips/10)
- [docs.ens.domains/resolvers/ccip-read](https://docs.ens.domains/resolvers/ccip-read)
- [gskril/ens-offchain-registrar](https://github.com/gskril/ens-offchain-registrar) (reference implementation)
- [unruggable-labs/unruggable-gateways](https://github.com/unruggable-labs/unruggable-gateways) (trustless rollup-proof variant)
