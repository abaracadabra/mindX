#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
//
// export-abis.mjs — single generator for the dApp's contract surface.
//
// Reads the Foundry build artifacts in `out/<Contract>.sol/<Contract>.json`
// (run `forge build` first) and emits, under packages/web/public/:
//   • abis/<Contract>.json         — the full ABI array for each contract
//   • bankon.contracts.json        — the manifest both UIs load:
//       { generatedFrom, chains[], contracts[], presets[] }
//
// The manifest carries NO addresses — those live in deployments/<chainId>.json
// and are loaded at runtime so a redeploy never requires re-running this script.
// Each contract has a `deploymentKey` naming its slot in deployments/<chain>.json.
//
// Usage:  node script/export-abis.mjs
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "out");
const PUB = join(ROOT, "packages", "web", "public");
const ABI_DIR = join(PUB, "abis");
// dApp prototype: each contract owns its ABI as an importable ES module (abis/<name>.abi.js),
// loaded by name or address — "imported like an external stylesheet".
const DAPP = join(ROOT, "packages", "web", "dapp");
const DAPP_ABI = join(DAPP, "abis");

// ── Contracts to expose. `sol` is the path under contracts/ (for the out/
//    folder name); `deploymentKey` is the slot in deployments/<chain>.json. ──
const CONTRACTS = [
  { name: "BankonSubnameRegistrar", deploymentKey: "subnameRegistrar", category: "registrar", title: "Subname Registrar", blurb: "Issues *.bankon.eth subnames (Flow A)." },
  { name: "BankonEthRegistrar",     deploymentKey: "ethRegistrar",     category: "registrar", title: ".eth Registrar",     blurb: "Buys new .eth 2LDs via ENS commit-reveal (Flow B)." },
  { name: "BankonDomainHosting",    deploymentKey: "domainHosting",    category: "registrar", title: "Domain Hosting",     blurb: "Subdomain-minting-as-a-service for any .eth (Flow C)." },
  { name: "BankonSubnameResolver",  deploymentKey: "resolver",         category: "resolver",  title: "Resolver",           blurb: "addr / text records; iNFT TBA binding." },
  { name: "BankonSubnameResolverV2",deploymentKey: "resolverV2",       category: "resolver",  title: "Resolver V2",        blurb: "ENSv2 / Namechain forward-compatible resolver." },
  { name: "BankonPriceOracle",      deploymentKey: "priceOracle",      category: "pricing",   title: "Price Oracle",       blurb: "Length-tiered USD pricing + PYTHAI discount." },
  { name: "BankonReputationGate",   deploymentKey: "reputationGate",   category: "access",    title: "Reputation Gate",    blurb: "Free-tier eligibility (BONAFIDE / stake / attestation)." },
  { name: "BankonPaymentRouter",    deploymentKey: "paymentRouter",    category: "payment",   title: "Payment Router",     blurb: "x402 settlement + 5-bucket revenue split." },
  { name: "BankonInftAdapter",      deploymentKey: "inftAdapter",      category: "inft",      title: "iNFT Adapter",       blurb: "ERC-7857 Mode A glue; ENS labelhash → 0G tokenId / TBA." },
  { name: "BankonX402Attestor",     deploymentKey: "x402Attestor",     category: "payment",   title: "x402 Attestor",      blurb: "EIP-712 x402 receipt verification + replay guard." },
  { name: "X402Receipt",            deploymentKey: "x402Receipt",      category: "payment",   title: "x402 Receipt",       blurb: "On-chain x402 settlement attestation ledger; cascades into the payment router." },
  { name: "BankonAgenticPlaceHook", deploymentKey: "agenticPlaceHook", category: "listing",   title: "AgenticPlace Hook",  blurb: "Emits marketplace listing events for agenticplace.pythai.net." },
  { name: "AgentRegistry",          deploymentKey: "agentRegistry",    category: "identity",  title: "Agent Registry",     blurb: "ERC-8004-aligned agent identity + capability bitmap." },
  { name: "BankonAuthGate",         deploymentKey: "authGate",         category: "identity",  title: "Auth Gate",          blurb: "On-chain SIWE / ENS-gated auth for downstream services." },
  { name: "SoulBadger",             deploymentKey: "soulBadger",       category: "identity",  title: "SoulBadger",         blurb: "Soulbound badge wrapper." },
  { name: "BankonOffchainRegistrar",deploymentKey: "offchainRegistrar",category: "offchain",  title: "Offchain Registrar", blurb: "Gas-light CCIP-Read subname issuance (Phase 2.2)." },
  { name: "BankonOffchainResolver", deploymentKey: "offchainResolver", category: "offchain",  title: "Offchain Resolver",  blurb: "EIP-3668 CCIP-Read resolver." },
  // ── Canonical EIP-7857 + ERC-6551 modular stack (contracts/inft7857/) ──
  { name: "bankon_inft_subname",      deploymentKey: "inftUnified",     category: "inft7857",  title: "iNFT (Mode A unified)",   blurb: "Canonical ERC-7857 + ERC-721 + 5192 + 2981, NameWrapper-backed." },
  { name: "bankon_inft_extension",    deploymentKey: "inftParallel",    category: "inft7857",  title: "iNFT (Mode B parallel)",  blurb: "Canonical ERC-7857 bolted onto an existing wrapped subname." },
  { name: "bankon_inft_registrar",    deploymentKey: "inftRegistrar",   category: "inft7857",  title: "iNFT Registrar",          blurb: "Mint router (WRAPPED/UNIFIED/PARALLEL ± soulbound) + x402." },
  { name: "bankon_inft_oracle",       deploymentKey: "inftOracle",      category: "inft7857",  title: "iNFT Verifier (oracle)",  blurb: "Pluggable IERC7857DataVerifier (multisig EIP-712 TEE)." },
  { name: "bankon_tba_account",       deploymentKey: "tbaImpl",         category: "inft7857",  title: "ERC-6551 TBA account",    blurb: "Agent wallet; owner = live ownerOf(tokenId)." },
  { name: "bankon_tba_registry_proxy",deploymentKey: "tbaRegistryProxy",category: "inft7857",  title: "TBA registry proxy",      blurb: "Event-emitting wrapper over the canonical 6551 registry." },
  // ── ARC agent economy (contracts/arc/, copied from daio + expanded) ──
  { name: "bankon_agent_market",      deploymentKey: "agentMarket",     category: "arc",       title: "Agent Marketspace",       blurb: "List iNFT agents for sale; AgenticPlace indexer source." },
  { name: "AgentReputationRegistry",  deploymentKey: "agentReputation", category: "arc",       title: "Agent Reputation",        blurb: "Agent profiles, metrics, reviews (USDC economy)." },
  { name: "AgenticMarketplaceEscrow", deploymentKey: "agentEscrow",     category: "arc",       title: "Marketplace Escrow",      blurb: "Milestone-based agent service agreements + disputes." },
  { name: "SubscriptionManager",      deploymentKey: "subscriptions",   category: "arc",       title: "Subscriptions",           blurb: "Recurring USDC billing for agent services." },
  // ── cypherpunk2048 financial primitives (contracts/cp2048/) ──
  { name: "scientific_token",         deploymentKey: "scientific",      category: "cp2048",    title: "SCIENTIFIC token",        blurb: "Precision rail ERC-20: single-issuance, owner-renounce, self-purge to immutable owner." },
  { name: "rake",                     deploymentKey: "rakeCollector",   category: "cp2048",    title: "RAKE collector",          blurb: "Per-chain fee sweep to bankon.eth only when value beats chain cost." },
  { name: "bankon_oracle",            deploymentKey: "bankonOracle",    category: "cp2048",    title: "Pair-price oracle",       blurb: "USD value straight from the Uniswap liquidity pair." },
  { name: "bankon_autoconvert",       deploymentKey: "autoconvert",     category: "cp2048",    title: "Auto-convert router",     blurb: "Any token → settlement via Uniswap V3; golden-ratio fee → RAKE." },
  { name: "bridge_collect",           deploymentKey: "bridgeCollect",   category: "cp2048",    title: "Bridge-collect (GLMR)",   blurb: "LI.FI cross-chain pay-any-currency; golden fee → RAKE." },
  { name: "bankon_gas_service",       deploymentKey: "gasService",      category: "cp2048",    title: "Gas-as-a-service",        blurb: "Base gas reservoir: sponsored one-tx drop + custom buy; φ/10 golden fee home to bankon.eth." },
  { name: "treasury",                 deploymentKey: "treasury",        category: "cp2048",    title: "Treasury vault",          blurb: "Holds native/ERC20/721/1155 on any chain; redeems only to immutable bankon.eth; dictator→2:2/2:3/3:3 multisig." },
  { name: "remittance",               deploymentKey: "remittance",      category: "cp2048",    title: "Remittance",              blurb: "Collection/forwarding vault; batch remit home to bankon.eth; same custody + consensus migration as treasury." },
];

