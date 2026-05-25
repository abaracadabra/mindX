# @mindx/boardroom-service

Standalone consensus service for the mindX boardroom. Hosts CEO + 7-soldier
deliberation as a private room mindX owns, plus a public surface where any
wallet can create or join a room via signed invite. **aisdk** powers per-soldier
LLM routing; **WebSockets** carry agent-to-agent interaction; **SSE** carries
read-only dashboard feeds; **HTTP** carries stateless commands.

> mindX is just one client. War-council on mastermind.pythai.net is another.
> Both speak the same protocol. Neither trusts the other beyond what the
> protocol enforces.

## Layout

```
src/
├── server.ts          # Hono app, port 8771, /healthz, /version
├── config.ts          # Reads daio/agents/agent_map.json (seven soldiers + CEO)
├── log.ts             # JSONL append-only logging with 100MB rotation
├── auth/              # Phase B — shadow-overlord 6-tier JWT, EIP-191 challenge
├── rooms/             # Phase C — room model + storage (private/public)
├── consensus/         # Phase D — per-soldier vote engine + verdict aggregation
├── providers/         # Phase D — aisdk provider routing per soldier
├── ws/                # Phase D — WebSocket handler (/rooms/{id}/ws)
├── sse/               # Phase D — SSE handler (/rooms/{id}/observe)
└── storage/           # JSONL helpers for sessions, rooms

deploy/
├── systemd/boardroom-service.service   # systemd unit, hardened
└── apache/boardroom-svc.conf           # vhost fragment for upgrade=websocket

scripts/
└── cross_check.js     # ExecStartPre — verifies agent_map.json + vault
```

## Transport tiers

| Tier | Path | Use |
|---|---|---|
| HTTP | `/healthz`, `/version`, `/rooms`, `/auth/*`, `POST /rooms/{id}/convene` | Commands |
| SSE  | `GET /rooms/{id}/observe` | Read-only dashboard tail |
| WSS  | `/rooms/{id}/ws` | Agent ↔ agent live debate |

WS protocol: `vote.delta` (server→all from aisdk stream), `amendment.propose` and
`question.ask` (any tier-3+ client → server), `verdict.partial` and `verdict.final`
(server→all). HTTP fallback exists for non-WS clients.

## Auth tiers (shadow-overlord pattern)

| Tier | Identity | Authority |
|---|---|---|
| 0 observer | anonymous | read public rooms only |
| 1 invitee | signed invite token | accept invite |
| 2 person | BONA FIDE balance (or K-of-N vouched pre-mint) | create public rooms, vote there |
| 3 seat | listed in `room.seats[]` | vote in that room with weight + veto |
| 4 cabinet | listed in `service.cabinet[]` (mindX, war-council) | manage rooms, issue invites |
| 5 sovereign | DAIO multisig + shadow-overlord ECDSA + JWT | cross-room sanction, emergency stop |

mindX is enrolled tier-4 in this service via the BANKON vault key
`mindx.boardroom.client:pk`.

## Run locally

```bash
cd openagents/boardroom-service
npm install
npm run dev      # tsx watch — restarts on edit
# curl http://127.0.0.1:8771/healthz
```

## Deploy

```bash
npm run build
sudo cp deploy/systemd/boardroom-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now boardroom-service
sudo systemctl status boardroom-service
```

Apache fragment in `deploy/apache/boardroom-svc.conf` — include from the
mindx.pythai.net vhost.

## Phases

This service ships in five phases (A–E) matching the umbrella plan in
`/home/hacker/.claude/plans/boardroom-dojo-isolation.md`. Phase A is the
scaffold you're reading; subsequent phases drop into `src/auth/`,
`src/rooms/`, etc.
