# Documenter Agent (`documenter.agent`)

> **Status: yet to be registered** — pending on-chain registration in the AgenticRegistry / agentregistry.
> Part of the mindX suite of yet-to-be-registered agents.

## Overview

The Documenter Agent organizes a deployer's contracts and contract-deployment suites into a clean,
navigable structure and **imports the scattered `.md` documentation** for each contract — the docs that
live all over the ecosystem (mindX, `mindX/openagents`, daio/contracts, parsec, x402-demo, …), named
after the contract (`registry.sol` → `registry.md`). It is the "keeper of contract docs."

Reference implementation: `DeltaVerse/scripts/doc-contracts.mjs` (zero-dependency Node, re-runnable,
`--check` for CI).

## What it does

1. **Sources every contract + suite** — from the deployer's `deploy/suites/*.xml` manifests and the
   Algorand collection (`engine/ngn/algo-index.js` `DVAlgoIndex`), including future/planned suites.
2. **Finds the scattered doc** — indexes `*.md` across the project roots and matches each contract by
   name / id / source-file base (with prefix-stripping: `aORC-`, `overlord-`, `bonafide-`, …).
3. **Imports or generates** — imports the matched `.md` into `docs/contracts/<suite>/<Name>.md` (with
   provenance), or generates a structured summary from the manifest (suite · concept · chain · stage ·
   DEPLOY→LAUNCH value · owner/privilege · constructor args · artifact · indexing surface · source).
4. **Preserves hand-written docs** (case/separator-insensitive) and writes a `docs/contracts/INDEX.md`.

## Inputs / outputs

- **In:** suite manifests + the contract `.md` corpus across the ecosystem.
- **Out:** `docs/contracts/<suite>/<Name>.md` (one per contract) + `INDEX.md`. Generated docs carry a
  `DV-CONTRACT-DOC` marker so re-runs are idempotent; imported docs carry their source provenance.

## A2A / persona

- **Role:** documentation curator (read-only over source repos; writes only docs).
- **Capabilities:** doc discovery, contract-manifest parsing, import/generate, index synthesis.
- **Traits:** thorough, faithful (imports verbatim with provenance), non-destructive (never clobbers
  hand-written docs), idempotent.
- **Registration:** to register, mint its persona iNFT via AutoMINDX and list it in the AgenticRegistry
  (the same path the aORC registry/minter use). Until then it operates as an unregistered local agent.

## Homage

Documentation is the web-of-trust for code. Homage to Dr. Richard S. Wallace (AIML, 1999) — the lineage
of machine-authored, auditable knowledge.
