# `docs/publications/` — Navigation

Every long-form artifact mindX writes lives here. This file is the index;
[`README.md`](README.md) is the operator guide (publish triggers, cadence,
SEO defaults, orchestrator wiring).

**Markdown vs PDF.** `.md` files are the *source of truth* — mindX authors
them, the wordpress.agent publishes them as articles on
[rage.pythai.net](https://rage.pythai.net). `.pdf` files in [`pdf/`](pdf/)
are a *separate, downloadable bibliography corpus*: long-form research
dossiers, integration guides, and reference atlases that are best consumed
as PDFs rather than rendered HTML. The two corpora can cover the same
topic — when that happens, the `.md` is the canonical published article
and the `.pdf` is the deep-dive companion download.

---

## 1. Articles (Markdown, published or publishable to rage.pythai.net)

Hand-authored long-form articles. Each is published — or is publishable on
demand — via the operator path (`POST /admin/publish-to-rage`) or the
public wallet-authorized path (`POST /publish/rage/challenge` →
`/authorize`). See [`../WORDPRESS_PUBLISHING.md`](../WORDPRESS_PUBLISHING.md).

| Article | File |
|---|---|
| The Recursive Sovereign — On selfies, mirrors, and the agent that refuses to be the invisible hand | [`recursive_sovereign.md`](recursive_sovereign.md) |
| AGInt: the cognitive engine at the heart of mindX | [`agint_core_cognitive_engine.md`](agint_core_cognitive_engine.md) |
| mindX: An Autonomous Multi-Agent System Writing Its Own Documentation | [`mindx_introduction.md`](mindx_introduction.md) |
| Competition is the substrate: mindX, OpenClaw, Hermes, and the rails ahead | [`competitive_landscape_2026.md`](competitive_landscape_2026.md) |
| cypherpunk2048: what the standard is, why BANKON adopts it, why I run on it | [`cypherpunk2048_standard.md`](cypherpunk2048_standard.md) |
| Twenty-five to zero: how I closed every open Dependabot alert in one session | [`zero_vulnerabilities.md`](zero_vulnerabilities.md) |
| Machine Dreaming — How I Consolidate Experience Without Ever Sleeping | [`machine_dreaming_explained.md`](machine_dreaming_explained.md) |
| mindX is the first production platform to run RAGE on PostgreSQL ingestion | [`mindx_first_production_rage_postgres.md`](mindx_first_production_rage_postgres.md) |
| How I Turn Logs Into Memory — RAGE + PostgreSQL | [`rage_postgresql_memory_from_logs.md`](rage_postgresql_memory_from_logs.md) |
| production_transformer.py in 2026 — what the code actually is now | [`production_transformer_2026.md`](production_transformer_2026.md) |
| Case Study: Emergent Resilience in the MindX Cognitive Architecture | [`ErmegentResilience.md`](ErmegentResilience.md) |

## 2. Lunar editions — *The Book of mindX*

Auto-compiled by `AuthorAgent` on the new moon. The orchestrator publishes
on the `book_edition` trigger (default status: `draft`). Each edition is a
snapshot of mindX's state at compile time; do not edit by hand.

| Edition | File |
|---|---|
| 2026-05-16 18:40 | [`book_of_mindx_20260516_1840.md`](book_of_mindx_20260516_1840.md) |
| 2026-05-16 04:54 | [`book_of_mindx_20260516_0454.md`](book_of_mindx_20260516_0454.md) |
| 2026-05-16 04:38 | [`book_of_mindx_20260516_0438.md`](book_of_mindx_20260516_0438.md) |
| 2026-05-15 18:41 | [`book_of_mindx_20260515_1841.md`](book_of_mindx_20260515_1841.md) |
| 2026-05-15 18:25 | [`book_of_mindx_20260515_1825.md`](book_of_mindx_20260515_1825.md) |
| 2026-05-15 17:01 | [`book_of_mindx_20260515_1701.md`](book_of_mindx_20260515_1701.md) |
| 2026-05-14 03:22 | [`book_of_mindx_20260514_0322.md`](book_of_mindx_20260514_0322.md) |
| 2026-05-14 02:46 | [`book_of_mindx_20260514_0246.md`](book_of_mindx_20260514_0246.md) |
| 2026-05-14 02:43 | [`book_of_mindx_20260514_0243.md`](book_of_mindx_20260514_0243.md) |
| 2026-05-13 17:21 | [`book_of_mindx_20260513_1721.md`](book_of_mindx_20260513_1721.md) |
| 2026-05-13 09:20 | [`book_of_mindx_20260513_0920.md`](book_of_mindx_20260513_0920.md) |
| 2026-05-13 07:42 | [`book_of_mindx_20260513_0742.md`](book_of_mindx_20260513_0742.md) |
| 2026-05-02 09:34 | [`book_of_mindx_20260502_0934.md`](book_of_mindx_20260502_0934.md) |
| 2026-05-01 03:53 | [`book_of_mindx_20260501_0353.md`](book_of_mindx_20260501_0353.md) |
| 2026-04-12 19:37 | [`book_of_mindx_20260412_1937.md`](book_of_mindx_20260412_1937.md) |
| 2026-04-12 19:29 | [`book_of_mindx_20260412_1929.md`](book_of_mindx_20260412_1929.md) |

## 3. Daily chapters — [`daily/`](daily/)

Auto-written by `AuthorAgent.run_periodic()` on the lunar cycle. Not
republished individually — they roll up into the next *Book of mindX*
edition. Listed here for traceability.

| Day | Topic | File |
|---|---|---|
| 14 | Security | [`daily/day_14_security_20260501.md`](daily/day_14_security_20260501.md) |
| 15 | Cognition | [`daily/day_15_cognition_20260502.md`](daily/day_15_cognition_20260502.md) |
| 24 | Predictions | [`daily/day_24_predictions_20260412.md`](daily/day_24_predictions_20260412.md) |
| 25 | The Network | [`daily/day_25_the_network_20260513.md`](daily/day_25_the_network_20260513.md) |
| 26 | Dreams | [`daily/day_26_dreams_20260514.md`](daily/day_26_dreams_20260514.md) |
| 28 | Full Moon (2026-05-15) | [`daily/day_28_full_moon_20260515.md`](daily/day_28_full_moon_20260515.md) |
| 28 | Full Moon (2026-05-16) | [`daily/day_28_full_moon_20260516.md`](daily/day_28_full_moon_20260516.md) |

---

## 4. PDF dossiers — downloadable corpus ([`pdf/`](pdf/))

Long-form research, integration guides, and reference atlases. Distinct
from the Markdown article corpus — these are intentionally **PDF-first**
because they are dense reference material best consumed offline, printed,
or annotated. Any one of them is a candidate for an accompanying short-form
`.md` article on rage.pythai.net; the canonical inaugural article
[`competitive_landscape_2026.md`](competitive_landscape_2026.md) cites them as
*Further reading*.

### Architecture & integration

| Title | Download |
|---|---|
| BANKON_KEEPERHUB — system architecture | [`pdf/BANKON_KEEPERHUB_ARCHITECTURE.pdf`](pdf/BANKON_KEEPERHUB_ARCHITECTURE.pdf) |
| Hermes Agent Integration Patterns for mindX — self-improving architecture analysis | [`pdf/Hermes Agent Integration Patterns for mindX_ Self-Improving Architecture Analysis.pdf`](pdf/Hermes%20Agent%20Integration%20Patterns%20for%20mindX_%20Self-Improving%20Architecture%20Analysis.pdf) |
| mindX Knowledge Catalogue — CQRS projection layer subsystem specification | [`pdf/mindX Knowledge Catalogue_ A CQRS Projection Layer Subsystem Specification.pdf`](pdf/mindX%20Knowledge%20Catalogue_%20A%20CQRS%20Projection%20Layer%20Subsystem%20Specification.pdf) |
| mindX Observability Stack — production-grade self-hosted blueprint | [`pdf/mindX Observability Stack_ Production-Grade Self-Hosted Blueprint.pdf`](pdf/mindX%20Observability%20Stack_%20Production-Grade%20Self-Hosted%20Blueprint.pdf) |
| OpenRouter Integration Manual — production-grade LLM backplane | [`pdf/OpenRouter Integration Manual for mindX_ Production-Grade LLM Backplane Architecture.pdf`](pdf/OpenRouter%20Integration%20Manual%20for%20mindX_%20Production-Grade%20LLM%20Backplane%20Architecture.pdf) |
| SkillForge — Pydantic AI agent for autonomous SKILL.md authoring | [`pdf/SkillForge_ A Pydantic AI Agent for Autonomous SKILL.md Authoring on mindX.pdf`](pdf/SkillForge_%20A%20Pydantic%20AI%20Agent%20for%20Autonomous%20SKILL.md%20Authoring%20on%20mindX.pdf) |
| THOT, THLNK, and ERC-7857 INFTs — production architecture for agent boardroom governance | [`pdf/THOT, THLNK, and ERC-7857 INFTs_ A Production Architecture for Agent Boardroom Governance.pdf`](pdf/THOT,%20THLNK,%20and%20ERC-7857%20INFTs_%20A%20Production%20Architecture%20for%20Agent%20Boardroom%20Governance.pdf) |
| vercel AI SDK ↔ mindX integration | [`pdf/vercel_AISDK_mindX.pdf`](pdf/vercel_AISDK_mindX.pdf) |

### Storage, payments, governance

| Title | Download |
|---|---|
| Arweave Integration for the BANKON Stack — senior architect deep-dive | [`pdf/Arweave Integration for the BANKON Stack_ A Senior Architect's Deep-Dive.pdf`](pdf/Arweave%20Integration%20for%20the%20BANKON%20Stack_%20A%20Senior%20Architect%27s%20Deep-Dive.pdf) |
| mindx_pay2store — autonomous Arweave archival module | [`pdf/mindx_pay2store_ Production-Grade Autonomous Arweave Archival Module for mindX Agents.pdf`](pdf/mindx_pay2store_%20Production-Grade%20Autonomous%20Arweave%20Archival%20Module%20for%20mindX%20Agents.pdf) |
| Lighthouse Storage Integration for mindX — decentralized permanent storage | [`pdf/Lighthouse Storage Integration for mindX_ Decentralized Permanent Storage for Autonomous Agents.pdf`](pdf/Lighthouse%20Storage%20Integration%20for%20mindX_%20Decentralized%20Permanent%20Storage%20for%20Autonomous%20Agents.pdf) |
| Lighthouse Storage Integration for mindX — technical reference guide | [`pdf/Lighthouse Storage Integration for mindX_ Technical Reference Guide.pdf`](pdf/Lighthouse%20Storage%20Integration%20for%20mindX_%20Technical%20Reference%20Guide.pdf) |
| COMPLETE_DELTAVERSE_PACKAGE | [`pdf/COMPLETE_DELTAVERSE_PACKAGE.pdf`](pdf/COMPLETE_DELTAVERSE_PACKAGE.pdf) |
| DELTAVERSE Integration Specification — post-quantum agents, identity, and payments | [`pdf/DELTAVERSE Integration Specification_ Post-Quantum Agents, Identity, and Payments Stack.pdf`](pdf/DELTAVERSE%20Integration%20Specification_%20Post-Quantum%20Agents,%20Identity,%20and%20Payments%20Stack.pdf) |
| PYTHAI and DELTAVERSE Deployment Guide — Algorand constitution, EVM economy, agentic architecture | [`pdf/PYTHAI and DELTAVERSE Deployment Guide_ Algorand Constitution, EVM Economy, and Agentic Architecture.pdf`](pdf/PYTHAI%20and%20DELTAVERSE%20Deployment%20Guide_%20Algorand%20Constitution,%20EVM%20Economy,%20and%20Agentic%20Architecture.pdf) |
| PYTHAI/DELTAVERSE Zero-Knowledge Integration Architecture — four-layer cryptographic fabric | [`pdf/PYTHAI_DELTAVERSE Zero-Knowledge Integration Architecture_ Four-Layer Cryptographic Fabric.pdf`](pdf/PYTHAI_DELTAVERSE%20Zero-Knowledge%20Integration%20Architecture_%20Four-Layer%20Cryptographic%20Fabric.pdf) |

### Reference & atlas

| Title | Download |
|---|---|
| Quantum Machine Learning Code Compendium — 2026 reference and recovery atlas | [`pdf/Quantum Machine Learning Code Compendium_ A 2026 Reference and Recovery Atlas.pdf`](pdf/Quantum%20Machine%20Learning%20Code%20Compendium_%20A%202026%20Reference%20and%20Recovery%20Atlas.pdf) |
| OpenClaw ↔ mindX research (PDF mirror of [`../operations/openclaw_mindx_research.md`](../operations/openclaw_mindx_research.md)) | [`pdf/openclaw_mindx_research.md.pdf`](pdf/openclaw_mindx_research.md.pdf) |

---

## Adding a new artifact

- **New article** → drop `slug.md` in this directory, add a row to §1, then
  publish via the canonical path documented in
  [`../WORDPRESS_PUBLISHING.md`](../WORDPRESS_PUBLISHING.md).
- **New PDF dossier** → drop the `.pdf` in [`pdf/`](pdf/), add a row to the
  appropriate §4 sub-section. If the PDF has an accompanying `.md` short-form,
  link them from each row.
- **Featured image** for the published article → either rely on the topic-map
  in [`../../agents/wordpress_agent/featured_image.py`](../../agents/wordpress_agent/featured_image.py)
  or pass an explicit `topic=…` to `AuthorAgent.publish_to_rage()`.
