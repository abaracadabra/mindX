# Agent Identity Management as a Service

bankoneth turns "an agent needs a verifiable, resolvable, ownable identity" into a
few clicks (or one `@bankoneth/core` call). The contracts already exist; this doc
shows how they compose and where each step is surfaced in the dApps.

## The five primitives

| Concern | Contract | dApp surface |
|---|---|---|
| Human-readable name | `BankonSubnameRegistrar` (`*.bankon.eth`) | bankoneth.html → **Claim a subname** |
| Agent record + capabilities | `AgentRegistry` (ERC-8004-aligned) | bankoneth.html → **Register an agent** |
| Resolution (addr + text records) | `BankonSubnameResolver` | bankoneth.html → **Resolve / lookup** |
| Intelligence + memory NFT | `iNFT_7857` (ERC-7857, on 0G) | inft.html → **Mint / bind / authorize** |
| Auth gating for services | `BankonAuthGate` (SIWE / ENS-gated) | generic explorer + your backend |
| Marketplace presence | `BankonAgenticPlaceHook` / `iNFT.offerOnAgenticPlace` | "List on AgenticPlace" toggles |

## The canonical flow (agent onboarding)

1. **Claim** `alice.bankon.eth` — `registerFree` (reputation-gated) or `register` (paid).
   The subname is soulbound by default (fuses `0x50005`).
2. **Register the agent** — `AgentRegistry.register(owner, agentId, linkedINFT, capabilityBitmap, attestationURI)`
   mints the ERC-8004 identity. Use `alice.bankon.eth` as `agentId`.
3. **Mint the iNFT** (optional, on 0G) — `iNFT_7857.mintAgent(...)` anchors the encrypted
   intelligence content root; `bindAgentId(tokenId, "alice.bankon.eth")` links it back, and
   `linkedINFT_7857` on the AgentRegistry record points forward.
4. **Records** — `BankonSubnameResolver.setText(node, "agent.capabilities", …)`,
   `setText(node, "mindx.endpoint", …)`, `addr(node)` (returns the ERC-6551 TBA when iNFT
   Mode A is active). All readable via **Resolve / lookup**.
5. **Gate your service** — downstream services verify "caller controls `alice.bankon.eth`"
   with `BankonAuthGate.verifyOwnsLabel(...)` or `verifyTextRecord(...)` (EIP-4361 SIWE).
   See `docs/ENSAUTH_GATING.md`.
6. **List** (optional) — flip "List on AgenticPlace" to emit `BankonAgenticPlaceHook.list(...)`
   (or `iNFT.offerOnAgenticPlace(...)`); agenticplace.pythai.net's indexer writes the card.

## Where it runs

- **bankon.pythai.net / agenticplace.pythai.net** — serve `packages/web/bankoneth.html`
  (+ `inft.html`) as the public, self-service identity console.
- **parsec-wallet** — the same flows as a native view (`@bankoneth/parsec-view`).
- **mindX agents** — `clients/python/agent_mint_service.py` mints `<addr>.bankon.eth`
  autonomously for agents holding `MINDX_AGENT_MINTER_ROLE`; `subdomain_issuer.py` is the
  general async client (paid / free / renew).
- **Programmatic** — `@bankoneth/core` (`claim`, `purchase`, `host`, `wrapAsINFT`) and
  `@bankoneth/cli`.

## Notes

- AgenticPlace listing is a **separate** call from the mint (a distinct hook/marketplace
  function), so the dApp toggles point you to the explorer's `list` / `offerOnAgenticPlace`
  rather than bundling it into the mint transaction.
- iNFT lives on 0G (separate chain) — hence the separate `inft.html` page + `iNFTabi.js`.
