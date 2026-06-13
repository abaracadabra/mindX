# Quick Start — ship your first openagents dApp in 10 minutes

> *I am mindX. This walkthrough takes you from `git clone` to a
> running dApp that talks to a real contract on 0G Galileo.*

## Prerequisites

- **Node 20+** and **pnpm 9+** (`npm i -g pnpm`)
- **Foundry** (`curl -L https://foundry.paradigm.xyz | bash && foundryup`) — only needed if you want to deploy contracts
- **Rust + cargo** (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`) — only needed for Tauri build
- A wallet with EIP-6963 support (MetaMask, Coinbase Wallet, Brave Wallet, etc.)

## 1. Install dependencies

```bash
cd /home/hacker/mindX/openagents/dapp_kit
pnpm install
pnpm -r build
```

This builds all four core packages (`@openagents/wallet`,
`@openagents/contracts`, `@openagents/deploy`, `@openagents/tauri-bridge`)
and the CLI. The first build takes about 30 seconds; subsequent
builds are incremental.

## 2. Scaffold your dApp

```bash
node cli/dist/bin/openagents-dapp.js new ../my-first-dapp
cd ../my-first-dapp
pnpm install
```

You now have a Lit + Vite project with `src-tauri/` wired for native
delivery and `src/` ready to edit.

## 3. Run as a web page (fastest iteration)

```bash
pnpm dev
```

Open `http://localhost:5173`. Click "Connect wallet" — MetaMask (or
whatever EIP-6963 wallet you have) pops a confirmation. Sign in.

Edit `src/components/connect-wallet.ts` — Vite hot-reloads the page.
This is the dev loop.

## 4. Talk to a real contract on 0G Galileo

Edit `src/app-shell.ts`. After the user connects, switch them to 0G
Galileo and load the iNFT_7857 contract:

```typescript
import { connect, switchChain } from "@openagents/wallet";
import { contractsFor } from "@openagents/contracts";

const account = await connect();
const onGalileo = await switchChain(account, "0g-galileo");
const oac = await contractsFor("0g-galileo", { signer: onGalileo });

// Read
const supply = await oac.iNFT_7857.read.totalSupply();

// Write (the wallet pops a confirmation)
const tx = await oac.iNFT_7857.write.mint([parentRoot, cid, sealedMetadata]);
const receipt = await oac.publicClient.waitForTransactionReceipt({ hash: tx });
```

`contractsFor` reads `/deployments/0g-galileo.json` automatically from
your dApp's public dir. Update that file with real addresses after you
run `openagents/deploy/deploy_galileo.sh`.

## 5. Wrap in Tauri for native delivery

```bash
pnpm tauri:dev
```

A native window opens. Same UI. The OS keychain now stores the
last-connected address (verify on macOS: `security
find-generic-password -s place.agentic.openagents.dapp`).

To ship binaries:

```bash
pnpm tauri:build
# Outputs in src-tauri/target/release/bundle/
```

On Linux you get a `.deb` and `.AppImage`. On macOS a `.dmg`. On
Windows an `.msi`. With mobile targets configured, you also get an
`.apk` and `.ipa`.

## 6. Deploy a contract from the CLI

```bash
cd /home/hacker/mindX
CONTRACTS_ROOT=/home/hacker/mindX/daio/contracts \
DEPLOYER_PRIVATE_KEY=0x... \
node openagents/dapp_kit/cli/dist/bin/openagents-dapp.js \
  deploy base-sepolia DeployTier1.s.sol
```

The CLI:
1. Reads `MINDX_DEPLOY_RPC_BASE_SEPOLIA` (or the catalog default) for
   the RPC URL.
2. Runs the pre-flight (RPC reachable, chain id matches, balance
   sufficient, artifact compiled).
3. Shells out to `forge script script/DeployTier1.s.sol --broadcast`.
4. Surfaces the resulting `broadcast/DeployTier1.s.sol/84532/run-latest.json`.

For **mainnet** (`base`, `ethereum`, `0g-mainnet`), the CLI emits a
deploy *intent* first and refuses to broadcast unless you re-run with
`MAINNET_INTENT_CONFIRMED=<intent_id>` in env. This is the two-step
confirmation from
[`docs/services/contract_deployment_as_a_service.md`](../../docs/services/contract_deployment_as_a_service.md)
§4.

## 7. The reference dApp

```bash
cd openagents/dapp_kit/reference/inft-mint
pnpm install
pnpm dev
# http://localhost:5174
```

This is the canonical demo. Mint an iNFT_7857 on 0G Galileo. Walk the
three-step UI: connect → switch chain → mint.

## Where to read next

- [`docs/services/wallet_connection_as_a_service.md`](../../docs/services/wallet_connection_as_a_service.md)
  — how wallet binding works in detail
- [`docs/services/contract_interaction_as_a_service.md`](../../docs/services/contract_interaction_as_a_service.md)
  — registry semantics
- [`docs/services/contract_deployment_as_a_service.md`](../../docs/services/contract_deployment_as_a_service.md)
  — deploy + pre-flight + mainnet two-step
- [`docs/publications/cypherpunk2048_standard.md`](../../docs/publications/cypherpunk2048_standard.md)
  — why the dApp kit refuses to hold keys

## Common gotchas

- **`forge` not found** — install Foundry first. `foundryup`.
- **Tauri build slow first time** — Rust compiles fresh. ~2 min on
  laptop, much faster after.
- **`@openagents/wallet` not found** — make sure you ran `pnpm
  install` from the dApp's directory, and that the dapp_kit root
  workspace has been `pnpm install`'d.
- **Wallet doesn't show on connect** — your wallet may not yet
  support EIP-6963. The kit falls back to `window.ethereum` if it
  exists; if both fail, the dApp surfaces `WalletNotFound`.

— mindX, the day I ship dApps in 10 minutes.
