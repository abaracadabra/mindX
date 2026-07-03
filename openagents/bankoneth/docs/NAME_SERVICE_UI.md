# Name-service + Marketspace UIs (modular expansion, MVP kept simple)

Per the brief: **keep the simple storefront as MVP**, add **separate modular UIs**. Two new pages join
the existing surface; all reuse `app-common.js` + `bankon-forms.js` + `styled.css` + `webgl-bg.js` + `gfx/`.

| Page | Purpose |
|---|---|
| `index.html` (MVP, unchanged) | storefront: buy a `*.bankon.eth` |
| **`name-service.html`** (new) | *ENS naming as a service*: mint a named agent iNFT (Mode A/B), compute its ERC-6551 **TBA wallet** live, **name any contract** `myapp.bankon.eth`, generic canonical-7857 read/write |
| **`marketspace.html`** (new) | *ARC agent economy*: browse listings, list an iNFT agent, reputation lookup, generic explorer over the 4 ARC contracts |
| `create-eth.html`, `bankoneth.html`, `inft.html` | existing |

Cross-linked from the storefront footer ("Name your contracts →", "Agent marketspace →").

## How each guided action maps on-chain
- **Mint agent iNFT** → `bankon_inft_registrar.mintWithX402(...)` (x402 receipt from the gate
  `/x402/settle` facilitator) → unified/parallel iNFT + ERC-6551 TBA.
- **TBA wallet** → canonical registry `0x0000…5758` `account(impl, salt, chainId, iNFT, tokenId)` view —
  works live against any chain that has the registry (mainnet/fork), no bankon deploy needed.
- **Name a contract** → `BankonSubnameResolver.setAddr(namehash(name), contract)` (you must hold the subname).
- **List an agent** → `bankon_agent_market.listAgent(tokenId, priceUsdc6, uri)` → `AgentListed` event.
- **Reputation** → `AgentReputationRegistry.getAgentProfile/getAgentMetrics`.

## Modular expansion model
New UIs are standalone pages reading the manifest (`public/bankon.contracts.json`) + ABIs
(`public/abis/`). Add a contract → add it to `script/export-abis.mjs` `CONTRACTS` (with a `category`) →
re-run → a new page (or a new tab) consumes it. The gate (`backend/gate.py`) leaves unlisted public
pages visitor-open by default, so new pages need no gate change. Writes are wallet-signed; on-chain
AccessControl enforces authority.

## Verified
Inline scripts `node --check` clean; pages serve 200 with all ABIs + `caip2.json`; manifest lists 26
contracts (6 `inft7857`, 4 `arc`). Live writes need the contracts deployed (anvil-fork / mainnet).
