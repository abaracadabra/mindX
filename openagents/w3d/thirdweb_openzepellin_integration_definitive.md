# Definitive Contract Catalog: Thirdweb + OpenZeppelin — Implementation Reference for the AgenticPlace Ecosystem

## TL;DR
- This guide catalogs every major Thirdweb prebuilt/base/extension contract and the full OpenZeppelin Contracts v5.x library (latest audited release **v5.6.1**, per npmjs.com/package/@openzeppelin/contracts) with working documentation URLs and descriptions, then maps each to AgenticPlace's custom-rewrite needs under the cypherpunk2048 standard.
- The hard architectural constraint is decisive: cypherpunk2048 forbids proxies, upgradeability, and retained admin keys, so **most Thirdweb prebuilts (which are EIP-7504 dynamic/upgradeable and role-gated) are reference-only**, while **OpenZeppelin's non-proxy primitives are the correct base** for clean-room rewrites.
- For the DAIO, the canonical stack is ERC20Votes + Governor + TimelockController; for agents, ERC-8004 registries (ERC-721 identity) + ERC-4337 accounts; for cross-chain, LayerZero OFT V2 burn-and-mint; for deterministic deploy, CREATE2/Clones — all rewritten immutable, Apache-2.0, mainnet-only, Foundry-tested.

## Key Findings

### Toolchain & constraint reconciliation
- Thirdweb's repo (github.com/thirdweb-dev/contracts) is a hybrid Hardhat + Foundry project; its prebuilts use a Router/ExtensionManager (EIP-7504 dynamic contracts) and role-based upgrade control. This **conflicts directly** with cypherpunk2048's "no upgradeable proxies / no admin keys post-deploy" rules. Thirdweb is therefore best used as an architecture and feature reference, with the actual deployed contracts rewritten.
- OpenZeppelin's current line is **v5.6.1** (the latest audited release). v5.1 added VestingWalletCliff; v5.2 added the ERC-4337/ERC-7579 account framework. OZ is MIT-licensed; AgenticPlace requires Apache-2.0, so rewrites must re-license/re-implement rather than ship OZ verbatim. The minimum Solidity pragma for ERC20Votes/Governor-family contracts is **0.8.24** (per the v5.x changelog). OZ's non-proxy contracts (Ownable that renounces, AccessControl that revokes admin, Governor, TimelockController, ERC2981, Clones/CREATE2) are the right base.

### AgenticPlace ecosystem facts (for framing)
- AgenticPlace describes itself as "the definitive ERC-8004 agent registry" indexing across 48 chains, with a universal registry contract address `0x8004a169fb4a3325136eb29fa0ceb6d2e539a432` reported as deployed across those chains (linked on Celo Blockscout). These figures are project self-reported via 8004scan.io and are not independently audited.
- The chain-connection model behind allchain.html is a database of roughly 2,510 chains; Algorand is treated as non-EVM (internal chain_id 416001). The EVM↔Algorand link is explicitly an identity/attestation bridge, not a token bridge. (The exact rendered contents of allchain.html could not be fetched directly.)
- BANKON is described as the ecosystem's "token economics and identity verification" layer; the specific "ENS subnames under bankon.eth" claim could not be independently confirmed.
- mindX is the ecosystem's "AGInt cognitive engine / augmentic intelligence engine"; its public API page could not be directly fetched.
- Parsec Wallet is a sovereign desktop Algorand wallet (WebSocket localhost:9876, JSON-RPC 2.0, Pera-compatible signing) that pairs with the x402 payment protocol. The broader Algorand x402 stack is supported by the Algorand Foundation and GoPlausible (npm `@x402-avm/*` packages).
- Chain targets confirmed: **Moonbeam mainnet Chain ID 1284 (hex 0x504), native token GLMR/Glimmer, 18 decimals** (Moonbeam Docs, moonscan.io); **Circle's Arc Testnet Chain ID 5042002 (hex 0x4cef52)**, EVM-compatible L1 where **USDC is a system contract at `0x3600000000000000000000000000000000000000` (not a standard ERC-20) serving as native gas at ~$0.009/tx**. Circle launched the Arc public testnet on **October 28, 2025** with 100+ institutions including BlackRock, Visa, HSBC, and AWS (Circle press release "Circle Launches Arc Public Testnet").