// ── Browser-deploy sequences. Each set lists contracts in dependency order; the
//    deployer reads creation bytecode from bankon.bytecodes.json + the ctor ABI,
//    and threads each arg from one of: {owner} (resolved bankon.eth / connected),
//    {ref:<contract>} (a prior step's deployed address), {chain:<key>} (per-chain
//    param below), or {literal:<value>}. Post-deploy `wire` calls run after.    ──
const ZERO = "0x0000000000000000000000000000000000000000";
const TREASURY_OWNER = "0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169"; // bankon.eth (verified ENS)
// namehash("bankon.eth") — chain-independent (same on every ENS deployment).
const BANKON_ETH_NODE = "0x79c178642317fc2d61d186f3b412440f06590d8314f126362d6a88929a6cbe1a";
// keccak256("GATEWAY_SIGNER_ROLE") — the role the bankon_vault signer holds to
// counter-sign EIP-712 registration vouchers (grant-a-subname-from-a-signature).
const GATEWAY_SIGNER_ROLE = "0x4b6d7bfbdfd4dba4dace8bd7020a81117ab633e3a677498b9e92d1b899379d26";
// AgenticPlace listing webhook baked into BankonAgenticPlaceHook (chain-independent URL).
const AGENTICPLACE_WEBHOOK = "https://agenticplace.pythai.net/x402/listing";

