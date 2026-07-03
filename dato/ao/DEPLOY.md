# Deploying `dato.lua` to a real AO process (via parsec-wallet)

This is the **real-AO** counterpart to the dry-run `dato/ao/spawn.py`. It spawns
`dato.lua` as a live AO process, **signed by a parsec wallet** — tying dato's
inclusion to `parsec/parsec-wallet` as the modular option.

## How it works

- **Wallet** — a parsec-derived Arweave key (`parsec-wallet`'s own
  `src/lib/arweave/seed.ts: deriveJwkFromMnemonic`, BIP-39 → RSA-4096). Saved to
  `dato/data/parsec_wallet.json` (gitignored) and reused on subsequent runs.
- **Transport** — `@permaweb/aoconnect` (the dep parsec-wallet's AO subset is built on).
- **Boot** — `dato.lua` is loaded via the AOS `On-Boot: Data` tag, prefixed with an
  owner preamble so the process boots **already owned by the DAIO**, with the parsec
  wallet recorded as `Deployer` + founding member, and the dato name seeded.

## Run

```bash
cd ~/parsec/parsec-wallet
node_modules/.bin/tsx scripts/deploy-dato-ao.ts            # legacynet (default)
# parameters via env:
DATO_HANDLE=archive DATO_TIER=immortal DATO_ROOT=blockchain \
MINDX_DAIO_ADDRESS=<daio-arweave-addr> \
node_modules/.bin/tsx scripts/deploy-dato-ao.ts
```

On success it writes `dato/data/ao_process.json` with the **process id** + the
parsec wallet recovery material, and probes the process `Info` handler.

## Modes

| `AO_MODE` | Network | Needs |
|-----------|---------|-------|
| `legacy` (default) | AO legacynet — module `Do_Uc2Sju…`, scheduler `_GQ33Bk…`, MU/SU/CU `*.ao-testnet.xyz` | nothing (no funding) |
| `mainnet` | AO mainnet / HyperBEAM | `AO_URL=<hyperbeam node>` + a funded wallet; optional `AO_MODULE` / `AO_SCHEDULER` |

```bash
AO_MODE=mainnet AO_URL=https://<your-hyperbeam-node> \
node_modules/.bin/tsx scripts/deploy-dato-ao.ts
```

## Status (2026-06-17) — verified path, endpoint-blocked

The full pipeline is **verified working**: parsec wallet derivation, ANS-104
RSA-PSS signing, scheduler resolution (`_GQ33Bk…` → `su-router.ao-testnet.xyz`),
and `On-Boot` bundling of `dato.lua`.

The live spawn is currently **blocked by the AO network, not by this code**: the
legacynet MU (`mu.ao-testnet.xyz`, up at `/`) returns
`500 TypeError: Cannot read properties of null (reading 'toLowerCase')` on spawn —
reproduced with a **minimal bare spawn** (no dato payload), so it is endpoint-side.
AO mainnet (HyperBEAM, e.g. `forward.computer`) was unreachable from the build
sandbox. The script records this in `dato/data/ao_process.json` as
`{"status":"blocked", …, "diagnosis": …}` and exits non-zero.

**To finish:** rerun when the legacynet MU recovers, or set `AO_MODE=mainnet
AO_URL=<reachable HyperBEAM node>` with a funded parsec wallet — the script is
parameterized and ready; no code change needed.

## Verify a live process

```bash
# Info (read-only dry-run) once spawned:
#   dryrun({ process: <id>, tags: [{name:'Action', value:'Info'}] })
# Join / Govern / Commit are sent as Action-tagged messages (see dato/ao/dato.lua handlers).
```