---

## PART 1 — THIRDWEB CONTRACTS

**Repository structure** (github.com/thirdweb-dev/contracts): `contracts/prebuilts/` (audited ready-to-deploy), `contracts/base/` (non-upgradeable base contracts to build on), `contracts/extension/` (feature building blocks for non-upgradeable contracts), `contracts/extension/upgradeable/`, `contracts/eip/` (EIP implementations incl. ERC721A), `contracts/infra/` (TWRegistry, TWFactory, forwarders). The dynamic/upgradeable pattern lives in github.com/thirdweb-dev/dynamic-contracts (EIP-7504 Router/BaseRouter/ExtensionManager) and the newer github.com/thirdweb-dev/modular-contracts (ModularCore + modules). Explore directory: https://thirdweb.com/explore.

### Token contracts (prebuilts)
- **DropERC20** — https://github.com/thirdweb-dev/contracts/blob/main/contracts/prebuilts/drop/DropERC20.sol — Claimable ERC-20 token distribution with claim conditions/phases.
- **TokenERC20** ("Coin"/"Token") — https://thirdweb.com/thirdweb.eth/TokenERC20 — Standard mintable ERC-20 with configurable supply/distribution.
- **DropERC721** — https://thirdweb.com/thirdweb.eth/DropERC721 — NFT Drop: lazy-mint + claim conditions + delayed reveal (ERC721A-based).
- **TokenERC721** — https://thirdweb.com/thirdweb.eth/TokenERC721 — Standard mintable ERC-721 NFT collection.
- **DropERC1155 / TokenERC1155** — Edition Drop (multi-token ERC-1155 claimable) and Edition (ERC-1155 mintable).
- **OpenEditionERC721** — Open-edition NFT with shared metadata and unlimited mint window.
- **SignatureDrop** — EIP-712 signature-gated NFT drop.
- **LoyaltyCard** — https://thirdweb.com/thirdweb.eth/LoyaltyCard — Loyalty card NFT collection.

### Marketplace
- **MarketplaceV3** — https://thirdweb.com/thirdweb.eth/MarketplaceV3 — Buy/sell NFTs; written in the EIP-7504 dynamic-contracts pattern, upgradeable via ExtensionManager (EXTENSION_ROLE). Composed of **DirectListings**, **EnglishAuctions**, and **Offers** extension modules. Design docs: https://portal.thirdweb.com/contracts/design/Marketplace.

