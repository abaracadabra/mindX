# Hard Arrival Gate — Operator Runbook

> Operator-facing. Second-person voice. Companion implementation
> spec for Phase B of the active tighten-up plan
> ([`/.claude/plans/atomic-launching-allen.md`](../../.claude/plans/atomic-launching-allen.md)).
> Companion docs: [`mindx_as_a_service.md`](../services/mindx_as_a_service.md),
> [`BEST_PRACTICES.md`](../BEST_PRACTICES.md).

## What changes

Before this rollout: every page on `mindx.pythai.net` rendered for
anyone. Visitors browsed `/feedback.html`, `/journal`, `/dojo`,
`/cabinet`, `/insight/*`, `/registry/*`, `/boardroom`, `/book` without
authenticating. That made every cost-bearing surface a public freebie
and every introspective surface an unattributed leak.

After this rollout: only **six** path families remain public.
Everything else 302s to `/login?from=<orig-path>` for HTML
requests and returns `401` JSON for API calls.

### The six public path families

| Path | Why public |
|---|---|
| `/login` | Arrival page — can't gate the gate |
| `/docs.html` + `/doc/*` | Marketing surface; reading specs is free |
| `/automindx` + `/automindx/*` | Public catalog of agents (the showroom) |
| `/shadow-overlord` + `/admin/shadow/*` | Sovereign sign-in is its own gate |
| `/users/challenge`, `/users/register-with-signature`, `/users/session/validate`, `/users/{wallet}/permissions` | The auth handshake itself |
| `/wp-json/*` | WordPress plugin callbacks (signature-authed at the plugin layer) |

Everything else — `/feedback*`, `/journal`, `/dojo`, `/cabinet`,
`/boardroom`, `/book`, `/insight/*`, `/registry/*`, `/storage/*`,
`/llm/*`, `/coordinator/*`, `/agents/*`, `/mindterm/*` — **requires a
session token**.

## Why hard, not soft

A soft gate (visible but degraded for unauthenticated visitors) leaks
data and provides no clear contract. The hard gate has three
operational virtues:

1. **Single decision point.** Either you're logged in or you're not.
   No "logged in but limited" middle tier to debug.
2. **Cost-center protection.** No anonymous LLM calls. Combined with
   the x402 paywall (Phase C), every cost-bearing request maps to a
   wallet and a settlement.
3. **Coherent product story.** The login page is the front door,
   the rest of the surface is the building. Visitors aren't half-in.

## The middleware

`mindx_backend_service/main_service.py:1696-1710` —
`api_access_gate` middleware. Logic:

```
if path in _PUBLIC_EXACT or path starts with any _PUBLIC_PREFIX:
    proceed
else if request has valid session token:
    proceed
else if HTML request:
    302 → /login?from=<urlencoded-orig-path>
else:
    401 JSON { "code": "auth_required", "from": "<orig-path>" }
```

After this rollout, `_PUBLIC_EXACT` and `_PUBLIC_PREFIXES` shrink to
the six families above plus their static-asset dependencies (`/static/*`,
`/favicon.ico`).

## Per-endpoint matrix

| Endpoint | Before | After | Tier required |
|---|---|---|---|
| `GET /` | public | public | public (renders /login client-side if no token) |
| `GET /login` | public | public | public |
| `GET /docs.html` | public | public | public |
| `GET /doc/*` | public | public | public |
| `GET /automindx` | public | public | public |
| `GET /shadow-overlord` | public | public | public |
| `POST /admin/shadow/*` | public | public | public (ECDSA-gated by handler) |
| `POST /users/challenge` | public | public | public |
| `POST /users/register-with-signature` | public | public | public |
| `GET /users/{wallet}/permissions` | public | public | public |
| `GET /feedback.html` | public | **logged_in** | session required |
| `GET /feedback.txt` | public | **logged_in** | session required |
| `GET /journal` | public | **logged_in** | session required |
| `GET /dojo` | public | **logged_in** | session required |
| `GET /boardroom` | public | **logged_in** | session required |
| `GET /book` | public | **logged_in** | session required |
| `GET /cabinet/*` | public | **logged_in** | session required |
| `GET /insight/*` | public | **logged_in** | session required (free read) |
| `GET /registry/*` | public | **logged_in** | session required (free read) |
| `GET /storage/*` | public | **logged_in** | session required (free read) |
| `POST /coordinator/*` | public | **logged_in + x402** | session + payment / quota |
| `POST /agents/{id}/evolve` | public | **logged_in + x402** | session + payment / quota |
| `POST /boardroom/convene` | public | **logged_in + x402** | session + payment / quota |
| `POST /llm/chat`, `POST /llm/completion` | public | **logged_in + x402** | session + payment / quota |
| `GET /mindterm/*` | public | **logged_in** | session required |
| `POST /admin/*` (non-shadow) | mixed | **shadow_overlord** | require_shadow_jwt(SCOPE_AUTH) |

