# DAIO voting UI (daio.pythai.net)

Static dapp for DAIO governance: connect wallet, list proposals, vote, create proposal.

## Files

- **index.html** — Page structure and links to daio.pythai.net, mindx.pythai.net, agenticplace.pythai.net
- **styled.css** — Layout and styling
- **dapp.js** — Wallet connection (MetaMask/ethers), proposal list, vote, create proposal
- **abi.js** — Minimal ABI for DAIOBridge (`getProposal`, `proposalCount`, `vote`, `createProposal`, etc.)

## Setup

1. Set **DAIO_BRIDGE_ADDRESS** in `dapp.js` to your deployed DAIOBridge contract address.
2. Optionally set **CHAIN_ID** in `dapp.js` (e.g. `1` for mainnet, `11155111` for Sepolia) to enforce network.
3. Serve the folder over HTTPS (e.g. for daio.pythai.net). Example: `npx serve .` or any static host.

## Usage

Users connect their wallet, see the list of proposals (by ID), vote for/against, and create new proposals (title, description, project ID). Proposal type is fixed to Generic (0) in the create form; target and execution data are left empty.

## References

- [ECOSYSTEM.md](../docs/daio/ECOSYSTEM.md) — interplanetaryfilesystem, mlodular, faicey, jaimla, Professor-Codephreak, pythai.net sites.
