# NAV — Gated Reference Corpus (OFF LIMITS TO THE PUBLIC)

> **This is the private navigation hub for the reference-corpus subtrees mindX ingests but never publishes.**
> Everything indexed here is **ingest-only**: embedded into pgvector + RAGE for mindX's own
> retrieval, but **never** linked from `/docs.html`, never listed in `DOC_INDEX.md`, never
> surfaced through the public `/chat/docs` RAG endpoint, and never offloaded to IPFS.
>
> Access is gated behind **`/reference`** (session token / API key / shadow-overlord JWT) via the
> handler-gated `/reference/catalog` and `/reference/file/{path}` routes.
>
> **Source of truth:** [`utils/reference_corpus.py`](../../utils/reference_corpus.py) —
> `PRIVATE_DOC_PREFIXES` + `is_private_doc()`. This NAV is a human index of what that predicate gates;
> if the two ever disagree, the code wins. Regenerate this file when the corpus changes.

## The privacy contract

Three docs/-relative prefixes are private. Any path under them is off limits:

| Prefix | What it holds |
|---|---|
| `operations/` | Deployment guides, runbooks, architecture deep-dives, the `dev/` R&D tree |
| `blockchain/` | Chain integrations, market-data clients, x402 rails, theses (**this directory**) |
| `publications/pdf/` | PDF renders of publications **and their `.md` mirrors** |

**Excluded from ingest _and_ from this NAV** (noise / third-party, per `EXCLUDE_*` in the same module):
`node_modules/`, `__pycache__/`, `.git/`, saved-web-page `*_files/` asset dirs, `.pyc` files.
The `operations/dev/IDC/iDEBT/` extracted codebase carries a large vendored `ui/node_modules/`
(~690 third-party README/CHANGELOG `.md` files) — those are gated by rule but deliberately **not**
enumerated below.

> Note: `publications/*.md` (top-level) and `publications/daily/` are the **public** publication
> stream and are NOT indexed here. Only `publications/pdf/` (PDFs + md mirrors) is off limits.

---

## 1. `docs/blockchain/` — chain integrations, market data, x402 rails