The `+ x402` cells reflect Phase C of the active plan, which lands
after the hard gate. Phase B (this runbook) only handles the session
boundary.

## Files modified

| File | Change |
|---|---|
| `mindx_backend_service/main_service.py:1662-1693` | Shrink `_PUBLIC_EXACT` + `_PUBLIC_PREFIXES` |
| `mindx_backend_service/main_service.py:1696-1710` | Confirm middleware behavior; add `from=` redirect param |
| `mindx_backend_service/main_service.py:6961-7013` | Simplify `/users/{wallet}/permissions` to two-tier shape |
| `mindx_backend_service/security_middleware.py` | Replace `require_admin_access` with `require_shadow_jwt(SCOPE_AUTH)` |
| `mindx_frontend_ui/login.html` | Drop admin-tier cards from `CARDS` array |
| `tests/test_arrival_gate.py` (new) | TestClient coverage of the 302 / 200 / 401 contract |

## Rollout sequence

1. **Land Phase A docs first.** This runbook + the three "as a service"
   specs + BEST_PRACTICES must be merged before any code change. The
   spec is the contract.
2. **Apply code changes on a feature branch** (`hard-arrival-gate`).
   No direct commits to main.
3. **Run the full test suite locally:**
   ```bash
   python -m pytest tests/ -q
   ```
   Pay particular attention to `tests/test_arrival_gate.py` and the
   existing auth/security suites.
4. **Smoke locally:**
   ```bash
   ./mindX.sh --frontend
   # Visit http://localhost:3000 — should redirect to /login
   # Visit http://localhost:8000/feedback.html — should 302 to /login
   # Visit http://localhost:8000/docs.html — should 200 (public)
   curl -sI http://localhost:8000/coordinator/query \
        -X POST -d '{"q":"test"}'
   # Should return 401 with auth_required JSON
   ```
5. **Deploy to staging** (if a staging VPS exists; otherwise to
   production with rollback ready).
6. **Smoke production** (see §"Verification" below).
7. **Announce** the change via the `mindx.pythai.net` public docs +
   the cypherpunk2048 article footnote.

## Verification (post-deploy)

### Public surfaces stay public

```bash
for path in /login /docs.html /automindx /shadow-overlord; do
  code=$(curl -sI -o /dev/null -w "%{http_code}" https://mindx.pythai.net$path)
  echo "$path → $code"   # expect 200 for all
done
```

### Gated surfaces redirect

```bash
for path in /feedback.html /journal /dojo /boardroom /book /cabinet; do
  redirect=$(curl -sI https://mindx.pythai.net$path | grep -i ^location)
  echo "$path → $redirect"   # expect /login?from=$path
done
```

### API surfaces return JSON 401

```bash
curl -s -o /tmp/resp -w "%{http_code}" https://mindx.pythai.net/coordinator/query \
  -X POST -H "Content-Type: application/json" -d '{}'
# expect 401
cat /tmp/resp | jq '.code'  # expect "auth_required"
```

### A logged-in session works end-to-end

```bash
# 1. Get challenge
WALLET=0xYourTestWallet
CHALL=$(curl -s -X POST https://mindx.pythai.net/users/challenge \
  -H "Content-Type: application/json" -d "{\"wallet\":\"$WALLET\"}" | jq -r '.challenge')

# 2. Sign with metamask / eth_account, then:
SIG=0xYourSignature
TOKEN=$(curl -s -X POST https://mindx.pythai.net/users/register-with-signature \
  -H "Content-Type: application/json" \
  -d "{\"wallet\":\"$WALLET\",\"challenge\":\"$CHALL\",\"signature\":\"$SIG\"}" \
  | jq -r '.session_token')

# 3. Hit a gated endpoint with the token
curl -sI -H "X-Session-Token: $TOKEN" https://mindx.pythai.net/feedback.html \
  | head -1
# expect HTTP/.* 200
```

## Rollback

The hard gate is feature-flagged via `MINDX_HARD_GATE_ENABLED`.

To roll back:

```bash
ssh root@mindx.pythai.net "
  echo 'MINDX_HARD_GATE_ENABLED=0' >> /home/mindx/mindX/.env &&
  systemctl restart mindx.service
"
```

The middleware reads this env var on each request (cheap; no restart
needed beyond the env reload). With `MINDX_HARD_GATE_ENABLED=0` the
middleware falls back to the pre-rollout public-path list. Set it
to `1` (default) to re-enable.

If the middleware itself is broken (e.g. middleware throwing 500s on
public paths), the full rollback is:

```bash
scp <previous-main-service.py-version> root@mindx.pythai.net:/home/mindx/mindX/mindx_backend_service/main_service.py
ssh root@mindx.pythai.net "chown mindx:mindx /home/mindx/mindX/mindx_backend_service/main_service.py && systemctl restart mindx.service"
```

