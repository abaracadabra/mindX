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

function readAbi(name) {
  const p = join(OUT, `${name}.sol`, `${name}.json`);
  if (!existsSync(p)) {
    throw new Error(`Missing artifact: ${p}\n  → run \`forge build\` in ${ROOT} first.`);
  }
  return JSON.parse(readFileSync(p, "utf8")).abi;
}

function main() {
  mkdirSync(ABI_DIR, { recursive: true });
  const contracts = [];
  for (const c of CONTRACTS) {
    const abi = readAbi(c.name);
    writeFileSync(join(ABI_DIR, `${c.name}.json`), JSON.stringify(abi, null, 2) + "\n");
    contracts.push({
      name: c.name,
      deploymentKey: c.deploymentKey,
      category: c.category,
      title: c.title,
      blurb: c.blurb,
      abi: `abis/${c.name}.json`,
      fnCount: abi.filter((x) => x.type === "function").length,
    });
    console.log(`  abis/${c.name}.json  (${abi.length} entries)`);
  }

  const manifest = {
    generatedFrom: "forge build artifacts in out/ — regenerate with `node script/export-abis.mjs`",
    chains: [
      { id: 1, key: "mainnet", label: "Ethereum", deployments: "deployments/1.json" },
      { id: 11155111, key: "sepolia", label: "Sepolia", deployments: "deployments/11155111.json" },
      { id: 31337, key: "local", label: "Anvil (local fork)", deployments: "deployments/local.json" },
    ],
    contracts,
    presets: PRESETS,
  };
  writeFileSync(join(PUB, "bankon.contracts.json"), JSON.stringify(manifest, null, 2) + "\n");
  console.log(`  bankon.contracts.json  (${contracts.length} contracts, ${PRESETS.length} presets)`);

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