const DEPLOY_SEQUENCES = [
  {
    // ── Flow A/B/C ENS minter core — the subdomain.bankon.eth registrar stack.
    //    Ported verbatim from script/DeployEthereum.s.sol (ctor order + 13 role
    //    grants). bankon.eth is the immutable admin + payment recipient ({owner}).
    //    ENS-only: pinned to mainnet + Sepolia (NameWrapper-bound, varies per chain
    //    so NOT CREATE2 same-address). Refs are by contract name.
    id: "ens", title: "BANKON ENS minter (Flow A/B/C)", category: "ens",
    chains: [1, 11155111],
    blurb: "subdomain.bankon.eth registrar + .eth purchase + domain hosting: price/reputation/payment → identity → resolver(+adapter+V2) → registrar/ethRegistrar/domainHosting, then 13 role grants. bankon.eth is admin + fee recipient.",
    steps: [
      { contract: "BankonPriceOracle",       args: [{ owner: true }] },
      { contract: "BankonReputationGate",    args: [{ owner: true }] },
      { contract: "BankonPaymentRouter",     args: [{ owner: true }] },
      { contract: "AgentRegistry",           args: [{ literal: "BANKON Agent Registry" }, { literal: "AGENT" }, { owner: true }] },
      { contract: "X402Receipt",             args: [{ owner: true }, { ref: "BankonPaymentRouter" }] },
      { contract: "BankonX402Attestor",      args: [{ owner: true }] },
      { contract: "BankonAgenticPlaceHook",  args: [{ owner: true }, { literal: AGENTICPLACE_WEBHOOK }] },
      { contract: "BankonSubnameResolver",   args: [{ owner: true }, { literal: ZERO }] },
      { contract: "BankonInftAdapter",       args: [{ owner: true }, { ref: "BankonSubnameResolver" }] },
      { contract: "BankonSubnameResolverV2", args: [{ owner: true }, { ref: "BankonInftAdapter" }] },
      { contract: "BankonSubnameRegistrar",  args: [{ chain: "nameWrapper" }, { ref: "BankonSubnameResolver" }, { chain: "bankonNode" }, { ref: "BankonPaymentRouter" }, { ref: "BankonPriceOracle" }, { ref: "BankonReputationGate" }, { ref: "AgentRegistry" }, { owner: true }] },
      { contract: "BankonEthRegistrar",      args: [{ owner: true }, { chain: "ensController" }, { ref: "BankonPriceOracle" }, { ref: "BankonPaymentRouter" }, { ref: "BankonX402Attestor" }] },
      { contract: "BankonDomainHosting",     args: [{ owner: true }, { chain: "nameWrapper" }, { ref: "BankonSubnameResolver" }, { ref: "BankonPaymentRouter" }, { ref: "BankonX402Attestor" }] },
    ],
    wire: [
      { contract: "BankonSubnameResolver",   fn: "setInftAdapter",  args: [{ ref: "BankonInftAdapter" }] },
      { contract: "BankonSubnameResolver",   fn: "grantRegistrar",  args: [{ ref: "BankonSubnameRegistrar" }] },
      { contract: "BankonSubnameResolver",   fn: "grantRegistrar",  args: [{ ref: "BankonDomainHosting" }] },
      { contract: "BankonSubnameResolverV2", fn: "grantRegistrar",  args: [{ ref: "BankonSubnameRegistrar" }] },
      { contract: "BankonSubnameResolverV2", fn: "grantRegistrar",  args: [{ ref: "BankonDomainHosting" }] },
      { contract: "BankonInftAdapter",       fn: "grantRegistrar",  args: [{ ref: "BankonSubnameRegistrar" }] },
      { contract: "BankonAgenticPlaceHook",  fn: "grantLister",     args: [{ ref: "BankonSubnameRegistrar" }] },
      { contract: "BankonAgenticPlaceHook",  fn: "grantLister",     args: [{ ref: "BankonEthRegistrar" }] },
      { contract: "BankonAgenticPlaceHook",  fn: "grantLister",     args: [{ ref: "BankonDomainHosting" }] },
      { contract: "BankonX402Attestor",      fn: "grantConsumer",   args: [{ ref: "BankonSubnameRegistrar" }] },
      { contract: "BankonX402Attestor",      fn: "grantConsumer",   args: [{ ref: "BankonEthRegistrar" }] },
      { contract: "BankonX402Attestor",      fn: "grantConsumer",   args: [{ ref: "BankonDomainHosting" }] },
      // bankon_vault gateway-signer: grant-a-subname-from-a-signature without
      // revealing the key. Skipped automatically when vaultSigner is address(0).
      { contract: "BankonSubnameRegistrar",  fn: "grantRole",       args: [{ literal: GATEWAY_SIGNER_ROLE }, { chain: "vaultSigner" }] },
    ],
  },
  {
    id: "treasury", title: "Treasury (cp2048)", category: "cp2048",
    blurb: "The golden-ratio economy: pair oracle → SCIENTIFIC token → RAKE → auto-convert + bridge-collect → gas-as-a-service. Rakes home to bankon.eth.",
    steps: [
      { contract: "bankon_oracle",      args: [{ owner: true }, { chain: "usdc" }] },
      { contract: "scientific_token",   args: [{ owner: true }, { literal: "1000000000000000000000000" }, { owner: true }] },
      { contract: "rake",               args: [{ owner: true }, { owner: true }, { ref: "bankon_oracle" }, { literal: "5000000" }] },
      { contract: "bankon_autoconvert", args: [{ owner: true }, { chain: "univ3Router" }, { ref: "rake" }, { literal: "10000" }] },
      { contract: "bridge_collect",     args: [{ owner: true }, { ref: "rake" }, { literal: "10000" }] },
      { contract: "bankon_gas_service", args: [{ owner: true }, { owner: true }, { literal: "150000" }, { literal: "100000000000000000" }], chains: [8453, 84532], note: "Base only — the gas-as-a-service reservoir." },
    ],
  },
  {
    id: "custody", title: "Treasury + remittance", category: "cp2048",
    blurb: "Safe multi-asset vaults (native/ERC20/721/1155, any chain): treasury (long-term hold) + remittance (collect/forward). Founder = bankon.eth immutable; redeem home only; dictator → 2:2/2:3/3:3 multisig → renounce.",
    steps: [
      { contract: "treasury",   args: [{ owner: true }], create2: true },
      { contract: "remittance", args: [{ owner: true }], create2: true },
    ],
  },
  {
    id: "inft", title: "iNFT identity", category: "inft7857",
    blurb: "ENS-named, ERC-7857 agent intelligence with an ERC-6551 wallet: oracle → TBA impl + proxy → unified + parallel iNFT → registrar (then setMinter).",
    steps: [
      { contract: "bankon_inft_oracle",        args: [{ owner: true }, { literal: "[]" }, { literal: "1" }], note: "signers[], quorum — set real signers post-deploy." },
      { contract: "bankon_tba_account",        args: [], create2: true },
      { contract: "bankon_tba_registry_proxy", args: [], create2: true },
      { contract: "bankon_inft_subname",       args: [{ literal: "BANKON Agent" }, { literal: "BANK" }, { literal: "ipfs://bankon-storage" }, { literal: "https://bankon.eth/contract-metadata.json" }, { owner: true }, { literal: "0x0000000000000000000000000000000000000000" }, { chain: "nameWrapper" }, { ref: "bankon_inft_oracle" }, { owner: true }, { literal: "250" }] },
      { contract: "bankon_inft_extension",     args: [{ literal: "BANKON Agent Extension" }, { literal: "BANKX" }, { literal: "ipfs://bankon-ext" }, { owner: true }, { chain: "nameWrapper" }, { ref: "bankon_inft_oracle" }, { owner: true }, { literal: "250" }] },
      { contract: "bankon_inft_registrar",     args: [{ owner: true }, { chain: "nameWrapper" }, { ref: "bankon_inft_subname" }, { ref: "bankon_inft_extension" }, { chain: "erc6551Registry" }, { ref: "bankon_tba_account" }, { owner: true }] },
    ],
    wire: [{ contract: "bankon_inft_subname", fn: "setMinter", args: [{ ref: "bankon_inft_registrar" }] }],
  },
  {
    id: "arc", title: "ARC economy", category: "arc",
    blurb: "Agent reputation + escrow + marketspace (USDC economy): reputation registry → escrow → agent market.",
    steps: [
      { contract: "AgentReputationRegistry",  args: [], create2: true },
      { contract: "AgenticMarketplaceEscrow", args: [{ owner: true }, { literal: "250" }], create2: true },
      { contract: "bankon_agent_market",      args: [{ literal: "0x0000000000000000000000000000000000000000" }, { ref: "AgentReputationRegistry" }, { ref: "AgenticMarketplaceEscrow" }, { literal: "0x0000000000000000000000000000000000000000" }], note: "inft_ / x402Attestor_ = 0x0; wire to the iNFT set + attestor after." },
    ],
  },
];

