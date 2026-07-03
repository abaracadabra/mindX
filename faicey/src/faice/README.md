# Faice — the FACE of an AI service

Turns an agent's **seven facets** into a wireframe FACE, served over HTTP and gated by
**x402 payment rails** with **FACE as privilege** (reputation grants free access).

> `.model · .agent · .prompt · .persona · .skill · .attribute · .reputation`  →  a FACE

This folder is the service layer. The FACE *computation* and *rendering* live in the
canonical engine (`facerig/src/lib/faicey`, served as `static/vendor/faicey-engine.js`).

## Quickstart

```bash
# from the faicey/ root
npm run sync-engine            # copy the engine + vendored three from facerig
npm run serve                  # boots the server (FACE routes live immediately)
curl http://localhost:8080/api/faice          # self-describing service manifest
```

For local testing without a real facilitator, accept any settlement envelope:

```bash
FAICE_X402_TEST_MODE=1 npm run serve
```

## API (ingestion)

`GET /api/faice` returns a **self-describing JSON manifest** — the canonical ingestion
surface (facets, privilege rule, rails, endpoint list, known agents).

| Endpoint | Access | Returns |
|----------|--------|---------|
| `GET /api/faice` | free | service manifest + known agents |
| `GET /api/faice/:agent/quote` | free | privilege verdict + price (no gating) |
| `GET /api/faice/:agent` | **overlord / privilege / x402** | FACE descriptor JSON |
| `GET /faice/:agent` | **overlord / privilege / x402** | rendered wireframe FACE page (HTML) |
| `POST /api/faice/:agent/interact` | **overlord only** | drive the FACE (set expression / override facets) |

`:agent` is a mindX entity id (e.g. `guardian_agent_main`) or a `0x` address.

**Query overrides** (quotes/testing): `?reputation=<score>`, `?skill=<n>`, `?role=<role>`.

### The gate — FACE as privilege

For a gated endpoint the gate decides in this order:

0. **Overlord** — a signature-proven overlord-session token (see below) bypasses every gate.
   `access.path = "overlord"`. The overlord is the ultimate privilege.
1. **Privilege** — the requested agent's reputation rank ≥ `privilegeFloor` (default
   `expert`) or BONA FIDE → served free. `access.path = "privilege"`.
2. **x402 settlement** — a valid `X-PAYMENT` header (base64 JSON
   `{scheme:"exact", network, payload}`) verified via the facilitator (or test mode) →
   served. `access.path = "x402_settled"`.
3. Otherwise → **HTTP 402** with a triple-rail `paymentRequirements` envelope.

### Overlord — the ultimate privilege (bankon.eth)

The **overlord** of the mindx / agenticplace / bankon cryptosystem is **`bankon.eth`** — its
wallet public key holds the overlord role, **granted from signature**. An overlord bypasses
every FACE gate and is the only identity that may **interact** with a FACE.

Authentication mirrors mindX's overlord model
([`mindx_backend_service/overlord`](../../../mindx_backend_service/overlord)): sign the
`OVERLORD-LOGIN` challenge → receive an `overlord_token` (HS256 JWT, scope `overlord.session`),
then send it as `Authorization: Bearer <token>` (or `X-Overlord-Token`, or `?overlord=<token>`
on the FACE page). Faicey verifies the JWT **in-house** (`overlord.js`, Node crypto, no
`jsonwebtoken` dep) against the shared secret.

```bash
# bypass the gate as overlord:
curl -H "Authorization: Bearer $OVERLORD_TOKEN" http://localhost:8080/api/faice/guardian_agent_main

# interact — drive the FACE:
curl -X POST -H "Authorization: Bearer $OVERLORD_TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"setExpression","expression":"laugh","intensity":1}' \
  http://localhost:8080/api/faice/guardian_agent_main/interact

# override any facet (overlord forces the FACE):
curl -X POST -H "Authorization: Bearer $OVERLORD_TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"override","overrides":{"reputation":60000}}' \
  http://localhost:8080/api/faice/guardian_agent_main/interact
```

The rendered FACE page (`/faice/:agent`) includes an **overlord control panel**: paste a
token (or `?overlord=<token>`), then click expression buttons to drive the live FACE, or use
**login via MetaMask** (runs the real `/overlord/challenge` → `personal_sign` → `/overlord/verify`
flow against the backend when reachable).

**bankon.eth binding:** set `FAICE_OVERLORD_ADDRESS` to bankon.eth's resolved address. When set,
the `overlord` role is **bound** to that address — an authentic overlord token whose subject is
not bankon.eth is downgraded (not THE overlord). The ENS name is `FAICE_OVERLORD_ENS` (default
`bankon.eth`).

| Env var | Effect |
|---------|--------|
| `MINDX_OVERLORD_JWT_SECRET` / `SHADOW_JWT_SECRET` | shared HS256 secret (≥32 chars) — same as the backend |
| `FAICE_OVERLORD_ADDRESS` | bankon.eth's resolved address — binds the overlord role |
| `FAICE_OVERLORD_ENS` | overlord ENS name (default `bankon.eth`) |

**Interaction actions** (`POST …/interact`, overlord only):
- `setExpression` — `{expression, intensity}` drive the resting expression
- `override` — `{overrides:{reputation, skill, role}}` re-resolve facets and recompute the FACE
- `inspect` — return the current descriptor

```bash
# 402 (novice agent, no payment):
curl -i http://localhost:8080/api/faice/guardian_agent_main

# privilege (simulate reputation):
curl http://localhost:8080/api/faice/guardian_agent_main?reputation=9000

# pay (test mode):
XP=$(node -e "console.log(Buffer.from(JSON.stringify({scheme:'exact',network:'base',payload:{sig:'0x1'}})).toString('base64'))")
curl -H "X-PAYMENT: $XP" http://localhost:8080/api/faice/guardian_agent_main
```

The 402 envelope mirrors `docs/services/x402_as_a_service.md`. Rails + facilitator are read
from mindX's `data/config/x402_pricing.json` when present (single source of truth:
`base`, `tempo`, `algorand-mainnet`), with a bundled fallback so faicey runs standalone.

## Configuration

| Source | What |
|--------|------|
| `faice_pricing.json` (this folder) | FACE endpoint prices + `privilegeFloor` |
| `data/config/x402_pricing.json` (mindX) | rails + facilitator (inherited when present) |
| `data/identity/production_registry.json` (mindX) | agent → address + role |
| `data/governance/dojo_snapshot.json` (mindX) | agent reputation scores (→ privilege) |

| Env var | Effect |
|---------|--------|
| `MINDX_ROOT` | override the mindX data root (default: three dirs up) |
| `FAICE_X402_TEST_MODE=1` / `MINDX_X402_TEST_MODE=1` | accept any valid X-PAYMENT envelope |

## File map

```
service.js          attachFaice middleware + descriptor/index/quote + renderFacePage
facets.js           loadFacets(agentId, overrides) — resolve the 7 facets (fallback-tolerant)
x402.js             faiceX402Gate(endpoint) — 402 envelope, X-PAYMENT verify, privilege bypass
faice_pricing.json  FACE prices + privilege floor
```

Engine: `faceFromFacets()` from `static/vendor/faicey-engine.js`
(source: `facerig/src/lib/faicey/FaiceIdentity.ts`). Voice is a separate peer: [`voaice`](../../../voaice).