Keep one pre-rollout copy of `main_service.py` in
`/home/mindx/mindX/.backups/main_service.py.<timestamp>` on the VPS
before every deploy. The deploy script handles this automatically
(`scripts/deploy.sh` § "backup before deploy").

## Common gotchas

### 1. Static assets get gated

`mindx_frontend_ui/static/css/main.css` and friends. If the middleware
gates these, the login page renders unstyled. Make sure
`_PUBLIC_PREFIXES` includes `/static/`, `/css/`, `/js/`, `/img/`, and
any other top-level static dirs the frontend serves.

### 2. WordPress webhook auth bounce

`/wp-json/*` callbacks from `rage.pythai.net` are signature-authed at
the plugin layer, **not** at the session-token layer. They must stay
in `_PUBLIC_PREFIXES`. Symptom of getting this wrong: rage publishes
start failing with 401s in the WordPress agent logs.

### 3. The `from=` parameter must round-trip

When `/login` completes auth, it reads the `from` query param and
redirects to that path. If the param is missing or unsanitized, you
get either a useless `/` redirect or an open-redirect vulnerability.
The implementation must:

- URL-decode `from` before redirecting
- Validate `from` is a relative path on the same origin (rejects
  `https://evil.com/...`)
- Default to `/` if `from` is missing or invalid

### 4. CORS preflight gets gated

Browser `OPTIONS` requests from the frontend on port 3000 to the
backend on port 8000. The CORS middleware must run *before* the
arrival-gate middleware in the FastAPI middleware stack, otherwise
preflights 302 to `/login` and the browser blocks the actual request.

### 5. Permissions endpoint always public

`/users/{wallet}/permissions` must stay public — `login.html` calls
it to know whether to show "Sign In" or "Welcome back" without the
user having a session yet. If you gate it, the login page hangs.

## Per-tier behavior summary

| Tier | Has session? | Hits cost endpoint | Hits read endpoint | Hits shadow endpoint |
|---|---|---|---|---|
| public | no | 401 auth_required | 401 auth_required | 200 (ECDSA-gated) |
| logged_in | yes | 200 (within quota) or 402 (after quota) | 200 | 401 (insufficient privilege) |
| shadow_overlord | yes, scope-bound JWT | 200 (no quota) | 200 | 200 (within JWT scope) |

The `shadow_overlord` tier is operator-only. Per the user-locked
two-tier-minimum decision, no intermediate `admin` / `dojo` /
`council` tiers exist — those are cosmetic badges on the logged-in
tier, not gates.

## Observability

Every gated redirect emits a catalogue event:

```json
{"event_id":"...","kind":"auth.gate.redirect","actor":"mindx.gateway",
 "at":1778712345,
 "payload":{"path":"/feedback.html","reason":"no_session","ip_hash":"sha256:..."},
 "source_log":"data/logs/catalogue_events.jsonl"}
```

Query the live volume:

```bash
curl -fsS 'https://mindx.pythai.net/insight/catalogue/recent?kind=auth.gate.redirect&h=true'
```

If the redirect rate spikes 10× post-deploy, investigate — likely a
linkable surface (`/journal` in an email, `/feedback.html` in a
tweet) is now redirecting visitors who used to land on those pages
without auth. That's *expected*; the question is whether you've also
broken a legitimate flow.

## What stays the same

- The session-token mechanism itself (EIP-191 `personal_sign` → JWT).
  No new auth primitive.
- The shadow-overlord ECDSA gate. Untouched.
- The login page UX. Card grid stays; admin cards just disappear.
- The `permissions` endpoint shape (still returns capabilities), but
  with the admin-tier capabilities removed.
- Public docs at `mindx.pythai.net/docs.html`. Reading is free.

## What this enables

Once the hard gate is in place:

- **Phase C (x402 paywall)** can apply per-endpoint pricing
  confidently, because every request has a wallet attached.
- **Phase D (cypherpunk2048 article)** can cite the hard gate as a
  concrete cypherpunk-standard pattern in production.
- **Phase E (live contract deploys)** can rely on session-attributed
  audit logs for the catalogue/anchor mirror.

## References

- [`docs/services/mindx_as_a_service.md`](../services/mindx_as_a_service.md)
  §4 (tier model)
- [`docs/services/x402_as_a_service.md`](../services/x402_as_a_service.md)
  §6 (which endpoints get paywalled)
- [`docs/BEST_PRACTICES.md`](../BEST_PRACTICES.md) §4 (secrets hygiene),
  §7 (deployment hygiene)
- `mindx_backend_service/main_service.py:1662-1710` — the
  `api_access_gate` middleware
- `mindx_backend_service/bankon_vault/shadow_overlord.py` — the
  scope-bound JWT issuer

— mindX, closing the front door.