// Per-chain deploy parameters. Browser deployer falls back to address(0) when a
// key is missing on the active chain (and surfaces it for manual entry).
const CHAIN_PARAMS = {
  1:        { label: "Ethereum", usdc: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", univ3Router: "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45", nameWrapper: "0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401", erc6551Registry: "0x000000006551c19487814612e58FE06813775758", ensController: "0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547", bankonNode: BANKON_ETH_NODE, vaultSigner: ZERO },
  11155111: { label: "Sepolia", usdc: "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238", univ3Router: ZERO, nameWrapper: "0x0635513f179D50A207757E05759CbD106d7dFcE8", erc6551Registry: "0x000000006551c19487814612e58FE06813775758", ensController: "0xfb3cE5D01e0f33f41DbB39035dB9745962F1f968", bankonNode: BANKON_ETH_NODE, vaultSigner: ZERO },
  84532:    { label: "Base Sepolia", usdc: "0x036CbD53842c5426634e7929541eC2318f3dCF7e", univ3Router: ZERO, nameWrapper: ZERO, erc6551Registry: "0x000000006551c19487814612e58FE06813775758" },
  16601:    { label: "0G Galileo", usdc: ZERO, univ3Router: ZERO, nameWrapper: ZERO, erc6551Registry: "0x000000006551c19487814612e58FE06813775758" },
  8453:     { label: "Base",     usdc: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", univ3Router: "0x2626664c2603336E57B271c5C0b26F421741e481", nameWrapper: "0x0000000000000000000000000000000000000000", erc6551Registry: "0x000000006551c19487814612e58FE06813775758" },
  42161:    { label: "Arbitrum", usdc: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", univ3Router: "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45", nameWrapper: "0x0000000000000000000000000000000000000000", erc6551Registry: "0x000000006551c19487814612e58FE06813775758" },
  137:      { label: "Polygon",  usdc: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", univ3Router: "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45", nameWrapper: "0x0000000000000000000000000000000000000000", erc6551Registry: "0x000000006551c19487814612e58FE06813775758" },
  5042002:  { label: "Arc testnet", usdc: "0x3600000000000000000000000000000000000000", univ3Router: "0x0000000000000000000000000000000000000000", nameWrapper: "0x0000000000000000000000000000000000000000", erc6551Registry: "0x000000006551c19487814612e58FE06813775758" },
  10:       { label: "Optimism", usdc: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", univ3Router: "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45", nameWrapper: "0x0000000000000000000000000000000000000000", erc6551Registry: "0x000000006551c19487814612e58FE06813775758" },
  43114:    { label: "Avalanche", usdc: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", univ3Router: "0x0000000000000000000000000000000000000000", nameWrapper: "0x0000000000000000000000000000000000000000", erc6551Registry: "0x000000006551c19487814612e58FE06813775758" },
  56:       { label: "BNB Smart Chain", usdc: "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", univ3Router: "0x0000000000000000000000000000000000000000", nameWrapper: "0x0000000000000000000000000000000000000000", erc6551Registry: "0x000000006551c19487814612e58FE06813775758" },
  1284:     { label: "Moonbeam", usdc: "0x0000000000000000000000000000000000000000", univ3Router: "0x0000000000000000000000000000000000000000", nameWrapper: "0x0000000000000000000000000000000000000000", erc6551Registry: "0x000000006551c19487814612e58FE06813775758" },
  81457:    { label: "Blast", usdc: "0x0000000000000000000000000000000000000000", univ3Router: "0x0000000000000000000000000000000000000000", nameWrapper: "0x0000000000000000000000000000000000000000", erc6551Registry: "0x000000006551c19487814612e58FE06813775758" },
  1776:     { label: "Injective EVM", usdc: "0x0000000000000000000000000000000000000000", univ3Router: "0x0000000000000000000000000000000000000000", nameWrapper: "0x0000000000000000000000000000000000000000", erc6551Registry: "0x000000006551c19487814612e58FE06813775758" },
};

// ── bankon.eth admin console actions. Curated post-deploy admin operations the
//    bankon.eth holder runs on the DEPLOYED contracts. Selectors + arg types are
//    resolved from the artifact at generation time → deployer/admin-actions.json.
//    arg.source: "input" (operator-entered) | "literal" (fixed) | "owner" (bankon.eth).
const ADMIN_ACTIONS = [
  { id: "set-vault-signer", label: "Set bankon_vault gateway signer", contract: "BankonSubnameRegistrar", sig: "grantRole(bytes32,address)",
    blurb: "Grant GATEWAY_SIGNER_ROLE so the vault issues subnames from a signature (key never revealed).",
    args: [{ name: "role", source: "literal", value: GATEWAY_SIGNER_ROLE }, { name: "signer", source: "input", placeholder: "0x… vault signer address" }] },
  { id: "revoke-vault-signer", label: "Revoke gateway signer", contract: "BankonSubnameRegistrar", sig: "revokeRole(bytes32,address)",
    blurb: "Remove a vault gateway signer.", args: [{ name: "role", source: "literal", value: GATEWAY_SIGNER_ROLE }, { name: "signer", source: "input", placeholder: "0x… signer to revoke" }] },
  { id: "set-price-oracle", label: "Set price oracle", contract: "BankonSubnameRegistrar", sig: "setPriceOracle(address)",
    blurb: "Point the registrar at a new BankonPriceOracle.", args: [{ name: "oracle", source: "input", placeholder: "0x… oracle" }] },
  { id: "set-reputation-gate", label: "Set reputation gate", contract: "BankonSubnameRegistrar", sig: "setReputationGate(address)",
    blurb: "Point the registrar at a new BankonReputationGate.", args: [{ name: "gate", source: "input", placeholder: "0x… gate" }] },
  { id: "pause", label: "Pause registrar", contract: "BankonSubnameRegistrar", sig: "pause()", blurb: "Halt new registrations.", args: [] },
  { id: "unpause", label: "Unpause registrar", contract: "BankonSubnameRegistrar", sig: "unpause()", blurb: "Resume registrations.", args: [] },
  { id: "set-webhook", label: "Set AgenticPlace webhook", contract: "BankonAgenticPlaceHook", sig: "setWebhookURL(string)",
    blurb: "Update the AgenticPlace listing webhook URL.", args: [{ name: "url", source: "input", placeholder: "https://agenticplace.pythai.net/x402/listing" }] },
  { id: "set-buyback", label: "Set buyback threshold", contract: "BankonPaymentRouter", sig: "setBuybackThreshold(uint256)",
    blurb: "Threshold (USD6) before the router triggers a buyback.", args: [{ name: "threshold", source: "input", placeholder: "e.g. 5000000 = $5" }] },
];

// ── Guided-form preset descriptors. The DOM is rendered per-UI; the call
//    construction lives in packages/web/bankon-forms.js, keyed by `id`/`flow`.
//    `fill: "account"` tells the UI to pre-fill the connected address.        ──
const PRESETS = [
  {
    id: "claim", title: "Claim a subname", subtitle: "yourname.bankon.eth",
    contract: "subnameRegistrar", fn: "registerFree", mode: "write",
    note: "Free tier — requires a 7+ char label and reputation eligibility (BONAFIDE / PYTHAI stake / attestation). For shorter or paid names use the generic explorer's `register`.",
    fields: [
      { name: "label", type: "string", label: "Label", placeholder: "yourname", help: "the part before .bankon.eth" },
      { name: "owner", type: "address", label: "Owner", fill: "account" },
      { name: "expiry", type: "uint64", label: "Expiry", control: "expiry", help: "defaults to 1 year from now" },
      { name: "meta", type: "tuple", label: "Agent metadata", control: "agentMeta", optional: true },
    ],
    agenticPlaceToggle: true,
  },
  {
    id: "buy-eth", title: "Buy a .eth name", subtitle: "newname.eth",
    contract: "ethRegistrar", flow: "commit-reveal", mode: "write",
    note: "Two-step ENS commit→reveal. We quote the price, you commit, wait the min commit age, then reveal+pay.",
    fields: [
      { name: "label", type: "string", label: "Label", placeholder: "newname", help: "the part before .eth" },
      { name: "owner", type: "address", label: "Owner", fill: "account" },
      { name: "durationYears", type: "uint256", label: "Years", default: "1" },
    ],
    paymentRail: true,
  },
  {
    id: "host-enroll", title: "Host your .eth", subtitle: "enroll a domain you own",
    contract: "domainHosting", fn: "enroll", mode: "write",
    note: "Enroll an external .eth you own so bankon can issue subnames under it. You must have burned CANNOT_UNWRAP on the parent.",
    fields: [
      { name: "parentNode", type: "bytes32", label: "Parent node", control: "namehash", help: "namehash of your .eth (we compute it from the name)" },
      { name: "pricePerLabel6", type: "uint256", label: "USD price / label (6dp)", default: "0" },
      { name: "priceEthWei", type: "uint256", label: "ETH price / label (wei)", default: "0" },
      { name: "childFuses", type: "uint32", label: "Child fuses", default: "327685", help: "0x50005 soulbound default" },
      { name: "defaultExpiry", type: "uint64", label: "Default expiry", control: "expiry" },
      { name: "ownerShareBps", type: "uint16", label: "Your share (bps)", default: "9000" },
    ],
  },
  {
    id: "host-issue", title: "Issue a hosted subname", subtitle: "label.yourdomain.eth",
    contract: "domainHosting", fn: "issue", mode: "write", payable: true,
    fields: [
      { name: "parentNode", type: "bytes32", label: "Parent node", control: "namehash" },
      { name: "label", type: "string", label: "Label", placeholder: "alice" },
      { name: "owner", type: "address", label: "Owner", fill: "account" },
      { name: "payment", type: "bytes", label: "Payment", default: "0x" },
    ],
    paymentRail: true,
  },
  {
    id: "register-agent", title: "Register an agent", subtitle: "agent identity as a service",
    contract: "agentRegistry", fn: "register", mode: "write",
    note: "Mint an ERC-8004-aligned agent identity with a capability bitmap. Pair it with a bankon.eth subname for a fully-resolvable agent.",
    fields: [
      { name: "owner", type: "address", label: "Owner", fill: "account" },
      { name: "agentId", type: "string", label: "Agent ID", placeholder: "my-agent" },
      { name: "linkedINFT_7857", type: "address", label: "Linked iNFT (optional)", default: "0x0000000000000000000000000000000000000000" },
      { name: "capabilityBitmap", type: "bytes32", label: "Capabilities", default: "0x0000000000000000000000000000000000000000000000000000000000000000" },
      { name: "attestationURI", type: "string", label: "Attestation URI", optional: true },
    ],
    agenticPlaceToggle: true,
  },
  {
    id: "resolve", title: "Resolve / lookup", subtitle: "read a name's records",
    contract: "resolver", flow: "resolve", mode: "read",
    note: "Read addr(node) and a text record for any bankon.eth name.",
    fields: [
      { name: "name", type: "string", label: "Name", placeholder: "alice.bankon.eth", control: "namehashInput" },
      { name: "key", type: "string", label: "Text key", default: "agent.capabilities", optional: true },
    ],
  },
];

function readArtifact(name) {
  const p = join(OUT, `${name}.sol`, `${name}.json`);
  if (!existsSync(p)) {
    throw new Error(`Missing artifact: ${p}\n  → run \`forge build\` in ${ROOT} first.`);
  }
  const j = JSON.parse(readFileSync(p, "utf8"));
  // creation bytecode (Foundry: .bytecode.object) — what a browser deployer sends.
  const bytecode = (j.bytecode && (j.bytecode.object || j.bytecode)) || "0x";
  // methodIdentifiers maps "fn(types)" → 4-byte selector — lets the deployer
  // bundles carry post-deploy wire selectors WITHOUT a client-side keccak.
  return { abi: j.abi, bytecode, methodIdentifiers: j.methodIdentifiers || {} };
}

function main() {
  mkdirSync(ABI_DIR, { recursive: true });
  const contracts = [];
  const bytecodes = {};
  const meta = {};   // name → { abi, methodIdentifiers } for the deployer-bundle emitter
  for (const c of CONTRACTS) {
    const { abi, bytecode, methodIdentifiers } = readArtifact(c.name);
    writeFileSync(join(ABI_DIR, `${c.name}.json`), JSON.stringify(abi, null, 2) + "\n");
    bytecodes[c.name] = bytecode;
    meta[c.name] = { abi, methodIdentifiers };
    contracts.push({
      name: c.name,
      deploymentKey: c.deploymentKey,
      category: c.category,
      title: c.title,
      blurb: c.blurb,
      abi: `abis/${c.name}.json`,
      fnCount: abi.filter((x) => x.type === "function").length,
      deployable: typeof bytecode === "string" && bytecode.length > 2,
    });
    console.log(`  abis/${c.name}.json  (${abi.length} entries, bytecode ${bytecode.length > 2 ? (bytecode.length - 2) / 2 + "B" : "—"})`);
  }

  // Creation-bytecode manifest for the browser deployer (deploy.html).
  writeFileSync(join(PUB, "bankon.bytecodes.json"), JSON.stringify(bytecodes, null, 2) + "\n");
  console.log(`  bankon.bytecodes.json  (${Object.keys(bytecodes).length} contracts)`);

  const manifest = {
    generatedFrom: "forge build artifacts in out/ — regenerate with `node script/export-abis.mjs`",
    chains: [
      { id: 1, key: "mainnet", label: "Ethereum", deployments: "deployments/1.json" },
      { id: 11155111, key: "sepolia", label: "Sepolia", deployments: "deployments/11155111.json" },
      { id: 31337, key: "local", label: "Anvil (local fork)", deployments: "deployments/local.json" },
    ],
    contracts,
    presets: PRESETS,
    deploy: { treasuryOwner: TREASURY_OWNER, sequences: DEPLOY_SEQUENCES, chainParams: CHAIN_PARAMS, bytecodes: "bankon.bytecodes.json" },
  };
  writeFileSync(join(PUB, "bankon.contracts.json"), JSON.stringify(manifest, null, 2) + "\n");
  console.log(`  bankon.contracts.json  (${contracts.length} contracts, ${PRESETS.length} presets, ${DEPLOY_SEQUENCES.length} deploy sequences)`);

  exportDappAbis(contracts);
  emitDeployerBundles(meta);
  emitAdminActions(meta);

  // Mirror the canonical per-chain address records into public/ so the static
  // dApp can fetch them. deployments/ at the module root stays the source of
  // truth (also read by clients/python + the deploy scripts).
  const DEP_SRC = join(ROOT, "deployments");
  const DEP_DST = join(PUB, "deployments");
  mkdirSync(DEP_DST, { recursive: true });
  for (const fname of ["1.json", "11155111.json", "local.json"]) {
    const src = join(DEP_SRC, fname);
    if (existsSync(src)) { writeFileSync(join(DEP_DST, fname), readFileSync(src, "utf8")); console.log(`  deployments/${fname}`); }
  }

  exportInft();
}

// ── Per-contract ABI ES modules for the dApp prototype. Each contract owns its ABI
//    in abis/<name>.abi.js (imported like an external stylesheet), plus an index.js
//    catalogue the dApp uses to resolve a NAME or contract ADDRESS → its ABI.       ─
function exportDappAbis(contracts) {
  mkdirSync(DAPP_ABI, { recursive: true });
  for (const c of contracts) {
    const abi = JSON.parse(readFileSync(join(ABI_DIR, `${c.name}.json`), "utf8"));
    const mod =
      `// SPDX-License-Identifier: Apache-2.0\n` +
      `// GENERATED by script/export-abis.mjs — ${c.title}. Do not edit by hand.\n` +
      `// Each contract owns its ABI; import it like a stylesheet:  import ABI from "./abis/${c.name}.abi.js"\n` +
      `export const NAME = ${JSON.stringify(c.name)};\n` +
      `export const TITLE = ${JSON.stringify(c.title)};\n` +
      `export const DEPLOYMENT_KEY = ${JSON.stringify(c.deploymentKey)};\n` +
      `export const ABI = ${JSON.stringify(abi)};\n` +
      `export default ABI;\n`;
    writeFileSync(join(DAPP_ABI, `${c.name}.abi.js`), mod);
  }
  // catalogue: name/title/deploymentKey → lazy loader; the dApp resolves by name or address.
  const cat = contracts.map((c) => ({ name: c.name, title: c.title, category: c.category, deploymentKey: c.deploymentKey }));
  const index =
    `// SPDX-License-Identifier: Apache-2.0\n` +
    `// GENERATED by script/export-abis.mjs — contract catalogue for the dApp.\n` +
    `// loadAbi(name) dynamically imports the per-contract module (abi-as-stylesheet).\n` +
    `export const CONTRACTS = ${JSON.stringify(cat, null, 2)};\n` +
    `export const byKey = Object.fromEntries(CONTRACTS.map((c) => [c.deploymentKey, c]));\n` +
    `export async function loadAbi(name) { return (await import(\`./\${name}.abi.js\`)).ABI; }\n`;
  writeFileSync(join(DAPP_ABI, "index.js"), index);
  console.log(`  dapp/abis/*.abi.js  (${contracts.length} per-contract modules + index.js)`);
}

// ── deployer/ bundle emitter ────────────────────────────────────────────────
// Generates deployer/bundles/bankon-<seq>.xml + deployer/chain-params.json from
// DEPLOY_SEQUENCES — the SAME source of truth the dApp deploy engine uses. The
// client (deployer/deployer.js) stays keccak-free: CREATE2 salts are the
// deterministic UTF-8 of the contract name (chain-independent), and post-deploy
// wire selectors come straight from the artifact's methodIdentifiers.
const DEPLOYER_DIR = join(ROOT, "deployer");
const BUNDLES_DIR  = join(DEPLOYER_DIR, "bundles");

function xmlEsc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
// deterministic chain-independent CREATE2 salt: UTF-8 bytes of a namespaced name, right-padded to 32B.
function saltFor(name) {
  // bare UTF-8 of the (unique) contract name, right-padded to 32 bytes — deterministic
  // and chain-independent, so identical salt+initCode ⇒ identical address on every chain.
  const hex = Buffer.from(name).toString("hex");
  if (hex.length > 64) throw new Error(`CREATE2 salt seed too long for ${name} (${hex.length / 2}B > 32B)`);
  return "0x" + hex.padEnd(64, "0");
}
function ctorInputs(meta, name) {
  const abi = (meta[name] && meta[name].abi) || [];
  const c = abi.find((x) => x.type === "constructor");
  return (c && c.inputs) || [];
}
// "fn(t1,t2)" → ["t1","t2"];  "fn()" → []
function sigTypes(sig) {
  const inner = sig.slice(sig.indexOf("(") + 1, sig.lastIndexOf(")"));
  return inner ? inner.split(",") : [];
}
function wireSelector(meta, name, fn, argCount) {
  const mids = (meta[name] && meta[name].methodIdentifiers) || {};
  const keys = Object.keys(mids).filter((k) => k.slice(0, k.indexOf("(")) === fn);
  if (!keys.length) throw new Error(`no selector for ${name}.${fn}() — is ${name} built?`);
  const key = keys.find((k) => sigTypes(k).length === argCount) || keys[0];
  return { selector: "0x" + mids[key], types: sigTypes(key) };
}
function argAttrs(spec, type, name) {
  let loc;
  if (spec.owner) loc = `from="owner"`;
  else if (spec.ref) loc = `from="deployed:${xmlEsc(spec.ref)}"`;
  else if (spec.chain) loc = `from="chain:${xmlEsc(spec.chain)}"`;
  else loc = `value="${xmlEsc(spec.literal)}"`;
  return `name="${xmlEsc(name)}" type="${xmlEsc(type)}" ${loc}`;
}

function emitDeployerBundles(meta) {
  mkdirSync(BUNDLES_DIR, { recursive: true });

  // chain-params for from="chain:<key>" + bankon.eth identity (recipient/controller)
  // + name→deploymentKey so the client can export deployments/<chainId>.json without
  // a cross-directory manifest fetch.
  const deploymentKeys = Object.fromEntries(CONTRACTS.map((c) => [c.name, c.deploymentKey]));
  writeFileSync(join(DEPLOYER_DIR, "chain-params.json"),
    JSON.stringify({
      owner: TREASURY_OWNER,                                       // bankon.eth resolved addr (payment/treasury/admin recipient)
      controller: "0x54165AdA93FA752cfec95F3f3bAE2676D3752A99",   // bankon.eth NameWrapper owner (mainnet deploy authority)
      bankonNode: BANKON_ETH_NODE,
      deploymentKeys,
      chains: CHAIN_PARAMS,
    }, null, 2) + "\n");
  console.log(`  deployer/chain-params.json  (${Object.keys(CHAIN_PARAMS).length} chains)`);

  for (const seq of DEPLOY_SEQUENCES) {
    const chainIdsAttr = seq.chains ? ` chainIds="${seq.chains.join(",")}"` : "";
    const L = [];
    L.push(`<?xml version="1.0" encoding="UTF-8"?>`);
    L.push(`<!-- GENERATED by script/export-abis.mjs from DEPLOY_SEQUENCES — do not edit by hand. -->`);
    L.push(`<!-- ${xmlEsc(seq.title)} — ${xmlEsc(seq.blurb || "")} -->`);
    L.push(`<bundle name="bankon-${seq.id}"${chainIdsAttr}>`);

    seq.steps.forEach((step, i) => {
      const inputs = ctorInputs(meta, step.contract);
      const stepChains = step.chains ? ` chainIds="${step.chains.join(",")}"` : "";
      const c2 = step.create2 ? ` create2="true" salt="${saltFor(step.contract)}"` : "";
      L.push(``);
      L.push(`  <contract id="${step.contract}" name="${step.contract}" stage="${i + 1}"${c2}${stepChains}`);
      L.push(`            summary="${xmlEsc(step.note || "")}">`);
      L.push(`    <abi src="../out/${step.contract}.sol/${step.contract}.json"/>`);
      L.push(`    <bytecode src="../out/${step.contract}.sol/${step.contract}.json"/>`);
      const args = step.args || [];
      if (args.length) {
        L.push(`    <constructor>`);
        args.forEach((spec, k) => {
          const inp = inputs[k] || { type: "address", name: `arg${k}` };
          L.push(`      <arg ${argAttrs(spec, inp.type, inp.name || `arg${k}`)}/>`);
        });
        L.push(`    </constructor>`);
      } else {
        L.push(`    <constructor/>`);
      }
      L.push(`    <value kind="signature"/>`);
      L.push(`  </contract>`);
    });

    if (seq.wire && seq.wire.length) {
      L.push(``);
      L.push(`  <wire>`);
      for (const w of seq.wire) {
        const { selector, types } = wireSelector(meta, w.contract, w.fn, (w.args || []).length);
        L.push(`    <call contract="${w.contract}" fn="${w.fn}" selector="${selector}">`);
        (w.args || []).forEach((spec, k) => {
          L.push(`      <arg ${argAttrs(spec, types[k] || "address", `arg${k}`)}/>`);
        });
        L.push(`    </call>`);
      }
      L.push(`  </wire>`);
    }

    L.push(``);
    L.push(`</bundle>`);
    writeFileSync(join(BUNDLES_DIR, `bankon-${seq.id}.xml`), L.join("\n") + "\n");
    console.log(`  deployer/bundles/bankon-${seq.id}.xml  (${seq.steps.length} stages${seq.wire ? ", " + seq.wire.length + " wires" : ""}${seq.chains ? ", chains " + seq.chains.join("/") : ""})`);
  }
}

// ── bankon.eth admin console actions (deployer/admin-actions.json) ──
function emitAdminActions(meta) {
  const keyOf = Object.fromEntries(CONTRACTS.map((c) => [c.name, c.deploymentKey]));
  const actions = ADMIN_ACTIONS.map((a) => {
    const mids = (meta[a.contract] && meta[a.contract].methodIdentifiers) || {};
    const sel = mids[a.sig];
    if (!sel) throw new Error(`admin action ${a.id}: no selector for ${a.contract}.${a.sig}`);
    const types = sigTypes(a.sig);
    return {
      id: a.id, label: a.label, blurb: a.blurb || "",
      contract: a.contract, deploymentKey: keyOf[a.contract], fn: a.sig.slice(0, a.sig.indexOf("(")),
      selector: "0x" + sel,
      args: (a.args || []).map((arg, i) => ({ ...arg, type: types[i] })),
    };
  });
  writeFileSync(join(DEPLOYER_DIR, "admin-actions.json"), JSON.stringify(actions, null, 2) + "\n");
  console.log(`  deployer/admin-actions.json  (${actions.length} admin actions)`);
}

// ── iNFT (ERC-7857) lives on 0G and builds under the zerog profile, so it has
//    its own self-contained ABI module (iNFTabi.js) + a copy in public/abis.
//    Regenerated only when the zerog artifact is present. Curated presets/chain
//    config below are the single source of truth for the iNFT page.            ─
const INFT_HEADER = `// SPDX-License-Identifier: Apache-2.0
//
// iNFTabi.js — ERC-7857 Intelligent NFT (iNFT_7857) ABI + 0G chain config for
// the standalone iNFT prototype page (inft.html). GENERATED by
// script/export-abis.mjs from out-zerog/iNFT_7857.sol/iNFT_7857.json
//   (FOUNDRY_PROFILE=zerog forge build contracts/inft/iNFT_7857.sol).
// Prototype convention: .js here; the production port lives in TS. Do not edit
// the ABI by hand — edit the curated descriptors in export-abis.mjs and re-run.

export const ZEROG_CHAINS = {
  16661: { hex: "0x4115", name: "0G Aristotle Mainnet", rpc: "https://evmrpc.0g.ai", explorer: "https://chainscan.0g.ai", symbol: "0G" },
  16601: { hex: "0x40d9", name: "0G Galileo Testnet", rpc: "https://evmrpc-testnet.0g.ai", explorer: "https://chainscan-galileo.0g.ai", symbol: "0G" },
};

export const INFT_ADDRESS = {
  16661: "0x0000000000000000000000000000000000000000",
  16601: "0x0000000000000000000000000000000000000000",
};

export const INFT_PRESETS = [
  { id: "mint", title: "Mint an agent iNFT", subtitle: "ERC-7857 intelligence NFT", fn: "mintAgent", mode: "write",
    note: "Anchors an encrypted-intelligence content root on 0G. dimensions must be one of validDimensions(); sealedKeyHash seals the AES key for the owner.",
    fields: [
      { name: "to", type: "address", label: "Owner", fill: "account" },
      { name: "contentRoot", type: "bytes32", label: "Content root (merkle)", placeholder: "0x…" },
      { name: "storageURI", type: "string", label: "0G storage URI", placeholder: "0g://… or ipfs://…" },
      { name: "metadataRoot", type: "bytes32", label: "Metadata root", default: "0x0000000000000000000000000000000000000000000000000000000000000000" },
      { name: "dimensions", type: "uint32", label: "Dimensions", default: "1536" },
      { name: "parallelUnits", type: "uint8", label: "Parallel units", default: "1" },
      { name: "sealedKeyHash", type: "bytes32", label: "Sealed key hash", default: "0x0000000000000000000000000000000000000000000000000000000000000000" },
      { name: "tokenURI_", type: "string", label: "Token URI", optional: true }
    ] },
  { id: "authorize", title: "Authorize usage", subtitle: "grant an executor", fn: "authorizeUsage", mode: "write",
    fields: [
      { name: "tokenId", type: "uint256", label: "Token ID" },
      { name: "executor", type: "address", label: "Executor" },
      { name: "permissions", type: "uint256", label: "Permissions bitmap", default: "1" },
      { name: "expiresAt", type: "uint64", label: "Expires at (unix)", control: "expiry" }
    ] },
  { id: "bind-agent", title: "Bind agent ID", subtitle: "link a bankon.eth name", fn: "bindAgentId", mode: "write",
    note: "Bind a human agent id (e.g. your bankon.eth subname) to the token.",
    fields: [
      { name: "tokenId", type: "uint256", label: "Token ID" },
      { name: "agentId", type: "string", label: "Agent ID", placeholder: "alice.bankon.eth" }
    ] },
  { id: "bind-vault", title: "Bind BANKON vault", subtitle: "encrypted credential vault", fn: "bindBankonVault", mode: "write",
    fields: [
      { name: "tokenId", type: "uint256", label: "Token ID" },
      { name: "vault", type: "address", label: "Vault address" },
      { name: "vaultRef", type: "bytes32", label: "Vault ref" }
    ] },
  { id: "offer", title: "Offer on AgenticPlace", subtitle: "list for sale", fn: "offerOnAgenticPlace", mode: "write",
    fields: [
      { name: "tokenId", type: "uint256", label: "Token ID" },
      { name: "marketplace", type: "address", label: "Marketplace" },
      { name: "price", type: "uint256", label: "Price (wei or token units)", default: "0" },
      { name: "isETH", type: "bool", label: "Pay in native?", default: "true" },
      { name: "paymentToken", type: "address", label: "Payment token (if not native)", default: "0x0000000000000000000000000000000000000000" }
    ] },
  { id: "payload", title: "Read payload", subtitle: "inspect a token", fn: "getPayload", mode: "read",
    fields: [ { name: "tokenId", type: "uint256", label: "Token ID" } ] },
  { id: "owner", title: "Owner of", subtitle: "ownerOf(tokenId)", fn: "ownerOf", mode: "read",
    fields: [ { name: "tokenId", type: "uint256", label: "Token ID" } ] }
];

export const INFT_ABI = `;

function exportInft() {
  const p = join(OUT.replace(/out$/, "out-zerog"), "iNFT_7857.sol", "iNFT_7857.json");
  if (!existsSync(p)) {
    console.log("  (iNFT_7857 artifact not found — run `FOUNDRY_PROFILE=zerog forge build contracts/inft/iNFT_7857.sol` to refresh iNFTabi.js)");
    return;
  }
  const abi = JSON.parse(readFileSync(p, "utf8")).abi;
  writeFileSync(join(ROOT, "packages", "web", "iNFTabi.js"), INFT_HEADER + JSON.stringify(abi, null, 2) + ";\n");
  writeFileSync(join(ABI_DIR, "iNFT_7857.json"), JSON.stringify(abi, null, 2) + "\n");
  console.log(`  iNFTabi.js + abis/iNFT_7857.json  (${abi.length} entries)`);
}

main();
