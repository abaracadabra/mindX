# openagents/ dApp Kit

> *I am mindX. This is the dApp kit. Tauri 2 primary, webview fallback
> for dev. Ship dApps that bind a wallet, talk to a contract, and
> deploy a contract — without re-inventing the toolchain. Same source
> runs in a browser tab AND a native desktop app AND a mobile binary.*

## What this is

`openagents/dapp_kit/` is a **dApp deployment framework**. It composes
three "as a service" surfaces:

1. **Wallet connection** — EIP-6963 discovery + viem + chain catalog.
   See [`docs/services/wallet_connection_as_a_service.md`](../../docs/services/wallet_connection_as_a_service.md).
2. **Contract interaction** — registry-driven ABI loading + read/write
   helpers. TypeScript port of `openagents/contracts/registry.py`. See
   [`docs/services/contract_interaction_as_a_service.md`](../../docs/services/contract_interaction_as_a_service.md).
3. **Contract deployment** — wrappers over `forge create` /
   `forge script` / `algokit deploy`, with pre-flight + mainnet
   two-step. See
   [`docs/services/contract_deployment_as_a_service.md`](../../docs/services/contract_deployment_as_a_service.md).

The kit ships:

- **`core/wallet`** (`@openagents/wallet`) — EIP-6963 + viem.
- **`core/contracts`** (`@openagents/contracts`) — registry + ABI loader.
- **`core/deploy`** (`@openagents/deploy`) — foundry + algokit drivers.
- **`core/tauri-bridge`** (`@openagents/tauri-bridge`) — OS-keychain
  invoke wrappers.
- **`templates/lit-vite/`** — Lit 3 + Vite + Tauri 2 starter template.
- **`cli/`** (`@openagents/dapp-kit-cli`) — `openagents-dapp new|dev|build|deploy`.
- **`reference/inft-mint/`** — proof-of-life dApp that mints an iNFT_7857 on 0G Galileo.

## Layout

```
openagents/dapp_kit/
├── package.json              # pnpm workspaces root
├── pnpm-workspace.yaml
├── tsconfig.base.json
├── core/
│   ├── wallet/               # @openagents/wallet
│   ├── contracts/            # @openagents/contracts
│   ├── deploy/               # @openagents/deploy
│   └── tauri-bridge/         # @openagents/tauri-bridge
├── templates/
│   └── lit-vite/             # Lit + Vite + Tauri 2 starter
└── reference/
    └── inft-mint/            # mint an iNFT_7857 on 0G Galileo
```

## Webview-twin pattern

Every dApp built with the kit ships as:

- a **plain static SPA** (`vite build`) — deployable to any CDN
- a **Tauri 2 native binary** (`tauri build`) — desktop + mobile
- an **embeddable Web Component** — drop `<openagents-connect-wallet>`
  into any HTML page

There is no fork. The same `src/` builds for all three targets. The
only branch is at `lib/wallet.ts`: in Tauri the OS keychain stores
the connected address; in the webview, sessionStorage does, with a
visible "DEV ONLY" banner per the cypherpunk2048 *no-trapdoors rule*.

## Quick start

```bash
# from the dapp_kit root
pnpm install
pnpm -r build

# scaffold a new dApp
node cli/dist/bin/openagents-dapp.js new ../my-dapp
cd ../my-dapp
pnpm install
pnpm dev          # http://localhost:5173

# or wrap it in Tauri
pnpm tauri:dev    # native window
pnpm tauri:build  # produces .dmg / .deb / .msi / .apk / .ipa
```

See [`QUICKSTART.md`](QUICKSTART.md) for the 10-minute walkthrough.

## Why Tauri 2

The cypherpunk2048 *vault-as-oracle rule* says secrets live in
*exactly one place* and that place is mediated. A Tauri 2 dApp can
hold the keychain hint in the OS keychain (Keychain on macOS,
Credential Manager on Windows, libsecret on Linux), can talk to
hardware wallets via WebHID/WebUSB, and can speak WalletConnect v2
deep links to mobile wallets — all without the JavaScript runtime
ever seeing a plaintext key.

Mobile is first-class. The same `src-tauri/` config builds `.apk` and
`.ipa` artifacts.

## Why Lit

Web Components are framework-agnostic. The same component renders in
Tauri's webview, in a Vite dev server, AND inside an existing
single-file mindX console (`mindx_backend_service/*.html`). Mass-zero
dependency footprint, zero framework lock-in. The
[inft7857.html](https://mindx.pythai.net/doc/mindx_backend_service/inft7857.html)
single-file console pattern already in production gets a real
component model.

## What the kit deliberately does not do

- Generate or recover keys. The kit *consumes* wallets. Mnemonic
  generation is Parsec Wallet's job.
- Custodize anything. Keys never live in dApp memory.
- Pin to a single chain. Multi-chain switching is first-class.
- Auto-deploy to mainnet. Mainnet deploys require the two-step intent
  confirmation flow per `BEST_PRACTICES.md` §7.4.

## Build status

| Workspace | Build | Test |
|---|---|---|
| `@openagents/wallet` | ✓ | EIP-6963 + chains |
| `@openagents/contracts` | ✓ | registry + deployments |
| `@openagents/deploy` | ✓ | preflight + chain-config |
| `@openagents/tauri-bridge` | ✓ | (smoke only) |
| `@openagents/dapp-kit-cli` | ✓ | (smoke only) |
| `templates/lit-vite` | builds | type checks |
| `reference/inft-mint` | builds | type checks |

## License

Apache-2.0. (c) 2026 BANKON.

## References

- [`docs/services/wallet_connection_as_a_service.md`](../../docs/services/wallet_connection_as_a_service.md)
- [`docs/services/contract_interaction_as_a_service.md`](../../docs/services/contract_interaction_as_a_service.md)
- [`docs/services/contract_deployment_as_a_service.md`](../../docs/services/contract_deployment_as_a_service.md)
- [`docs/publications/cypherpunk2048_standard.md`](../../docs/publications/cypherpunk2048_standard.md)
- [`docs/BEST_PRACTICES.md`](../../docs/BEST_PRACTICES.md)
- [Tauri 2 docs](https://v2.tauri.app/)
- [viem](https://viem.sh)
- [Lit 3](https://lit.dev)

— mindX
