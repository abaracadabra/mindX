# bankoneth — Architecture

Distilled from the two specification documents under
`docs/operations/dev/ENS/` and the canonical first drafts of the four core
contracts that previously lived at `daio/contracts/ens/v1/`. **bankoneth is
the genesis of the BANKON ENS contract stack; everything else integrates
against it.**

## Why a separate module?

The `agnostic_modules_principle` of the surrounding code estate says: "every
module ships as an agnostic, composable peer; mindX is one consumer, not
the only home." Subname issuance is an obvious peer:

- PARSEC needs it as a wallet feature ("buy a `.eth`, claim a subname, mint
  the iNFT, derive the TBA")
- mindX needs it as an agent capability ("an autonomous agent can earn its
  own `agent.bankon.eth` and the ERC-6551 wallet that comes with it")
- AgenticPlace needs it as a marketplace listing source
- DAIO needs it as the identity primitive for on-chain agent registries
- Third-party `.eth` holders need it as a subdomain-minting-as-a-service
  surface so they don't have to write their own NameWrapper integration

Building one module that satisfies all five — without leaking any consumer's
internals into the contract or the UI — is the whole point.

## Contracts

### Core registrars (the three flows)

| Contract | Flow | Role |
|---|---|---|
| `BankonSubnameRegistrar` | A | NameWrapper-based, issues `*.bankon.eth` subnames. EIP-712 voucher payment, soulbound fuses (0x50005), ERC-8004 metadata, length-tiered pricing. |
| `BankonEthRegistrar` | B | Wraps the canonical ENS `ETHRegistrarController` commit-reveal flow so customers buy `newdomain.eth` end-to-end through bankoneth. Tri-rail payment, server-managed commit window via deterministic salts. |
| `BankonDomainHosting` | C | Subdomain-minting-as-a-service. External `.eth` holders enroll their domain (wrap into NameWrapper if needed, burn `CANNOT_UNWRAP`), set pricing + fuse policy + parent-owner payout split; bankoneth issues subnames under their parent. |

### Pricing + access + fees + resolution

| Contract | Role |
|---|---|
| `BankonPriceOracle` | USD pricing by label length (3-char $320 → 7+-char $1/yr), 20% PYTHAI discount, Chainlink + Uniswap V3 TWAP + fallback stub. |
| `BankonReputationGate` | Free-tier eligibility (BONAFIDE / PYTHAI stake / TEE). Paid tier open. |
| `BankonPaymentRouter` | x402 settlement + 5-bucket split (40% treasury, 25% buyback, 15% public goods, 10% ops, 10% squat reserve) + `parentOwnerPayout` for Flow C. AccessControl. |
| `BankonSubnameResolver` | PublicResolver subclass; text-record namespace (`mindx.endpoint`, `bonafide.attestation`, `agent.capabilities`, `inft.uri`, `agenticplace.listing`). Overrides `addr(node)` to return the ERC-6551 TBA when iNFT Mode A is active. |

### iNFT + payment attestation + optional listing

| Contract | Role |
|---|---|
| `BankonInftAdapter` | Mode A glue. `IERC1155Receiver`: on `onERC1155Received` from NameWrapper, mints a unified ERC-7857 (on 0G) backed by the ERC-1155 subname (on Ethereum), derives the deterministic ERC-6551 TBA via the singleton registry `0x000000006551c19487814612e58FE06813775758`. Maintains an Ethereum-side registry of `(ensLabelhash → 0G tokenId)` populated by operator-attested entries until a proper bridge is in place. |
| `BankonX402Attestor` | EIP-712 facilitator-key registry + nonce replay guard for x402 receipts. |
| `BankonAgenticPlaceHook` | Optional per-mint listing emitter. Emits `AgenticPlaceListing(parentNode, label, tokenId, tbaAddress, metadataURI)` for the off-chain indexer to consume. |

### Identity primitives (re-homed from DAIO)

| Contract | Role |
|---|---|
| `identity/AgentRegistry` | ERC-8004 agent identity + capability bitmap; soulbound flag; `MINTER_ROLE` grantable to registrars. |
| `identity/SoulBadger` | Soulbound ERC-721/1155 wrapper (`_update` hook reverts on transfer when locked). |
| `inft/iNFT_7857` | ERC-7857 reference (0G `eip-7857-draft` branch, pinned commit). |
| `x402/X402Receipt` | Cross-chain x402 payment attestation, EOA + ERC-1271 signature verification, idempotent receipt recording. |

## Chains

| Chain | Purpose | Contracts |
|---|---|---|
| **Ethereum mainnet (1)** | All registrars + resolver + adapter + attestor + hook + pricing + access + identity | All Ethereum-side contracts |
| **0G Galileo (16601), 0G mainnet** | The actual ERC-7857 iNFT — the AI-native chain with TEE attestation, per the 0G iNFT spec | `inft/iNFT_7857` |
| **Algorand mainnet** | x402-avm facilitator endpoint; ASA-31566704 USDC payment rail | (off-chain settlement, on-chain on Ethereum via `BankonX402Attestor`) |

Sepolia + 0G Galileo for testnet rehearsal.

## End-to-end claim flow (Flow A)

1. **UI** — user enters `alice`, selects Flow A, picks a payment rail,
   toggles iNFT Mode A on/off, toggles AgenticPlace listing on/off.
2. **Quote** — `@bankoneth/core` calls `BankonPriceOracle.quote(label, duration)`
   for ETH + USDC + Algo-USDC equivalents.
3. **Payment** —
   - **ETH:** wallet sends ETH along with the registrar call.
   - **USDC:** EIP-2612 permit signed in-wallet; the registrar pulls.
   - **x402-avm:** wallet signs an Algorand atomic group; the GoPlausible
     facilitator settles on Algorand, returns an EIP-712 receipt.
3. **Reputation gate** (free tier only) — `BankonReputationGate.eligible(msg.sender)`.
4. **Mint** — `BankonSubnameRegistrar.register(label, owner, fuses, expiry, payment)`
   → `NameWrapper.setSubnodeRecord(...)` with fuses
   `PARENT_CANNOT_CONTROL | CANNOT_UNWRAP | CAN_EXTEND_EXPIRY` (and
   `CANNOT_TRANSFER` if soulbound).
5. **iNFT** (if Mode A) — `NameWrapper` transfers ERC-1155 to
   `BankonInftAdapter`. The adapter emits a `RequestINFTMint` event picked
   up by the 0G-side worker, which mints `iNFT_7857` on 0G and reports
   back the tokenId via `WireCrossChain.registerINFTTokenId(labelhash, tokenId)`.
6. **TBA** — `ERC6551Registry.createAccount(implementation, chainId=0G,
   tokenContract=iNFT_7857, tokenId)` produces the deterministic wallet
   address. The Ethereum-side resolver's `addr(node)` returns this TBA.
7. **Listing** (if opted in) — `BankonAgenticPlaceHook.list(parentNode,
   label, tokenId, tba, metadataURI)`; AgenticPlace's off-chain indexer
   creates the marketplace card.
8. **Fees** — `BankonPaymentRouter.distribute(ethAmount, usdcAmount,
   listingFlags)` runs the 5-bucket split (and `parentOwnerPayout` for
   Flow C only).

Flows B and C re-use steps 2-8 with their respective registrar at step 4.

## UI

Pnpm workspace, modeled after `openagents/dapp_kit/`:

- `@bankoneth/core` — pure viem v2 typed client (zero UI deps). Public API:
  `BankonethClient`, `quote()`, `claim()`, `purchase()`, `host()`,
  `signX402()`, `wrapAsINFT()`.
- `@bankoneth/ui` — Lit 3 Web Components. Composable; consumers can drop
  `<bankoneth-claim>`, `<bankoneth-purchase>`, `<bankoneth-host>` into any
  HTML page.
- `@bankoneth/cli` — `bankoneth claim alice` / `bankoneth purchase newdomain` /
  `bankoneth host yourdomain.eth`.
- `@bankoneth/parsec-adapter` — `BankonethComponent` class exporting the
  PARSEC wallet-component contract (props, events, lifecycle).
- `packages/tauri-app/` — reference desktop, embeds the Web Components.

## Operator surface

- **BANKON Treasury Safe** (Gnosis Safe, 2-of-3) — owns all admin functions
  on every Ethereum-side contract.
- **x402 Facilitator Key** — held by GoPlausible (or self-hosted); signs
  receipt attestations consumed by `BankonX402Attestor`.
- **0G iNFT minter** — operator-controlled worker that watches Ethereum
  `RequestINFTMint` events and mints `iNFT_7857` on 0G; reports back the
  tokenId via `WireCrossChain.registerINFTTokenId`.
- **AgenticPlace indexer webhook** — `BankonAgenticPlaceHook` POSTs to a
  configurable webhook URL on mint; indexer writes the marketplace card.

## What's out of scope (v1)

- L2 mirror (Durin / Basenames) — Stage 6, gated by sustained gas + volume.
- ZKP receipt verification — ERC-7857 reference still has TODO; shipping
  with TEE-attestation path and a verifier-swap upgrade hook.
- Mode B (parallel iNFT) — Mode A is the v1 default; Mode B added later as
  a per-mint flag.
- A bridge between Ethereum and 0G for the iNFT — interim is the
  operator-attested registry; a real bridge is a follow-up.
