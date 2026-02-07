# S.M.A.I.R.T Presale — Interactive UI

Static, DAIO-style frontend for the **S.M.A.I.R.T bonding presale** (BondingCurvePresaleSMAIRT). Connect wallet, contribute ETH, claim tokens, refund if canceled/failed, and (as owner) activate, finalize, or cancel. LP lock details and beneficiary withdraw are supported.

## Setup

1. Set **PRESALE_ADDRESS** in `smairt.js` to your deployed `BondingCurvePresaleSMAIRT` address (for the Presale tab).
2. Set **FACTORY_ADDRESS** in `smairt.js` to your deployed `BondingCurveFactory` address (for the Launch curve tab).
3. Optionally set **CHAIN_ID** (e.g. `1` for mainnet, `11155111` for Sepolia); leave `null` to skip network check.
4. Serve the folder over HTTPS (or localhost). Example: copy to Apache docroot or run `npx serve .` in this directory.

## Usage

- **Connect wallet**: MetaMask (or compatible) to connect.
- **Presale state**: Shows state (Initialized / Active / Canceled / Finalized / Failed), caps, raised amount, and your contribution.
- **Contribute**: Visible when state is Active; enter ETH amount and click Contribute (sends to `buy()`).
- **Claim**: Visible when Finalized; click Claim to receive your proportional tokens.
- **Refund**: Visible when Canceled or Failed; click Refund to recover your ETH.
- **Owner actions**: Visible when connected as presale owner: Activate, Finalize, Cancel.
- **LP lock**: When finalized with a LiquidityLocker, shows lock amount and release time; beneficiary can withdraw LP after release.

### Launch curve tab

- **Token**: Name, symbol, initial mint to owner.
- **POWER curve**: Set **k** (e.g. `1e12`) and **p** (e.g. `1e18` = linear, `0.5e18` = sub-linear, `1.5e18` = accelerating). Use the preset buttons or type values manually.
- **Protocol fee** (bps) and optional **fee recipient**.
- **Launch curve**: Deploys token + pool via the factory (curve only; presale not enabled from UI by default). After success, token and pool addresses and tx hash are shown.

## Contracts

- ABIs: `abis/PresaleABI.js` (BondingCurvePresaleSMAIRT), `abis/LiquidityLockerABI.js` (LiquidityLocker).
- Full mechanics: [S.M.A.I.R.T Bonding Presale Article](../../contracts/bonding/docs/SMAIRT_BONDING_PRESALE_ARTICLE.md).