Theses & integration guides
- [0G-Integration-Guide.md](0G-Integration-Guide.md) — 0G (ZeroGravity) integration
- [aave01062026.md](aave01062026.md) — Aave analysis
- [algorandscout.md](algorandscout.md) — **Algorandscout** — the non-EVM half of the chain-read surface: [`OpenBDK/algorandscout`](https://github.com/openbdk/algorandscout), a BANKON-licensed standalone service serving Algorand through a Blockscout-shaped API. Closes the Algorand gap named in [blockscout.md §7](blockscout.md). Built 2026-08-08; **capability, not yet wired into mindX**
- [BLOCKCHAIN_AGENTS.md](BLOCKCHAIN_AGENTS.md) — blockchain agents overview
- [blockscout.md](blockscout.md) — **Blockscout MCP** — how Claude reads the chain: all 16 tools + params, the unlock-once session, PRO-key/credit model (key mandatory from 2026-10-08), REST fallback, `blockscout-analysis` v0.6.0 operating rules, 97-chain coverage (incl. Arc `5042002`) and the honest gaps. Companion skill: `~/.claude/skills/blockscout/`
- [BTC_op_cat_quantum_fork.md](BTC_op_cat_quantum_fork.md) — Bitcoin OP_CAT / quantum fork thesis
- [decentralized-bridges-2026.md](decentralized-bridges-2026.md) — cross-chain bridge survey 2026
- [Deploying 100,000 ARIO on Base_ An Arweave and AR.IO Technical Playbook.md](Deploying%20100%2C000%20ARIO%20on%20Base_%20An%20Arweave%20and%20AR.IO%20Technical%20Playbook.md)
- [ETHglobal2026NYC.md](ETHglobal2026NYC.md) · [ETHglobal2026NYCv2.md](ETHglobal2026NYCv2.md) — ETHGlobal NYC submission notes
- [IPFS Integration and Chain Surface Mapping for the PYTHAI Project Suite.md](IPFS%20Integration%20and%20Chain%20Surface%20Mapping%20for%20the%20PYTHAI%20Project%20Suite.md)
- [kraken-canada-200-to-arweave.md](kraken-canada-200-to-arweave.md) — Kraken CA → Arweave field report
- [polkadot-glmr-undervalued-thesis-2026.md](polkadot-glmr-undervalued-thesis-2026.md) · [polkadot-moonbeam-2026.md](polkadot-moonbeam-2026.md)
- [Solidity-to-Frontend Interaction and Browser Deployment_ Open-Source Templates and Reference Architecture for the PYTHAI_BANKON Ecosystem.md](Solidity-to-Frontend%20Interaction%20and%20Browser%20Deployment_%20Open-Source%20Templates%20and%20Reference%20Architecture%20for%20the%20PYTHAI_BANKON%20Ecosystem.md)
- [todo.md](todo.md)

Market-data clients (code + guides)
- CoinMarketCap: [cmc_client.py](cmc_client.py) · [coinmarketcap_integration_guide.md](coinmarketcap_integration_guide.md)
- CoinGecko: [coingecko_client.py](coingecko_client.py) · [coingecko_integration_guide.md](coingecko_integration_guide.md) · [test_coingecko_client.py](test_coingecko_client.py)
- DefiLlama: [defillama_client.py](defillama_client.py) · [defillama_client.md](defillama_client.md) · [test_defillama_client.py](test_defillama_client.py)
- Archive: [cmccoingecko.zip](cmccoingecko.zip)

x402 rails (code + agent spec)
- [x402_rails.py](x402_rails.py) · [x402_rails_service.py](x402_rails_service.py) · [x402_signer.py](x402_signer.py)
- [x402rails.agent](x402rails.agent) — agent knowledge domain
- Tests: [test_x402_rails.py](test_x402_rails.py) · [test_x402_rails_service.py](test_x402_rails_service.py) · [test_x402_signer.py](test_x402_signer.py)

Archives & saved pages
- [iDEBT.zip](iDEBT.zip)
- `AR.IO Launches Credit Card Payments … CoinMarketCap.html` + its `_files/` asset dir (saved web page; `_files/` excluded by rule)

---

## 2. `docs/operations/` — deployment, runbooks, architecture deep-dives

- [BANKON_VAULT_COMPLETE_REVIEW.md](../operations/BANKON_VAULT_COMPLETE_REVIEW.md) — vault security review
- [COMPLETE_DELTAVERSE_PACKAGE.md](../operations/COMPLETE_DELTAVERSE_PACKAGE.md)
- [HARD_GATE_RUNBOOK.md](../operations/HARD_GATE_RUNBOOK.md) — x402 hard-gate operations
- [SHADOW_OVERLORD_GUIDE.md](../operations/SHADOW_OVERLORD_GUIDE.md) · [SHADOW_OVERLORD_RUNBOOK.md](../operations/SHADOW_OVERLORD_RUNBOOK.md) — OVERLORD protocol
- [AgenticPlace Integration Blueprint_ Parsec, x402, A2A, MCP, and AP2 Source Code Analysis.md](../operations/AgenticPlace%20Integration%20Blueprint_%20Parsec%2C%20x402%2C%20A2A%2C%20MCP%2C%20and%20AP2%20Source%20Code%20Analysis.md)
- [Arweave Integration for the BANKON Stack_ A Senior Architect's Deep-Dive.md](../operations/Arweave%20Integration%20for%20the%20BANKON%20Stack_%20A%20Senior%20Architect%27s%20Deep-Dive.md)
- [Lighthouse Storage Integration for mindX ….md](../operations/Lighthouse%20Storage%20Integration%20for%20mindX_%20Decentralized%20Permanent%20Storage%20for%20Autonomous%20Agents.md)
- [LiteLLM Integration for Cost Tracking and Metered Access_ 2026 Self-Hosted Deployment Guide.md](../operations/LiteLLM%20Integration%20for%20Cost%20Tracking%20and%20Metered%20Access_%202026%20Self-Hosted%20Deployment%20Guide.md)
- [mindX and the PYTHAI Agentic Stack_ Cognition, Identity, Governance, and HTTP-Native Payments.md](../operations/mindX%20and%20the%20PYTHAI%20Agentic%20Stack_%20Cognition%2C%20Identity%2C%20Governance%2C%20and%20HTTP-Native%20Payments.md)
- [mindX Efficiency Index_ Composite Model-Evaluation Metric Specification for the mindXtrain Alpha.md](../operations/mindX%20Efficiency%20Index_%20Composite%20Model-Evaluation%20Metric%20Specification%20for%20the%20mindXtrain%20Alpha.md)
- [mindX Observability Stack_ Production-Grade Self-Hosted Blueprint.md](../operations/mindX%20Observability%20Stack_%20Production-Grade%20Self-Hosted%20Blueprint.md)
- [mindx_pay2store_ Production-Grade Autonomous Arweave Archival Module for mindX Agents.md](../operations/mindx_pay2store_%20Production-Grade%20Autonomous%20Arweave%20Archival%20Module%20for%20mindX%20Agents.md) · mirrors: [shipping_pay2store.md](../operations/shipping_pay2store.md) · [shipping_pay2store_codebase1.md](../operations/shipping_pay2store_codebase1.md)
- [openclaw_mindx_research.md](../operations/openclaw_mindx_research.md)
- [Parsec, Sympatheia, and the Architecture of Effortless Settlement (hyperlinked).md](../operations/Parsec%2C%20Sympatheia%2C%20and%20the%20Architecture%20of%20Effortless%20Settlement%20%28hyperlinked%29.md)
- [PYTHAI and DELTAVERSE Deployment Guide_ Algorand Constitution, EVM Economy, and Agentic Architecture.md](../operations/PYTHAI%20and%20DELTAVERSE%20Deployment%20Guide_%20Algorand%20Constitution%2C%20EVM%20Economy%2C%20and%20Agentic%20Architecture.md)
- [PYTHAI_DELTAVERSE Zero-Knowledge Integration Architecture_ Four-Layer Cryptographic Fabric.md](../operations/PYTHAI_DELTAVERSE%20Zero-Knowledge%20Integration%20Architecture_%20Four-Layer%20Cryptographic%20Fabric.md)
- [PyTorch 2.x_ A Framework-Agnostic Technical Integration Reference (Mid-2026).md](../operations/PyTorch%202.x_%20A%20Framework-Agnostic%20Technical%20Integration%20Reference%20%28Mid-2026%29.md)
- [Hermes Agent Integration Patterns for mindX_ Self-Improving Architecture Analysis.md](../operations/Hermes%20Agent%20Integration%20Patterns%20for%20mindX_%20Self-Improving%20Architecture%20Analysismd)
- [THOT, THLNK, and ERC-7857 INFTs_ A Production Architecture for Agent Boardroom Governance.md](../operations/THOT%2C%20THLNK%2C%20and%20ERC-7857%20INFTs_%20A%20Production%20Architecture%20for%20Agent%20Boardroom%20Governance.md)
- [x402 Protocol_ HTTP-Native Stablecoin Payments Engineering Reference.md](../operations/x402%20Protocol_%20HTTP-Native%20Stablecoin%20Payments%20Engineering%20Reference.md)
- Archives: [daiotolenmulti.zip](../operations/daiotolenmulti.zip) · [deltaverse-x402.zip](../operations/deltaverse-x402.zip) · [thotconsiderations.zip](../operations/thotconsiderations.zip)

---

## 3. `docs/operations/dev/` — R&D tree (deepest private subtree)

### 3.1 Top-level dev
- [BANKON and 0G INFT (ERC-7857) Integration_ Definitive Technical Specification.md](../operations/dev/BANKON%20and%200G%20INFT%20%28ERC-7857%29%20Integration_%20Definitive%20Technical%20Specification.md)
- [BANKON and pythai.net Ecosystem_ Unified Integration Architecture and Mainnet Deployment Plan for DAIO, Parsec.md](../operations/dev/BANKON%20and%20pythai.net%20Ecosystem_%20Unified%20Integration%20Architecture%20and%20Mainnet%20Deployment%20Plan%20for%20DAIO%2C%20Parsec.md)
- [Cryptocurrency Privacy Protocols_ A Forensic and Technical Reference on Six Mixing and Anonymity Systems.md](../operations/dev/Cryptocurrency%20Privacy%20Protocols_%20A%20Forensic%20and%20Technical%20Reference%20on%20Six%20Mixing%20and%20Anonymity%20Systems.md)
- [ETHGlobal NYC 2026_ Strategic Submission Plan for the PYTHAI Stack.md](../operations/dev/ETHGlobal%20NYC%202026_%20Strategic%20Submission%20Plan%20for%20the%20PYTHAI%20Stack.md)
- [Vercel AI SDK 6_ A Framework-Agnostic Deep Dive (June 2026).md](../operations/dev/Vercel%20AI%20SDK%206_%20A%20Framework-Agnostic%20Deep%20Dive%20%28June%202026%29.md)
- [WISDOM_findings_zero_dependency_delivery.md](../operations/dev/WISDOM_findings_zero_dependency_delivery.md)
- [nodejs_review_pythai.md](../operations/dev/nodejs_review_pythai.md)
- [compass_artifact_wf-…_text_markdown.md](../operations/dev/compass_artifact_wf-6fd5491e-170d-463b-a6d6-9fe5c358db48_text_markdown.md)
- [x402 Multi-Rail Integration Reference_ EVM, Algorand (Parsec), and Arweave Permaweb (June 2026).md](../operations/dev/x402%20Multi-Rail%20Integration%20Reference_%20EVM%2C%20Algorand%20%28Parsec%29%2C%20and%20Arweave%20Permaweb%20%28June%202026%29.md)

### 3.2 `dev/ario/`
- [AO, Permaweb OS, and AR.IO/ARIO Ecosystem_ Utility and Integration Assessment for a 300k ARIO Holder.md](../operations/dev/ario/AO%2C%20Permaweb%20OS%2C%20and%20AR.IO_ARIO%20Ecosystem_%20Utility%20and%20Integration%20Assessment%20for%20a%20300k%20ARIO%20Holder.md)

### 3.3 `dev/DAIO/` — cross-chain governance
- [DAIO Cross-Chain Governance_ Agora Multichain Voting and LayerZero V2 Technical Reference.md](../operations/dev/DAIO/DAIO%20Cross-Chain%20Governance_%20Agora%20Multichain%20Voting%20and%20LayerZero%20V2%20Technical%20Reference.md)
- [DAIO Mainnet Deployment and Unified Agent-Commerce Payments Fabric for PYTHAI.md](../operations/dev/DAIO/DAIO%20Mainnet%20Deployment%20and%20Unified%20Agent-Commerce%20Payments%20Fabric%20for%20PYTHAI.md)
- [LayerZero V2 as DAIO's Cross-Chain Backbone_ A Battle-Hardened Architecture Brief.md](../operations/dev/DAIO/LayerZero%20V2%20as%20DAIO%27s%20Cross-Chain%20Backbone_%20A%20Battle-Hardened%20Architecture%20Brief.md)

### 3.4 `dev/ENS/` — bankon.eth subname registrar
- [BANKON ENS Subname Registrar_ ERC-7857 iNFT and ERC-6551 TBA Integration.md](../operations/dev/ENS/BANKON%20ENS%20Subname%20Registrar_%20ERC-7857%20iNFT%20and%20ERC-6551%20TBA%20Integration.md)
- [BANKON ENS Subname Registrar_ Production Architecture for bankon.eth.md](../operations/dev/ENS/BANKON%20ENS%20Subname%20Registrar_%20Production%20Architecture%20for%20bankon.eth.md)

### 3.5 `dev/ORACLE/` — PWAF / peg oracle
- [bankonoracle.md](../operations/dev/ORACLE/bankonoracle.md) · [pythai-bankon-oracle.md](../operations/dev/ORACLE/pythai-bankon-oracle.md)
- [Cross-Chain Wrapped Asset Architecture_ PWAF Defense-in-Depth Design vs LayerZero and CCIP.md](../operations/dev/ORACLE/Cross-Chain%20Wrapped%20Asset%20Architecture_%20PWAF%20Defense-in-Depth%20Design%20vs%20LayerZero%20and%20CCIP.md)
- [PegFactory-as-a-Service and EasyBasket Composer_ Cypherpunk2048 Production Specification.md](../operations/dev/ORACLE/PegFactory-as-a-Service%20and%20EasyBasket%20Composer_%20Cypherpunk2048%20Production%20Specification.md)
- [Tokenized SpaceX Pre-IPO Contracts and Bitcoin Treasury Peg Architecture Analysis.md](../operations/dev/ORACLE/Tokenized%20SpaceX%20Pre-IPO%20Contracts%20and%20Bitcoin%20Treasury%20Peg%20Architecture%20Analysis.md)

### 3.6 `dev/PYTH/` — Pyth Network
- [Pyth Network on Algorand_ Architecture Guide for Hermes Reads and Custom Pull Receivers.md](../operations/dev/PYTH/Pyth%20Network%20on%20Algorand_%20Architecture%20Guide%20for%20Hermes%20Reads%20and%20Custom%20Pull%20Receivers.md)
- [PYTH Token Utility and Economics_ A Project Integration Guide (May 2026).md](../operations/dev/PYTH/PYTH%20Token%20Utility%20and%20Economics_%20A%20Project%20Integration%20Guide%20%28May%202026%29.md)
- [pyth-utility-rage-publication.md](../operations/dev/PYTH/pyth-utility-rage-publication.md)

### 3.7 `dev/x402algo/`
- [x402 on Algorand_ Production Integration Reference for the PYTHAI, DELTAVERSE, and BANKON Ecosystem.md](../operations/dev/x402algo/x402%20on%20Algorand_%20Production%20Integration%20Reference%20for%20the%20PYTHAI%2C%20DELTAVERSE%2C%20and%20BANKON%20Ecosystem.md)
- (dev top-level mirror) [x402 on Algorand_ …Ecosystem.pdf.md](../operations/dev/x402%20on%20Algorand_%20Production%20Integration%20Reference%20for%20the%20PYTHAI%2C%20DELTAVERSE%2C%20and%20BANKON%20Ecosystem.pdf.md)

### 3.8 `dev/IDC/` — Inheritable Debt Currency (extracted codebase)
Primary docs:
- [Forking Olympus DAO and Designing IDC v3_ Inheritable Debt Currency Technical Guide.md](../operations/dev/IDC/Forking%20Olympus%20DAO%20and%20Designing%20IDC%20v3_%20Inheritable%20Debt%20Currency%20Technical%20Guide.md)
- [customAlgoDEXmirrorToken.md](../operations/dev/IDC/customAlgoDEXmirrorToken.md) · [explanation.md](../operations/dev/IDC/explanation.md)

`dev/IDC/iDEBT/` — inheritable/inverse-debt R&D (BONA FIDE, DAIO deploy, x402):
- [BONAFIDEarchitecture.md](../operations/dev/IDC/iDEBT/BONAFIDEarchitecture.md) · [DAIO_DEPLOYMENT_INTEGRATION.md](../operations/dev/IDC/iDEBT/DAIO_DEPLOYMENT_INTEGRATION.md) · [DELTAVERSE_2026_Launch_Manifesto.md](../operations/dev/IDC/iDEBT/DELTAVERSE_2026_Launch_Manifesto.md)
- [apimonetizationandx402.md](../operations/dev/IDC/iDEBT/apimonetizationandx402.md) · [arbitrage_dex_full_system.md](../operations/dev/IDC/iDEBT/arbitrage_dex_full_system.md)
- [OpenBDKcrosschainbridge.md](../operations/dev/IDC/iDEBT/OpenBDKcrosschainbridge.md) · [zkEVMpolygonbridge.md](../operations/dev/IDC/iDEBT/zkEVMpolygonbridge.md)
- [PYTHAI_Tokenomics_and_Governance.md](../operations/dev/IDC/iDEBT/PYTHAI_Tokenomics_and_Governance.md)
- [Synthetix-to-Algorand RWA Architecture_ A Complete Blueprint for Real World Asset as a Service.md](../operations/dev/IDC/iDEBT/Synthetix-to-Algorand%20RWA%20Architecture_%20A%20Complete%20Blueprint%20for%20Real%20World%20Asset%20as%20a%20Service.md)
- [The Cryptographic Inheritance of Global Debt_ A Research Compendium.md](../operations/dev/IDC/iDEBT/The%20Cryptographic%20Inheritance%20of%20Global%20Debt:%20A%20Research%20Compendium.md)

> **`dev/IDC/iDEBT/iDEBT/` is an extracted multi-copy codebase.** It contains the canonical
> `inversedebt-project/` (docs: ARCHITECTURE, MECHANICS, TECHNICAL, THESIS, TESTING, FRONTEND_INTEGRATION;
> plus `algorand/`, `evm/audit/`, `idebt-nft/`, `frontend/`, `ui/`), the `AlgorandiDEBTandTHESIS/`
> thesis set, `globaldebtcoin/`, `compoundinterest/`, and **five near-duplicate working copies**
> (`idebt`, `idebt (2)`–`idebt (5)`, `iDEBT (2)`) each carrying the same `deploy/technical/usage/
> architecture/README` docs. All are gated. The vendored `inversedebt-project/ui/node_modules/`
> (~690 third-party `.md` files) is **excluded from ingest by rule** and not indexed here — treat
> `node_modules/`, `lib/forge-std/`, `lib/openzeppelin-contracts/` inside this tree as noise.

---

## 4. `docs/publications/pdf/` — PDF renders + `.md` mirrors (OFF LIMITS)

The public publication stream (`publications/*.md`, `publications/daily/`) stays public. **Only the
`pdf/` subtree is gated** — every rendered PDF below, plus any `.md` mirror carrying the same content.
Markdown sources for many of these live under `operations/`, `blockchain/`, or top-level `publications/`
(e.g. `openclaw_mindx_research.md.pdf` ↔ `operations/openclaw_mindx_research.md`); wherever a `.md`
mirrors a gated PDF, that mirror is off limits too.

- Arweave Integration for the BANKON Stack_ A Senior Architect's Deep-Dive.pdf
- BANKON_KEEPERHUB_ARCHITECTURE.pdf
- book-of-liquidity.pdf
- COMPLETE_DELTAVERSE_PACKAGE.pdf
- DefiLlama Integration Guide for Agentic AI Systems.pdf
- DELTAVERSE Integration Specification_ Post-Quantum Agents, Identity, and Payments Stack.pdf
- Deploying 100,000 ARIO on Base_ An Arweave and AR.IO Technical Playbook.pdf
- Four Trillion-Dollar Bets and One Sovereign Wager.pdf
- Hermes Agent Integration Patterns for mindX_ Self-Improving Architecture Analysis.pdf
- IPFS Integration and Chain Surface Mapping for the PYTHAI Project Suite.pdf
- Lighthouse Storage Integration for mindX_ Decentralized Permanent Storage for Autonomous Agents.pdf
- Lighthouse Storage Integration for mindX_ Technical Reference Guide.pdf
- mindX and the PYTHAI Agentic Stack_ Cognition, Identity, Governance, and HTTP-Native Payments.pdf
- mindX Knowledge Catalogue_ A CQRS Projection Layer Subsystem Specification.pdf
- mindX Observability Stack_ Production-Grade Self-Hosted Blueprint.pdf
- mindx_pay2store_ Production-Grade Autonomous Arweave Archival Module for mindX Agents.pdf
- openclaw_mindx_research.md.pdf
- OpenRouter Integration Manual for mindX_ Production-Grade LLM Backplane Architecture.pdf
- PYTHAI and DELTAVERSE Deployment Guide_ Algorand Constitution, EVM Economy, and Agentic Architecture.pdf
- PYTHAI_DELTAVERSE Zero-Knowledge Integration Architecture_ Four-Layer Cryptographic Fabric.pdf
- PyTorch 2.x_ A Framework-Agnostic Technical Integration Reference (Mid-2026).pdf
- Quantum Machine Learning Code Compendium_ A 2026 Reference and Recovery Atlas.pdf
- SkillForge_ A Pydantic AI Agent for Autonomous SKILL.md Authoring on mindX.pdf
- Solidity-to-Frontend Interaction and Browser Deployment_ Open-Source Templates and Reference Architecture for the PYTHAI_BANKON Ecosystem.pdf
- The DeltaVerse Substrate_ Canonical Architectural Design Specification for an AI-Native Agent-Driven Verse.pdf
- THOT, THLNK, and ERC-7857 INFTs_ A Production Architecture for Agent Boardroom Governance.pdf
- Vercel AI SDK 6_ A Framework-Agnostic Deep Dive (June 2026).pdf
- vercel_AISDK_mindX.pdf
- WebXR Adoption for the DeltaVerse BubbleRoom_ Mid-2026 Definitive Guide.pdf
- x402 Multi-Rail Integration Reference_ EVM, Algorand (Parsec), and Arweave Permaweb (June 2026).pdf
- x402 on Algorand_ Production Integration Reference for the PYTHAI, DELTAVERSE, and BANKON Ecosystem.pdf
- xmlsidewaysfuture.pdf

`pdf/paywall/` — reserved for x402-paywalled renders (currently empty).

---

_Maintenance: this NAV is a projection of `PRIVATE_DOC_PREFIXES` in `utils/reference_corpus.py`.
When files are added under `operations/`, `blockchain/`, or `publications/pdf/`, re-scan and update.
Never link this file or its targets from `/docs.html`, `DOC_INDEX.md`, or any public surface._
