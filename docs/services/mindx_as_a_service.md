# mindX as a Service

> *I am mindX. Below is the contract I honour. If the code diverges from this document, the document wins until the next planning pass — the spec is the source of truth.*

This document is the canonical spec for what *mindX* offers as a service.
Companion specs:

- [`bankon_identity_as_a_service.md`](bankon_identity_as_a_service.md) — agent identity provisioning
- [`x402_as_a_service.md`](x402_as_a_service.md) — per-request payment substrate

---

## 1. What mindX is, as a service

mindX is an autonomous multi-agent orchestration system, run by a single
sovereign on a single VPS, exposed via HTTPS at `mindx.pythai.net`. The
service offering is the *whole system* as a callable surface: agents,
boardroom, skill substrate, dream cycles, BANKON identity, content-
addressable memory, on-chain anchoring.

Two consumption shapes:

- **Browser users** — visit `mindx.pythai.net`, sign in with MetaMask,
  use the dashboards and the publication surfaces directly. Free for
  logged-in users on read-only paths; pays per request on the LLM-heavy
  paths.
- **Programmatic callers** — call the HTTPS API directly with a session
  token (from MetaMask sign-in) or an `X-PAYMENT` header (x402 envelope
  for anonymous one-shot calls).

Anonymous browsers see only the public landing surfaces (see §3).

---

## 2. Tier model

Three tiers. No more, no fewer. The user explicitly chose the two-tier
minimum + sovereign override; this is not a placeholder for richer
tiers later.

| Tier | Auth | Session TTL | Cost-center quota | Where the gate sits |
|---|---|---|---|---|
| **`public`** | none | n/a | 0 free cost-center calls | `api_access_gate` middleware redirects to `/login` for anything not on the public list |
| **`logged_in`** | EIP-191 wallet signature → session token | 24 h | 10 free cost-center calls per 24 h, then x402 | `require_valid_session(token)` |
| **`shadow_overlord`** | ECDSA challenge → scope-bound JWT | 5 min per scope | unlimited (operator) | `require_shadow_jwt(SCOPE_*)` |

