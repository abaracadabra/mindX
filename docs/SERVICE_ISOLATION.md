# Service Isolation Plan — Boardroom, Dojo, War-Council

> Status: **Phase A complete (scaffold)** — 2026-05-25.
> Full plan: `/home/hacker/.claude/plans/boardroom-dojo-isolation.md`.

mindX no longer hosts the boardroom or dojo as in-process components.
They become standalone Node.js services with explicit transport tiers and
explicit trust tiers. mastermind.pythai.net runs its own peer service
(the war-council) on the same VPS in a separate filesystem with mutual-
distrust posture.

## The three services

| Service | Tree | Port | aisdk | Filesystem owner | Default room |
|---|---|---|---|---|---|
| boardroom-service | `openagents/boardroom-service/` | 8771 | yes | `mindx` user | CEO + 7 soldiers (from `agent_map.json`) |
| dojo-service      | `openagents/dojo-service/`      | 8772 | no  | `mindx` user | war-council reputation preset |
| warcouncil-service| `/home/mastermind/.../warcouncil-service/` | 8773 | yes | `mastermind` user | 16-seat war council (13 original + Sun Tzu + Musashi + DAIO) |

The first two ship from this repo. The third lives in
`/home/hacker/mastermind/warcouncil-service/` locally and deploys to
mastermind.pythai.net.

## Transport tiers (per service)

| Tier | Use case |
|---|---|
| HTTP | Stateless commands — create room, list rooms, fetch session, query reputation |
| SSE  | Read-only dashboard tails — `GET /rooms/{id}/observe`, `GET /standings/feed` |
| WSS  | Agent ↔ agent live interaction — vote streaming via aisdk, amendments, questions |

Apache front-ends each service with `upgrade=websocket` and
`flushpackets=on` so SSE and WSS pass through unbuffered. See each
service's `deploy/apache/*-svc.conf`.

## Trust tiers (shadow-overlord pattern)

| Tier | Identity | Authority |
|---|---|---|
| 0 observer | anonymous | read public rooms only |
| 1 invitee | signed invite token | accept invite |
| 2 person  | BONA FIDE balance ≥ threshold (or K-of-N vouched pre-mint) | create public rooms, vote in them |
| 3 seat    | listed in `room.seats[]` | vote in that room with weight + veto |
| 4 cabinet | listed in `service.cabinet[]` | manage rooms, issue invites |
| 5 sovereign | DAIO multisig + shadow-overlord ECDSA + JWT | cross-room sanction, emergency stop |

JWT carries `tier`, `scope` (room_id or service-name), `exp`. Every
endpoint declares `required_tier`. Tier upgrades during a session
(personhood granted while logged in, BONA FIDE balance shifts) are
pushed via a WS control frame — no full reconnect.

## Mutual-distrust posture: mindX ↔ war-council

Even though both services live on the same VPS:

- mindX's `data/governance/` and mastermind's `data/governance/` are
  **separate directories owned by separate users**. The war-council's
  cross_check.js explicitly refuses to boot if its data dir resolves
  under mindX's tree.
- All cross-service calls carry an **EIP-191 envelope**:
  `X-MindX-Signer`, `X-MindX-Nonce`, `X-MindX-Timestamp`, `X-MindX-Signature`.
- Each side maintains an **explicit allowlist** of the other's wallet
  addresses (`WARCOUNCIL_MINDX_ALLOWLIST` env on mastermind side; mirror
  on mindX side in Phase B).
- Replay protection (60s timestamp window + nonce cache) + per-wallet
  rate-limiting (30/min, burst 10) applied before any handler sees the
  request.
- Rejection audit log at `data/governance/{warcouncil_mindx,mindx_warcouncil}_rejected.jsonl`.
- 401 responses give no detail to hostile clients about *why* they failed.

## Augmented seats — war council

The war-council adds three seats beyond the 13 from `docs/BOARDROOM.md`:

- **Sun Tzu** — strategist archetype. Five Factors from *The Art of War*:
  Moral Law, Heaven, Earth, Commander, Method & Discipline. Lapidary
  voice. Specialty: *position* over rules. Asks "If we win this vote, do
  we win the war?"
- **Miyamoto Musashi** — tactician archetype. Five Rings from *Go Rin no
  Sho*: Earth (ground), Water (flow), Fire (engagement), Wind (rival
  schools), Void (the unsayable). Specialty: *the decisive cut*.
- **DAIO** — constitutional observer. Weight 0 by default. Cites the
  DAIO Constitution; issues cross-room sanctions when joint action is
  proposed. Becomes voting (weight 1.2, veto) only via dual-sanction
  (mastermind-sovereign + DAIO-multisig signatures).

Personas in `warcouncil-service/src/seats/personas/{sun_tzu,miyamoto_musashi,daio}.md`.

## Roadmap

| Phase | Status | Scope |
|---|---|---|
| A | ✅ shipped | Scaffold all three services |
| A2 | ✅ shipped | Scaffold war-council with Sun Tzu, Musashi, DAIO seats + mindX envelope verifier |
| B | pending | Shadow-overlord 6-tier wallet auth (each service) |
| C | pending | Room model + storage (private/public/invite); mindX-default + war-council-default rooms boot from registries |
| D | pending | Consensus engine in TypeScript + aisdk + WebSocket protocol (vote.delta, amendment.propose, question.ask, verdict.final) |
| E | pending | Thin proxy from `mindx_backend_service/main_service.py`; `agents/boardroom_client.py` + `agents/warcouncil_client.py` |
| F | pending | Dojo reputation + K-of-N personhood vouching + BonaFideOracle stub |
| G | pending | Public UI (create/join room, personhood declaration) in `openagents/dapp_kit/templates/boardroom-ui/` |
| H | pending | `MINDX_DAIO_SANCTIONING_ENABLED` cross-room sanction flow |

Effort: ~19 dev-days; ~3.5–4 weeks.
