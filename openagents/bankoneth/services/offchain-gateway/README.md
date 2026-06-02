# bankoneth offchain-gateway

[Phase 2.2](../../docs/specs/CCIP_READ_REGISTRAR.md) — single-file Bun + Hono
CCIP-Read (EIP-3668) gateway for `BankonOffchainResolver`.

Receives queries from the on-chain resolver via the EIP-3668
`OffchainLookup` handshake, looks up records in a JSON store
(rehearsal-grade; production: SQLite + IPFS via Lighthouse), EIP-712
signs the response against an allowlisted signer key, returns JSON.

Mirrors the gateway pattern from
[gskril/ens-offchain-registrar](https://github.com/gskril/ens-offchain-registrar)
+ the ENS docs' CCIP-Read reference.

## Quick start

```bash
cd services/offchain-gateway
bun install

# Required env
export RESOLVER_ADDR=0x...                # the deployed BankonOffchainResolver
export SIGNER_PK=0x...                    # the gateway signer's private key
export PARENT_NODE=$(cast namehash bankon.eth)

# Optional env
export GATEWAY_PORT=8888                  # default 8888
export CHAIN_ID=1                         # default 1 (mainnet)
export STORE_PATH=./gateway-records.json  # default ./gateway-records.json
export TTL_SECONDS=3600                   # default 3600 (1 hour)
export ADMIN_SECRET=...                   # optional, gates POST /admin/claims

bun run dev
```

## Endpoints

### `POST /`
CCIP-Read entry point per [EIP-3668](https://eips.ethereum.org/EIPS/eip-3668).
The client sends:

```json
{
  "sender": "0x<RESOLVER_ADDR>",
  "data":   "0x<calldata>"
}
```

Where `data` is the resolver method calldata (`addr(node)`,
`addr(node,coinType)`, `text(node,key)`, or `contenthash(node)`).

The gateway:

1. Validates `sender` matches the configured `RESOLVER_ADDR`.
2. Decodes the calldata against known selectors.
3. Looks up the record by `node` (= `keccak256(parentNode || labelhash)`).
4. ABI-encodes the result.
5. EIP-712-signs `(result, expires, sender, keccak256(data))`.
6. Returns `{ "data": "0x<abi(result, expires, signature)>" }`.

The client then passes the response to
`BankonOffchainResolver.resolveWithProof(response, extraData)` on chain.

### `GET /health`
Returns `{ ok, records, signer, resolver, chainId }`. Hook up to your
uptime monitor.

### `POST /admin/claims`
Operator-only — gated by `Authorization: Bearer $ADMIN_SECRET`.

```json
{
  "label":      "alice",
  "owner":      "0x...",
  "recordsCid": "bafy..."
}
```

Persists a new subname record. A separate watcher (not embedded here) is
expected to listen for `OffchainSubnameClaimed` events from
`BankonOffchainRegistrar.sol` and POST them here, with the records pulled
from the optional IPFS CID. The MVP store is a JSON file; production
should swap in SQLite + Lighthouse-mirrored IPFS.

## EIP-712 domain

The contract verifies signatures against:

```
domain   : BankonOffchainResolver v1, chainId, verifyingContract = resolver
typehash : OffchainLookupResponse(bytes result,uint64 expires,address sender,bytes32 callHash)
```

The `callHash = keccak256(data)` binding prevents a gateway from
substituting a response for a different query.

## Signer rotation

The on-chain resolver has `SIGNER_ROLE` granted to one or more EOAs
(multi-sig friendly). When rotating:

1. Admin calls `BankonOffchainResolver.grantSigner(newSigner)`.
2. Update `SIGNER_PK` env on the gateway, restart.
3. Admin calls `BankonOffchainResolver.revokeSigner(oldSigner)`.

In-flight signed responses from the old signer remain valid until their
embedded `expires` lapses; tune `TTL_SECONDS` to bound the worst-case
revocation window.

## Production checklist

- [ ] Replace JSON store with SQLite (`bun:sqlite` is built in).
- [ ] Add Lighthouse IPFS mirror for record bundles (
  `agents/storage/lighthouse_provider.py`-equivalent in TS).
- [ ] Run behind a TLS-terminating proxy (Caddy / nginx / Apache).
- [ ] Rate-limit `POST /` per IP (Hono middleware).
- [ ] Pin the signer key inside the BANKON Vault (not raw env).
- [ ] Run the event watcher as a separate process (e.g. with
  `viem.watchEvent` against `BankonOffchainRegistrar`).
- [ ] Operator runbook: `docs/specs/CCIP_READ_REGISTRAR.md`.
