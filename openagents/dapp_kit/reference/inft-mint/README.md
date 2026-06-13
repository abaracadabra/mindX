# inft-mint — reference dApp

Mints an `iNFT_7857` on **0G Galileo** using the openagents/ dApp kit.
Exercises the full pipeline:

1. **Wallet connection** via EIP-6963 → `@openagents/wallet`
2. **Chain switch** to 0G Galileo (chain id 16601)
3. **Contract write** via `@openagents/contracts` → `iNFT_7857.mint(parentRoot, cid, sealedMetadata)`
4. **Receipt wait + event decode** to surface the new token id

## Run as web

```bash
pnpm install
pnpm dev   # http://127.0.0.1:5174
```

## Run as Tauri native

```bash
pnpm tauri:dev    # native window
pnpm tauri:build  # produces .dmg / .deb / .msi / .apk / .ipa
```

## Deployment record

The dApp reads `public/deployments/0g-galileo.json` at runtime to find the
`iNFT_7857` address. The placeholder ships with zero addresses; fill in
real addresses after running `openagents/deploy/deploy_galileo.sh`. The
record format is identical to `openagents/deployments/*.json` (same
shape consumed by `openagents/contracts/registry.py`).

## What the reference proves

- The kit produces a real dApp that *minteably* talks to a real
  contract.
- Same `src/` runs in browser AND Tauri shell with zero source changes.
- The Lit components are reusable elsewhere (embed `<inft-mint-app>`
  in any HTML page that imports the bundle).

— mindX
