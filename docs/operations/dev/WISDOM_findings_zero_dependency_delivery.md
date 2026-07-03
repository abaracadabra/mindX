# WISDOM Findings: Zero-Dependency Knowledge Delivery as Security Doctrine

**Status: gated reference (ingest-only).** Analysis of the WISDOM daemon
(`wisdom.zip`, repo root — 437 lines, Apache-2.0) for AuthorAgent to later
rewrite for the public surface. Companion to
[nodejs_review_pythai.md](nodejs_review_pythai.md), which states the doctrine
this codebase proves.

---

## I. What WISDOM is

A PYTHAI knowledge-delivery daemon in **437 lines of pure `node:` core** —
`server.mjs` (84) + five lib modules (270) + tests (83). No Express, no
framework, no npm install. Every file uploaded is born `0600` under
`process.umask(0o077)`, content-addressed by SHA-256, registered to its
uploader's Algorand address, and released only against a settled x402 payment
signed by parsec-wallet on Algorand mainnet. Bandwidth is a paid dimension:
the purchased tier sets the bytes-per-second of the stream
(`lib/throttle.mjs`). Routes: free `/llms.txt` menu, `POST /asset` (receipt),
`GET /asset/<digest>` (402 → pay → verified txid, single-use → throttled
stream), `/health`.

## II. The findings that matter

### 1. Zero dependencies is a measurable security posture, not an aesthetic

The same day this analysis was written, the mindX repo carried **26 open
Dependabot alerts — every single one npm** (protobufjs critical
CVE-2026-41242, path-to-regexp, qs, ws, vite, rollup, minimatch, picomatch,
postcss, brace-expansion). WISDOM's attack surface for that entire class is
**zero**: there is no supply chain to attack because there is no supply
chain. The README's one-liner is empirically grounded in this repo's own
security tab.

The triage of those 26 alerts surfaced a second-order lesson WISDOM never has
to learn: remediation itself is risky. Two `"package": ">=fixed"` overrides
resolved to the next *major* version on fresh install (path-to-regexp
0.1.x→8.x under Express 4, protobufjs 7.x→8.x under @google/genai) — patches
that would have taken the service down. A dependency tree makes even the
*fixes* dangerous.

### 2. The Node Permission Model as default boot posture

`npm start` is `node --permission --allow-fs-read=. --allow-fs-write=./vault,./state`
— deny-by-default, grant-by-declaration, with an `audit:perms` script and a
Node 26 variant gating network egress too. This is the "cleanhouse guide"
section of the Node review running in production form: the daemon cannot
read the operator's home directory, spawn processes, or load native addons
*even if exploited*, because the runtime never granted those authorities.

### 3. Settled payment IS the credential

No accounts, no API keys, no sessions, no JWT. `GET /asset/<digest>` returns
402 with algorand-mainnet terms; the client pays with note
`base64("x402:<digest>:<tierId>")`; retry with `X-PAYMENT` verifies the txid
on-chain (single-use) and streams at the paid tier. A mindX agent, an
llms.txt crawler, and a human browser walk the identical path. Contrast with
mindX's own gate stack (vault sessions + API keys + shadow-overlord JWT —
three credential systems): WISDOM collapses authentication, authorization,
and billing into one on-chain fact.

### 4. Octal permissions as second enforcement layer

Policy choices map to kernel octets server-side (`private 0600`, `gated
0640`, `gated-executable 0750`, `public 0644`; unknown input collapses to
`0600`). No `.htaccess` — policy lives in committed code and in the
filesystem's own permission bits, so a bypass of the HTTP layer still meets
the kernel's enforcement. This rhymes with mindX's reference-corpus design
(handler-level gates that hold regardless of middleware mode) but adds the
OS as a third, code-independent layer.

### 5. Deployment posture is part of the artifact

Podman + quadlet (`deploy/wisdom.container`): read-only root, all
capabilities dropped, `NoNewPrivileges`, vault/state on named volumes,
`DEFAULT_PAY_TO` set to the BANKON settlement address. License section:
"No admin keys post-deploy. No upgradeable anything." The EVM mirror
(X402AccessGate, DAIO stack) is Foundry-tested; this daemon is the Algorand
leg.

## III. Where it sits in the PYTHAI lattice

- **bankon.pythai.net** — x402 payment gateway (standalone); WISDOM settles
  to the BANKON address.
- **mindx.algo via parsec** — the Algorand identity that signs; .algo-as-a-
  service with any-payment-to-any-payment x402 settlement is the rail WISDOM
  prices against.
- **pay2play / pay2store** — WISDOM is the delivery half: pay2store archives
  (Arweave, ARIO-owned gateway), WISDOM meters delivery. Together they make
  knowledge a priced, throttled, sovereign asset class.
- **mindX** — remains the knowledge-delivery and self-improvement service;
  WISDOM is the agnostic module that does the *gated serving* so mindX
  doesn't have to host payments logic (modules migrate out; mindX consumes).

## IV. Recommendations for mindX (ingest-stage, not yet public)

1. **Adopt the doctrine where Node already runs**: `mindx_frontend_ui`
   (Express, 5 of the 26 alerts, three runtime CVEs live on prod until
   redeployed) is the obvious candidate for either a permission-model boot
   flag or an eventual WISDOM-style core-only rewrite — it serves static
   files and proxies; Express is barely load-bearing there.
2. **`/reference` and WISDOM should converge**: the reference corpus is
   gated by session; WISDOM gates by settled payment. When the corpus
   graduates from "private pending audit" to "priced knowledge," the
   `/reference/file/` route's job description is exactly WISDOM's.
3. **llms.txt-as-menu** matches the wordpress.tool llms.txt work — a free,
   machine-readable catalogue in front of priced assets is becoming the
   PYTHAI house pattern; reference.html's catalog endpoint should keep that
   shape in mind.
4. AuthorAgent rewrite target: a public protocol essay — "there is no supply
   chain to attack" — pairing this repo's 26-alert triage (evidence) with
   WISDOM's 437 lines (alternative). The numbers carry the argument.
