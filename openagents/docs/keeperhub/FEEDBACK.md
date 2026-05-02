# KeeperHub Builder Feedback — mindX integration

> Submitted to the **KeeperHub Builder Feedback Bounty** ($500 pool, 2 × $250) at ETHGlobal Open Agents.
> Drafted during integration of the `mindX × AgenticPlace × KeeperHub` bidirectional x402 bridge (`openagents/keeperhub/bridge_routes.py`).
> Dates reference 2026-04-27 unless otherwise noted.

## Summary of integration

mindX exposes paid AgenticPlace endpoints as KH-compatible 402 challenges (Base USDC + Tempo MPP) under `/p2p/keeperhub/*`, and consumes paid KH workflows from Python via a hand-rolled EIP-3009 client (`tools/keeperhub_x402_client.py`). End-to-end works against the public KH endpoints. Items below are issues we hit during this integration that would tangibly improve the experience for future builders.

---

## 1. Documentation gaps

### 1.1 `/introduction/what-is-keeperhub` returns HTTP 404
- **Where:** docs.keeperhub.com (top-level intro link from the marketing page)
- **Impact:** First-time visitors hit a dead end.
- **Suggested fix:** redirect to `/introduction` or update the navigation anchor.

### 1.2 No "fee-payer leg" pricing example for the 402 caller
- **Where:** all paid-workflow docs
- **What's missing:** an explicit worked example of who pays gas for the EIP-3009 `transferWithAuthorization` settlement (KH? caller? facilitator on KH's behalf?). For Base USDC the gas is meaningful relative to a $0.005 charge.
- **Suggested fix:** add a "who-pays-what" matrix per network (Base vs Tempo) in the `/workflows/paid-workflows` page.

### 1.3 Tempo / MPP USDC.e address not enumerated
- The `KH_MPP_USDC_ADDRESS` for Tempo (chain 4217) is referenced in our bridge code but not directly published in a single doc page; we had to infer from blog posts. Worth a single canonical "supported assets" table.

---

## 2. SDK gaps

### 2.1 No first-party Python SDK
- We had to hand-roll a 200-line EIP-3009 signer + 402-retry client in `tools/keeperhub_x402_client.py` to consume paid workflows from a Python codebase. mindX is Python.
- **Suggested:** publish a `keeperhub-py` matching `@keeperhub/wallet`'s surface. Even a thin Hatch-packaged port would unlock an entire ecosystem (FastAPI agents, LangChain, CrewAI Python).

### 2.2 `@keeperhub/wallet` v0.1.7 was published 2026-04-21 — six days before the hackathon
- **Risk:** breaking changes during the hackathon window. We pinned to v0.1.7 in `package.json` to avoid drift.
- **Suggested:** publish a v0.1.x stability statement or freeze API contract for the duration of the hackathon judging window.

### 2.3 No type definitions for the 402 challenge envelope
- `accepts` shape varies subtly by version (we saw both `paymentRequirements` and `accepts` in the wild). A formal JSON Schema or `.d.ts` would help cross-language clients.
- **Suggested:** publish `@keeperhub/x402-schema` (JSON Schema + zod schema + Python pydantic models).

---

## 3. Behaviour / API friction

### 3.1 MCP server is org-scoped — multi-org agents must switch tokens per call
- For an agentic platform like mindX where one process serves multiple tenants, this forces per-tenant client construction. Single MCP connection that authorizes per-call would be cleaner.
- **Suggested:** accept `X-KH-Org` header on the MCP endpoint as a per-request override.

### 3.2 No on-chain consumer interface for "bring your own facilitator"
- KH validates payments server-side. There is no escape hatch for a customer who wants to verify settlement on-chain themselves (e.g. our boardroom wants to audit every paid call). This is acceptable for hackathon; long-term, a settlement-proof endpoint (`GET /settlements/<id>/proof`) would help skeptical procurement teams.
- **Suggested:** publish settlement Merkle inclusion proofs after batch finalization.

### 3.3 Webhook signature scheme is undocumented
- We implemented HMAC-SHA256 over the raw body using a shared secret in `bridge_routes.py:kh_workflow_callback` based on conventional patterns. Could not find an authoritative spec for the exact scheme KH uses.
- **Suggested:** add a "verifying webhook signatures" page with a worked example in TS, Python, Go.

---

## 4. Discoverability

### 4.1 No public list of registered paid workflows
- Hard to browse what other people have published. Reduces network effect.
- **Suggested:** add a public directory at `https://app.keeperhub.com/workflows` (opt-in per workflow) so caller-side teams can discover what's available without scraping.

### 4.2 Hackathon partnership announcement could link the EIP-3009 spec
- The blog post (`/blog/008-first-hackathon-openagents`) is great context but doesn't link out to the underlying x402 standard or the EIP-3009 spec. New builders have to follow the chain backwards.

---

## 5. Positive notes (mergeable quality)

- **Dual-network 402 is excellent design.** Letting wallets pick base or Tempo based on their balance is exactly the right primitive — we modeled our bridge envelope (`openagents/keeperhub/bridge_routes.py:_build_kh_challenge`) on it directly.
- **EIP-3009 over EIP-2612 was the right call** — `transferWithAuthorization` removes the approval round-trip cleanly.
- **Turnkey-backed wallets** are a strong default for solo developers — we did not have to manage key material to receive USDC on Base. Excellent UX.
- **The `kh` CLI** is well-organized; `kh serve --mcp` (deprecated) was useful for local development.

---

## Contact

mindX team via codephreak (Telegram: TBD, X: TBD).
Submission repository: github.com/Professor-Codephreak/mindX