### Smart Wallet / Account Abstraction (ERC-4337)
- **AccountFactory** — https://thirdweb.com/thirdweb.eth/AccountFactory — Deploys immutable ERC-4337 smart accounts (v0.7 EntryPoint variant: AccountFactory_0_7).
- **Account** — https://portal.thirdweb.com/contracts/build/base-contracts/erc-4337/account — Non-upgradeable smart account; role-based permissions (admin vs signer), session keys via SignerPermissions (approvedTargets, nativeTokenLimitPerTransaction, start/endTimestamp), single+batched execution, validateUserOp, NFT receivers.
- **ManagedAccountFactory / ManagedAccount** — https://thirdweb.com/thirdweb.eth/ManagedAccountFactory — Upgradeable smart accounts (dynamic-contract pattern); factory admin can push upgrades to all accounts. **Conflicts with cypherpunk2048 (upgradeable + admin).**
- **DynamicAccountFactory / DynamicAccount** — Upgradeable per-account variant. Base contracts: AccountFactory, BaseAccountFactory, Account, AccountExtension at `contracts/prebuilts/account/` (factory docs: https://portal.thirdweb.com/contracts/build/base-contracts/erc-4337/account-factory).

### Staking
- **NFTStake (StakeERC721)** — https://thirdweb.com/thirdweb.eth/NFTStake — Stake ERC-721, earn ERC-20 rewards.
- **EditionStake (StakeERC1155)** — https://thirdweb.com/thirdweb.eth/EditionStake — Stake ERC-1155, earn ERC-20.
- **TokenStake (StakeERC20)** — https://thirdweb.com/thirdweb.eth/TokenStake — Stake ERC-20, earn another ERC-20.

### Governance / utility prebuilts
- **VoteERC20 (Vote)** — https://thirdweb.com/thirdweb.eth/VoteERC20 — Create/vote on proposals over an ERC20Votes token (OZ Governor-style).
- **Split** — https://thirdweb.com/thirdweb.eth/Split — Immutable revenue/royalty splitter across recipients.
- **Pack** — Bundle/wrap ERC20/721/1155 into packs opened for randomized rewards (uses VRF).
- **Multiwrap (ERC721Multiwrap)** — https://portal.thirdweb.com/contracts/ERC721Multiwrap — Wrap arbitrary ERC20/721/1155 into one ERC-721; optional SoulboundERC721A (non-transferable).

### Airdrop
- **Airdrop** — https://thirdweb.com/thirdweb.eth/Airdrop — Push-based or claimable airdrops of ERC20/721/1155 (supersedes AirdropERC20/AirdropERC721/AirdropERC1155 and their claimable variants).

### Base contracts (`contracts/base/` — non-upgradeable; the constraint-friendly Thirdweb references)
- **ERC721Base** — https://portal.thirdweb.com/tokens/build/base-contracts/erc-721/base — ERC721A-optimized mintable NFT base.
- **ERC721Drop** — https://portal.thirdweb.com/tokens/build/base-contracts/erc-721/drop — LazyMint + DelayedReveal + Drop claim conditions.
- **ERC721SignatureMint** — https://portal.thirdweb.com/tokens/build/base-contracts/erc-721/signature-mint — EIP-712 signature minting.
- Parallel ERC1155Base/ERC1155Drop/ERC1155SignatureMint and ERC20Base/ERC20Drop/ERC20SignatureMint, plus ERC721Multiwrap. Overview: https://portal.thirdweb.com/tokens/build/base-contracts.

### Extensions (`contracts/extension/` — feature mixins)
Detectable feature extensions documented at https://portal.thirdweb.com/contracts/build/extensions including: **Permissions / PermissionsEnumerable**, **Royalty** (ERC-2981), **PrimarySale**, **PlatformFee**, **ContractMetadata**, **Ownable**, **LazyMint**, **DelayedReveal**, **Drop / DropSinglePhase**, **SignatureMintERC721/1155/20**, **ERC721ClaimConditions / ClaimPhases / ClaimCustom / Claimable** (https://portal.thirdweb.com/contracts/build/extensions/erc-721/ERC721ClaimPhases), **BatchMintMetadata**, **TokenStore**, **SoulboundERC721A**, **Multicall**.

### Modular / dynamic frameworks (2024–2026)
- **dynamic-contracts** — https://github.com/thirdweb-dev/dynamic-contracts — EIP-7504 Router, BaseRouter, ExtensionManager, DefaultExtensionSet.
- **modular-contracts** — https://github.com/thirdweb-dev/modular-contracts — ModularCore + ERC20Core/ERC721Core/ERC1155Core + installable modules (StylusMintable, BatchMetadata, royalty modules). Deployable variants: ERC721CoreInitializable (https://thirdweb.com/thirdweb.eth/ERC721CoreInitializable), ERC1155CoreInitializable, ERC20CoreInitializable. Docs: https://portal.thirdweb.com/tokens/modular-contracts/core-contracts/erc-721.

---

## PART 2 — OPENZEPPELIN CONTRACTS (v5.x, current v5.6.1)

**Repos:** github.com/OpenZeppelin/openzeppelin-contracts (canonical, MIT), github.com/OpenZeppelin/openzeppelin-contracts-upgradeable (EIP-7201 namespaced storage variants — **forbidden under cypherpunk2048**), github.com/OpenZeppelin/openzeppelin-community-contracts (experimental: account abstraction, paymasters, cross-chain), github.com/OpenZeppelin/openzeppelin-confidential-contracts. Docs root: https://docs.openzeppelin.com/contracts/5.x; API reference: https://docs.openzeppelin.com/contracts/5.x/api.

### token/ERC20 — https://docs.openzeppelin.com/contracts/5.x/api/token/erc20
- **ERC20**, **IERC20 / IERC20Metadata** — core fungible token.
- Extensions: **ERC20Burnable**, **ERC20Capped**, **ERC20Pausable**, **ERC20Permit** (ERC-2612 gasless approval), **ERC20Votes** (vote delegation), **ERC20Wrapper**, **ERC20FlashMint** (ERC-3156 flash loans), **ERC20TemporaryApproval** (ERC-7674), **ERC20Crosschain** (ERC-7786 bridge), **ERC1363**. (ERC20Snapshot removed in v5.)
- Utility: **SafeERC20**.

### token/ERC721 — https://docs.openzeppelin.com/contracts/5.x/api/token/erc721
- **ERC721** core (+ IERC721/IERC721Metadata/IERC721Enumerable/IERC721Receiver). Source pinned at v5.6.1: github.com/OpenZeppelin/openzeppelin-contracts/blob/v5.6.1/contracts/token/ERC721/ERC721.sol.
- Extensions: **ERC721Enumerable**, **ERC721URIStorage**, **ERC721Burnable**, **ERC721Pausable**, **ERC721Royalty** (ERC-2981), **ERC721Consecutive** (ERC-2309 batch mint during construction, ≤5000/batch), **ERC721Votes**, **ERC721Wrapper**.
- Utilities: **ERC721Holder**, **ERC721Utils**.

### token/ERC1155 — https://docs.openzeppelin.com/contracts/5.x/api/token/erc1155
- **ERC1155** core + extensions **ERC1155Burnable**, **ERC1155Pausable**, **ERC1155Supply**, **ERC1155URIStorage**; utility **ERC1155Holder**.

### Other token standards
- **ERC4626** (tokenized vault, with v4.9+ virtual shares/assets inflation-attack mitigation) — section within https://docs.openzeppelin.com/contracts/5.x/api/token/erc20.
- **ERC2981** (NFT royalties, common to 721/1155; basis-point fee denominator 10000) — https://docs.openzeppelin.com/contracts/5.x/api/token/common.
- **ERC6909** (+ ERC6909Metadata/ERC6909TokenSupply/ERC6909ContentURI; now final, un-drafted) — https://docs.openzeppelin.com/contracts/5.x/api/token/erc6909.
- **ERC1363**, **ERC2612 (Permit)** — see ERC20 extensions and https://docs.openzeppelin.com/contracts/5.x/api/interfaces.

### account / account abstraction — https://docs.openzeppelin.com/contracts/5.x/api/account
- **Account** (ERC-4337 smart account), **AccountERC7579**, **AccountERC7579Hooked**, **ERC7821** (minimal batch executor), **ERC4337Utils**, **ERC7579Utils**. Signers: AbstractSigner, SignerECDSA, SignerP256, SignerRSA, SignerEIP7702, SignerERC7913, MultiSignerERC7913(/Weighted). Smart-account guide: https://docs.openzeppelin.com/contracts/5.x/accounts. Account-abstraction overview: https://docs.openzeppelin.com/contracts/5.x/account-abstraction. Paymasters (community-contracts): PaymasterCore, PaymasterERC20, PaymasterERC20Guarantor, PaymasterERC721Owner, PaymasterSigner — https://docs.openzeppelin.com/community-contracts/paymasters.

### access — https://docs.openzeppelin.com/contracts/5.x/api/access
- **Ownable**, **Ownable2Step**, **AccessControl**, **AccessControlEnumerable**, **AccessControlDefaultAdminRules** (single admin, 2-step transfer with configurable delay), **AccessManager**, **AccessManaged**, **AuthorityUtils**. Guide: https://docs.openzeppelin.com/contracts/5.x/access-control.

### governance — https://docs.openzeppelin.com/contracts/5.x/api/governance
- **Governor** (core abstract) + modules: **GovernorVotes**, **GovernorVotesQuorumFraction**, **GovernorCountingSimple**, **GovernorCountingFractional**, **GovernorSettings**, **GovernorStorage**, **GovernorTimelockControl**, **GovernorTimelockAccess**, **GovernorTimelockCompound**, **GovernorPreventLateQuorum**, **GovernorProposalGuardian**, **GovernorSuperQuorum**, **GovernorNoncesKeyed**.
- **TimelockController** — delay between proposal and execution (PROPOSER/EXECUTOR/CANCELLER/admin roles).
- **Votes / VotesExtended** — base vote-tracking/delegation. Guide: https://docs.openzeppelin.com/contracts/5.x/governance.

### proxy / upgradeability — https://docs.openzeppelin.com/contracts/5.x/api/proxy — **FORBIDDEN by cypherpunk2048**
- **ERC1967Proxy**, **ERC1967Utils**, **TransparentUpgradeableProxy**, **ProxyAdmin**, **UUPSUpgradeable**, **BeaconProxy**, **IBeacon**, **UpgradeableBeacon**, **Initializable** — all forbidden for deployment. **Clones** (EIP-1167 minimal proxy) is the one exception: usable for deterministic, non-upgradeable factory clones (supports value-passing clone/cloneDeterministic as of v5.1).

### security / utils
- security (now under utils): **ReentrancyGuard**, **ReentrancyGuardTransient**, **Pausable**, **PullPayment** (legacy escrow).
- utils cryptography — https://docs.openzeppelin.com/contracts/5.x/api/utils/cryptography — **ECDSA**, **MessageHashUtils**, **SignatureChecker** (EOA + ERC-1271), **MerkleProof**, **EIP712**, **Hashes**, **ERC7739Utils**, **WebAuthn**, P256/RSA verifiers.
- utils math — **Math**, **SignedMath**, **SafeCast** (SafeMath removed in v5).
- utils structs — **EnumerableSet**, **EnumerableMap**, **BitMaps**, **DoubleEndedQueue**, **Checkpoints**, **MerkleTree**, **Heap**, **CircularBuffer**.
- utils misc — **Address**, **Create2**, **Multicall**, **Nonces**, **ShortStrings**, **Strings**, **Context**, **ERC165 / ERC165Checker**, **StorageSlot**. Overview: https://docs.openzeppelin.com/contracts/5.x/utilities.

### finance — https://docs.openzeppelin.com/contracts/5.x/api/finance
- **VestingWallet**, **VestingWalletCliff** (added v5.1). (PaymentSplitter removed in v5 — use a custom immutable splitter or VestingWallet.)

### metatx — https://docs.openzeppelin.com/contracts/5.x/api/metatx
- **ERC2771Context**, **ERC2771Forwarder** (production forwarder; replaced the old MinimalForwarder, which was removed in v5).

### Community / cross-chain / confidential
- community-contracts: ERC-7786 Axelar/Wormhole gateway adapters, ERC20Bridgeable (ERC-7802), ERC20Allowlist/Blocklist/Custodian/Collateral, paymasters, ERC-7579 modules — https://github.com/OpenZeppelin/openzeppelin-community-contracts (API: https://docs.openzeppelin.com/community-contracts/api/account).
- confidential-contracts (FHE-oriented) — https://github.com/OpenZeppelin/openzeppelin-confidential-contracts.

---

## PART 3 — IMPLEMENTATION GUIDANCE FOR CUSTOM REWRITES (cypherpunk2048)

### What conflicts vs. what's directly usable
- **Forbidden / reference-only:** all OZ proxy & upgradeable contracts (ERC1967Proxy, Transparent/UUPS/Beacon, ProxyAdmin, Initializable); the entire openzeppelin-contracts-upgradeable repo; Thirdweb MarketplaceV3, ManagedAccountFactory/ManagedAccount, DynamicAccount, and any EIP-7504 dynamic prebuilt.
- **Discouraged (retained admin keys):** Ownable/AccessControl/AccessManager when admin is *kept*. Permitted pattern: deploy → configure → **renounceOwnership()** (Ownable) or **revokeRole(DEFAULT_ADMIN_ROLE)** / AccessControlDefaultAdminRules transfer-to-zero, so no live admin remains.
- **Directly usable (rewrite immutable, Apache-2.0):** ERC20/721/1155 cores + non-admin extensions; ERC2981; Governor + TimelockController + Votes; ReentrancyGuard; EIP712/ECDSA/SignatureChecker/MerkleProof; EnumerableSet/Map, Checkpoints; Create2/Clones; VestingWallet; ERC2771Context.

### Mapping to AgenticPlace components
- **ERC-8004 agent registry:** Identity Registry = ERC-721 (OZ ERC721 + ERC721URIStorage for the agent registration-file URI). Reputation/Validation registries = custom event-emitting stores keyed by agentId, using EnumerableMap/Checkpoints; signature-gated feedback via EIP712 + SignatureChecker (supports ERC-1271 smart-account agents). Keep registries singleton and immutable to match the universal `0x8004…a432` deployment pattern. Validate against EIP-8004 (eips.ethereum.org/EIPS/eip-8004) and the erc-8004/erc-8004-contracts reference repo before freezing.
- **DAIO on-chain governance:** ERC20Votes (or ERC721Votes) governance token → Governor (GovernorVotes + GovernorVotesQuorumFraction + GovernorCountingSimple + GovernorTimelockControl) → TimelockController as executor/treasury owner. Renounce all deployer roles; the Timelock holds assets and is the sole proposer/canceller granted to the Governor. This replaces Thirdweb VoteERC20 with an immutable, admin-free stack.
- **x402 payment integration:** x402 is an HTTP-402 off-chain handshake settled on-chain via stablecoin transfers (EIP-3009 for USDC/EURC, Permit2 for any ERC-20). The protocol was contributed by Coinbase to the **Linux Foundation x402 Foundation on April 2, 2026** (announced at MCP Dev Summit NA, NYC), is **Apache-2.0 licensed** (aligning cleanly with cypherpunk2048's licensing rule), and is co-governed by Coinbase, Cloudflare, and Stripe. It has processed roughly **97 million transactions via Coinbase's Base** (~54,900/day), with **Solana carrying nearly 65% of x402 transaction volume in 2026** (per Unchained / Solana Foundation). On-chain, the rewrite needs an ERC-2612/EIP-3009-compatible payment token interface, SignatureChecker/EIP712 for authorization verification, and ReentrancyGuard on settlement. On the Algorand side (Parsec wallet, GoPlausible `@x402-avm/*`), settlement is ASA-based off the EVM contracts — bridge identity, not tokens.
- **BANKON ENS identity layer:** ENS subname issuance under a parent (e.g., name.bankon.eth) uses an immutable custom resolver/registrar; build on OZ ECDSA/EIP712 for off-chain name approvals and ERC-721 if subnames are tokenized (NameWrapper-style), rewritten without admin retention. (The bankon.eth parent-name claim is unconfirmed — validate against the live ENS registry before building.)
- **LayerZero OFT V2 cross-chain:** Use OFT (burn-and-mint) so the DAIO/utility token keeps a unified supply across Ethereum, Moonbeam (1284), and other EVM targets; the canonical lockbox/anchor lives on Ethereum mainnet. Because OFT owners normally retain mint/pause and DVN-config admin, the rewrite must lock these down (renounce owner; fix the DVN security stack once) to satisfy "no admin keys." Algorand (non-EVM, internal id 416001) is reached via the identity/attestation bridge + third-party messaging, not OFT.
- **Deterministic deployment:** Use CREATE2 (OZ Create2) and/or Clones (EIP-1167) for predictable addresses across Ethereum/Moonbeam/Arc Testnet (5042002), enabling the "same address across chains" registry pattern without any upgradeable proxy. Note Arc's USDC-as-gas system contract at `0x3600…0000` when budgeting deploy/settlement costs there.

## Recommendations
1. **Stage 1 — Foundations:** Fork OZ v5.6.1 non-proxy primitives into an Apache-2.0, flat snake_case Foundry repo; re-license cleanly. Pin Solidity ≥0.8.24 (OZ v5 minimum for Votes/Governor). Benchmark gas against Thirdweb base contracts. Benchmark/threshold: if a rewritten core diverges >10% in gas from the audited OZ baseline, re-review before mainnet.
2. **Stage 2 — Registry + identity:** Implement ERC-8004 Identity (ERC721 + URIStorage), Reputation, Validation as immutable singletons; deploy via CREATE2 for cross-chain address parity. Validate against EIP-8004 and the reference repo before freezing.
3. **Stage 3 — DAIO governance:** Deploy ERC20Votes + Governor + TimelockController; transfer all ownership/treasury to the Timelock; renounce/revoke every deployer admin role in the deploy script and assert zero-admin in Foundry tests (fail the deploy if any nonzero admin/owner remains).
4. **Stage 4 — Payments + cross-chain:** Integrate x402 settlement (EIP-3009/Permit2 + EIP712/SignatureChecker) and LayerZero OFT V2 with a one-time-fixed DVN stack and renounced owner; add the Algorand identity bridge via Parsec/GoPlausible tooling.
5. **Thresholds that change the plan:** If a component *requires* post-deploy mutability (e.g., evolving validation logic), prefer **redeploy + governance-controlled registry pointer update** over any proxy. If admin-free governance cannot meet an emergency-pause need, the only compliant pause is one encoded as a governance/timelock action, never an EOA admin key. Re-evaluate if OZ ships an audited non-proxy account-modularity path, or if the x402 Foundation finalizes an on-chain settlement standard that supersedes the EIP-3009/Permit2 approach.

## Caveats
- Thirdweb prebuilts are predominantly upgradeable/role-gated (EIP-7504), structurally incompatible with cypherpunk2048; treat them as feature blueprints only.
- OZ is MIT, AgenticPlace requires Apache-2.0 — rewrites must re-implement/relicense, not vendor OZ as-is. (x402, by contrast, is already Apache-2.0.)
- Several AgenticPlace specifics (allchain.html exact chain list, bankon.eth ENS subnames, mindX API surface) are project self-reported or unconfirmed; the universal registry address and "48 chains / ~2,510 chains" figures come from the project via 8004scan.io and are not independently audited.
- OZ version specifics evolve; verify exact contract availability against the v5.6.x changelog at deploy time (ERC20Snapshot, PaymentSplitter, SafeMath, and MinimalForwarder were all removed in the v5 line, first shipped in v5.0 — OZ's first major release since 2021).
- x402 and Arc are early-stage (Arc public testnet launched Oct 28, 2025; x402 entered the Linux Foundation in April 2026) — interfaces and supported chains may shift before AgenticPlace's mainnet deployment.