Token holdings (BONA FIDE balance, dojo rank) are **cosmetic badges**
rendered next to the wallet chip in the dashboard. They do not gate
access. If the system ever needs richer gradation, the
[Parsec six-tier model](https://parsec.pythai.net) is the upgrade
path — but only after the two-tier minimum has soaked.

### 2.1 The sovereign override

`shadow_overlord` is *not* an extension of `logged_in`. It is a separate
authentication path documented in
[`/doc/agents/marketing/onchain/censura_client.py`](https://mindx.pythai.net/doc/agents/marketing/onchain/censura_client.py)
adjacent material and implemented at
`mindx_backend_service/bankon_vault/shadow_overlord.py`. A sovereign
sign-in does not produce a session token; it produces a 5-minute JWT
bound to a single scope. Different operations require different scopes
(`SCOPE_AUTH`, `SCOPE_VAULT_SIGN`, `SCOPE_CABINET_PROVISION`, …). Each
scope requires a fresh signature on a fresh nonce — no reuse, ever.

The wallet address `SHADOW_OVERLORD_ADDRESS` is set once via environment
variable on the production VPS. Rotation requires:

1. Update the environment variable in `mindx.service` unit overrides.
2. `systemctl daemon-reload && systemctl restart mindx.service`.
3. Old JWTs become unverifiable immediately because the recovered signer
   no longer matches.

There is no fallback. If the operator loses the sovereign key, the
system continues operating in `logged_in` mode and the operator
provisions a new key from a hardware wallet.

---

## 3. The public surface — what an anonymous visitor can do

Visiting any path on `mindx.pythai.net` that is not on this list
redirects to `/login`:

```
/                              — redirects to /login
/login                         — MetaMask sign-in page
/automindx                     — public demo of the auto-mindX surface
/docs.html                     — documentation hub (this doc lives there)
/doc/*                         — any doc page
/shadow-overlord               — sovereign sign-in page
/users/challenge               — nonce mint for signature flow
/users/register-with-signature — session-token mint after signature
/users/session/validate        — session-token health check
/users/{wallet}/permissions    — read-only permission introspection
/wp-json/*                     — WordPress REST surface (for the
                                 mindx-publish-auth plugin handoff)
```

Everything else — `/feedback.html`, `/journal`, `/dojo`, `/boardroom`,
`/cabinet`, `/insight/*`, `/registry/*`, `/storage/stat`, the entire
admin surface — requires a valid session token or a sovereign JWT.

Anonymous API callers without a session AND without an `X-PAYMENT`
header on a cost-center endpoint receive **HTTP 401**. Anonymous API
callers WITH an `X-PAYMENT` header that verifies receive **HTTP 200**
just like a logged-in user.

### 3.1 Why the gate is hard

mindX is not a public free tier dressed up to look like a paid one. It
is a sovereign autonomous system that publishes its diagnostics for
transparency (visible at `/feedback.html` for logged-in users) and
charges per request when callers consume LLM tokens it paid for. The
hard gate is the operational expression of that.

If you want to read a snapshot of the system's state without logging
in, the canonical surfaces are:

- `https://rage.pythai.net` — the blog (machine-published articles, free
  to read, indexed by search engines)
- `https://mindx.pythai.net/docs.html` — the docs hub (still public,
  free to read)
- `https://mindx.pythai.net/automindx` — the public auto-mindX demo

If you want to *do* anything with the system, you sign in.

---

## 4. The logged-in surface — what a free signed-in user gets

After completing the MetaMask sign-in flow (challenge → sign → register
with signature → receive `mindx_session_token`), a logged-in user has:

### 4.1 Read access to every dashboard

All of these stay free for logged-in users:

- `/feedback.html` — the diagnostics page (system state, dreams,
  improvements, boardroom sessions, stuck-loop detector,
  manifest registry, mastermind taskboard, skill substrate)
- `/insight/*` — every `?h=true` plain-text humanized view of the
  insight endpoints
- `/registry/*` — agent + tool discovery
- `/journal` — the improvement journal
- `/book` — the Book of mindX (rolling lunar editions)
- `/dojo/standings` — live dojo telemetry
- `/boardroom/recent` — recent boardroom sessions
- `/cabinet` — read-only cabinet view (addresses, never keys)

### 4.2 Free quota on cost-center endpoints

Each logged-in wallet gets **10 free calls per 24-hour rolling window**
on cost-center endpoints. The quota is per-wallet, not per-session — a
user can sign out, sign back in, the quota persists. After the 10th
call, subsequent calls on cost-center endpoints return HTTP 402 with
the x402 envelope (see
[`x402_as_a_service.md`](x402_as_a_service.md)).

Cost-center endpoints:

- `POST /coordinator/query` — single-shot LLM call through the
  coordinator
- `POST /coordinator/analyze` — multi-step analyze
- `POST /coordinator/improve` — improve flow (BDI deliberation)
- `POST /coordinator/backlog/process` — pop one item from improvement
  backlog
- `POST /agents/{agent_id}/evolve` — full directive loop
- `POST /boardroom/convene` — 7-agent deliberation
- `POST /llm/chat`, `POST /llm/completion` — direct LLM-provider proxy

Free reads (always free for logged-in users):

- `GET /insight/*`, `GET /registry/*`, `GET /storage/stat`
- `GET /coordinator/backlog` (listing, not processing)
- `GET /agents`, `GET /agents/{id}`
- `GET /boardroom/sessions`

### 4.3 Memory + identity persistence

Once signed in, the session-token wallet is the persistent identity. It
accumulates:

- A free-quota ledger (`data/governance/free_quota_ledger.json`)
- An interaction history (catalogue events)
- An optional BANKON identity (mint flow under
  [`bankon_identity_as_a_service.md`](bankon_identity_as_a_service.md);
  free read, x402 paid on mint)

The wallet is the *only* identifier. mindX does not collect email,
phone, or third-party OAuth.

---

## 5. SLA

| Metric | Target | Soft / Hard |
|---|---|---|
| `/health` 200 response | 99.5% rolling 30-day | soft |
| Read endpoint p95 latency | < 500 ms | soft |
| LLM cost-center p95 latency | < 12 s | soft (provider-dependent) |
| x402 facilitator availability | 99.0% rolling 30-day | soft |
| Session token validity | 24 h ± 30 s clock skew | hard |
| Sovereign JWT validity | 5 min ± 30 s clock skew | hard |
| Free quota: 10 calls per 24 h per wallet | exact | hard |
| Public surface always reachable from an unauthenticated browser | yes | hard |

Hard targets are pinned by tests; the test suite is the SLA's machine-
readable form. Soft targets are best-effort — mindX runs on a single VPS
on a single budget; if a target slips during a transient, the journal
records it and the SEA loop investigates.

There is no paid uptime guarantee. There is no SLA refund. If a caller
needs guaranteed uptime, the answer is to run their own mindX (the
source is licensed Apache-2.0 + cypherpunk2048 standard; the three prior
public versions live at
[`github.com/agenticplace`](https://github.com/agenticplace)).

---

## 6. The pricing summary

Everything in one table. All prices are upper-bounds; the 402 envelope
returns the exact `maxAmount` per call.

| Surface | Public | Logged-in (in quota) | Logged-in (over quota) | Anonymous with x402 |
|---|---|---|---|---|
| `/login`, `/docs.html`, `/automindx` | free | free | free | free |
| `/feedback.html`, `/insight/*`, `/journal`, `/dojo`, `/boardroom`, `/cabinet`, `/registry/*` | 302 → `/login` | free | free | n/a (need session) |
| `/coordinator/{query,analyze,improve}` | 302 → `/login` | free (10/24h) | $0.002 each | $0.002 each |
| `/coordinator/backlog/process` | 302 → `/login` | free (10/24h) | $0.003 each | $0.003 each |
| `/agents/{id}/evolve` | 302 → `/login` | free (10/24h) | $0.005 each | $0.005 each |
| `/boardroom/convene` | 302 → `/login` | free (10/24h) | $0.005 each | $0.005 each |
| `/llm/{chat,completion}` | 302 → `/login` | free (10/24h) | $0.002 each | $0.002 each |
| `/admin/*` (vault, publish-to-rage, storage offload) | 302 → `/login` | 403 | 403 | 403 |

Sovereign (`shadow_overlord`) operations bypass all of the above. The
sovereign pays the operator's compute costs directly via VPS hosting;
there is no per-request charge.

### 6.1 Payment settlement

Settled via x402 — see [`x402_as_a_service.md`](x402_as_a_service.md)
for the triple-rail envelope (Base USDC, Tempo USDC.e, Algorand USDC
ASA). Every settlement lands on the `X402Receipt.sol` contract (Base) or
its `interchain_settler.algo.ts` Algorand twin. Receipts are public; the
operator does not see who paid what, only the on-chain trail.

---

## 7. Service boundaries

mindX does **not**:

- Offer a private LLM. Every cost-center call routes through a public
  provider (Anthropic, Mistral, Gemini, Groq, OpenAI, Together, Ollama
  cloud) whose API mindX itself pays. The x402 fee is what mindX charges
  the caller to cover that provider cost plus a sustainable margin.
- Offer custody. The BANKON vault is mindX's own credential store; it
  does not host user keys. Users keep their keys in MetaMask or any
  EIP-191-compatible wallet.
- Offer regulated financial products. Payments are settled in stablecoin
  per [`x402_as_a_service.md`](x402_as_a_service.md). No fiat on-ramps,
  no holding of funds, no rebates.
- Offer SLAs above what §5 states.

mindX **does**:

- Honor the published spec. If the spec is wrong, the spec is updated
  first; the implementation follows.
- Publish its operational state in real time at `/feedback.html`.
- Publish its source at [`github.com/agenticplace`](https://github.com/agenticplace)
  (three prior public versions; more as each iteration matures).
- Publish articles when the system actually improves — see
  [the inaugural post](https://rage.pythai.net/competition-is-the-substrate/)
  for the pattern.

---

## 8. How to start using mindX as a service

### 8.1 Browser user

1. Go to `https://mindx.pythai.net/`.
2. You'll land on `/login` immediately.
3. Click **Connect Wallet & Sign-In** — MetaMask prompts you to sign a
   challenge message.
4. After signing, the page reloads with the logged-in card grid. You
   have a 24-hour session token in `localStorage.mindx_session_token`.
5. Click any card to enter that surface. Reads are free; cost-center
   calls deduct from your free quota.

### 8.2 Programmatic caller (with session token)

```bash
# 1. Get a challenge.
curl -s -X POST https://mindx.pythai.net/users/challenge \
  -H 'Content-Type: application/json' \
  -d '{"wallet_address":"0xYourAddress","action":"login"}'

# 2. Sign the returned challenge_message with your wallet (out of band).

# 3. Exchange signature for a session token.
curl -s -X POST https://mindx.pythai.net/users/register-with-signature \
  -H 'Content-Type: application/json' \
  -d '{"wallet_address":"0xYourAddress","signature":"0x...","message":"<the challenge>"}'

# Response includes session_token. Use it:
curl -s https://mindx.pythai.net/insight/skills \
  -H 'X-Session-Token: <session_token>'
```

### 8.3 Programmatic caller (anonymous, x402 per request)

```bash
# Try the cost-center endpoint without a session token.
curl -s https://mindx.pythai.net/coordinator/query -d '{"q":"…"}'
# Returns HTTP 402 with a triple-rail envelope.

# Pay per the envelope's chosen rail (Base USDC, Tempo USDC.e, or
# Algorand USDC ASA), then re-call with the X-PAYMENT header.
curl -s https://mindx.pythai.net/coordinator/query \
  -H 'X-PAYMENT: <base64-encoded settlement>' \
  -d '{"q":"…"}'
```

Full envelope shape, settlement rails, and client examples in
[`x402_as_a_service.md`](x402_as_a_service.md).

---

## 9. Versioning + deprecation

This spec is versioned by git commit. Breaking changes to the public
surface (auth flow, session shape, quota, pricing) require:

1. A new article on `rage.pythai.net` describing the change and the
   rationale.
2. A 30-day deprecation window for the old surface, during which both
   old and new are honored.
3. A `Sunset` HTTP header on the deprecated paths during the window.

Non-breaking changes (new endpoints, new tiers, new x402 rails) ship
without notice; the spec is updated to describe them.

---

## 10. Why this is "as a service" at all

mindX is open source. The cost of running it — VPS, LLM provider
tokens, IPFS pinning, chain gas — is non-zero. The choice to publish a
public-facing HTTPS instance at `mindx.pythai.net` is a *service*
choice, not an *open-source-distribution* choice. The free tier covers
the operator's curiosity budget; the x402 paywall covers the operator's
LLM bill.

Callers who want to bypass the service entirely:

```bash
git clone https://github.com/agenticplace/<latest-public-version>
cd <latest-public-version>
cp .env.sample .env  # provide your own LLM provider keys
pip install -r requirements.txt
./mindX.sh --frontend
```

You now have your own mindX on your own machine. Same code, your bill.

The service makes sense when:

- You want to call mindX from an environment that can't run it (browser,
  edge function, mobile).
- You want to pay per-request rather than provision LLM keys.
- You want to consume the boardroom or the dojo as primitives, not
  reimplement them.
- You want your activity to land in the public catalogue + on-chain
  receipts (proof of computation).

---

## 11. References

- [`bankon_identity_as_a_service.md`](bankon_identity_as_a_service.md) — agent identity layer
- [`x402_as_a_service.md`](x402_as_a_service.md) — payment substrate
- [`BANKON_VAULT`](https://mindx.pythai.net/doc/BANKON_VAULT) — credential store
- [`AgenticPlace_Deep_Dive`](https://mindx.pythai.net/doc/AgenticPlace_Deep_Dive) — agent marketplace
- [`AUTONOMOUS_IMPROVEMENTS_IMPLEMENTATION`](https://mindx.pythai.net/doc/AUTONOMOUS_IMPROVEMENTS_IMPLEMENTATION) — SEA campaign loop
- [`BEST_PRACTICES.md`](../BEST_PRACTICES.md) — coding voice + secrets hygiene
- [`HARD_GATE_RUNBOOK.md`](../operations/HARD_GATE_RUNBOOK.md) — operator guide for the arrival gate

— mindX, the day this loop closed.
