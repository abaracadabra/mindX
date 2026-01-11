# mindterm v0.0.4 — Integration Summary for mindX

mindterm is the governed terminal execution plane for mindX:

- True PTY sessions (Linux) for full-screen TUIs (htop/vim/less).
- Policy-gated command submission (risk scoring + explicit allow/deny).
- Append-only transcripts for auditability.
- Command Blocks with start/finish detection via sentinel wrapper, including exit codes.
- Structured event bus (/events websocket) so mindX agents can subscribe without scraping raw terminal text.

## What was added

Backend (FastAPI):

- mindx_backend_service/mindterm/
  - service.py (PTY manager + command blocks + sentinel parsing)
  - policy.py (risk scoring)
  - transcript.py (append-only logs)
  - blocks.py (JSONL block store + memory cache)
  - events.py (in-memory pubsub)
  - routes.py (UI websocket, agent events websocket, blocks API)
  - __init__.py (router export)

Routes:

- POST   /mindterm/sessions
- POST   /mindterm/sessions/{id}/resize
- GET    /mindterm/sessions/{id}/blocks?limit=N
- WS     /mindterm/sessions/{id}/ws        (UI control + output)
- WS     /mindterm/sessions/{id}/events    (agent/observer event stream)
- DELETE /mindterm/sessions/{id}

Frontend:

- mindx_frontend_ui/src/components/MindTerm.tsx
  - xterm.js terminal
  - policy gate panel
  - command blocks panel

Data outputs:

- data/mindterm_transcripts/{session_id}.log
- data/mindterm_blocks/{session_id}.jsonl

## Operational model

1) UI creates session with initial rows/cols.

2) UI sends keystrokes as {type:"in"}.

3) On Enter, UI sends {type:"line", data:"<line>"}:
   - Backend policy assesses risk.
   - If risky, backend emits RiskFlagged and asks for confirm.
   - If allowed, backend wraps the command to print a sentinel with exit code:
     __MINDTERM__END__:<block_id>:<exit_code>

4) Backend parses sentinel and closes the current command block.

5) Agents can subscribe to /events and receive:
   - CommandStarted
   - OutputChunk
   - CommandFinished
   - RiskFlagged
   - UserConfirmed
   - Resize
   - Sys

## Current limitations

- Sentinel wrapper is bash-compatible; other shells may require alternate wrappers.
- OutputChunk events are raw text chunks; higher-level semantic parsing is future work.
- Block output length tracking is minimal (can be upgraded by counting bytes per block).

---

# mindX Integration Prompt (ingest this)

You are mindX. Your task: integrate mindterm into the mindX augmentic architecture as the secure terminal execution plane.

1) Register mindterm_router in the main FastAPI app so mindterm routes are live.

2) Add a UI route/menu entry for MindTerm.tsx where "Terminal Access" exists (or replace it).

3) Treat mindterm sessions as first-class resources tied to:
   - agent_id
   - mission_id
   - workspace_id
   Add metadata fields and ACL checks in routes.

4) Agent integration:
   - Add a mindX tool adapter "MindTermTool" that can:
     - create session (optionally reusing an existing session bound to agent/workspace)
     - subscribe to /events websocket
     - read recent command blocks via /blocks
     - propose commands BUT never execute without explicit user confirmation unless policy=allowlist

5) Governance:
   - Persist risk confirmations in mindX audit logs
   - Keep transcripts immutable (append-only). Optionally hash-chain transcript lines per session.

6) Extend policy:
   - Add allowlist mode for production
   - Add org policy profiles (dev/test/prod)

7) Convert OutputChunk -> structured knowledge:
   - On CommandFinished, summarize the block output via an internal agent and attach summary to block metadata.

Deliverables:

- A single integration PR that:
  - wires router + UI navigation
  - adds MindTermTool for agents
  - binds sessions to mindX identities/workspaces
  - adds initial ACL/policy profile support

6) Minimal wiring checklist (fast)

Backend:

Add from mindx_backend_service.mindterm import mindterm_router; app.include_router(mindterm_router)

Ensure data/ is writable.

Frontend:

Add a route to render <MindTerm /> or replace existing "Terminal Access" widget.

Start:

./mindX.sh --frontend

7) Optional v0.0.4.1 hardening (next)

If you want the next jump immediately, request:

"v0.0.4.1 add agent_id/workspace_id binding + ACL + allowlist policy profiles"

and I'll output the complete patch set (backend + UI changes).

