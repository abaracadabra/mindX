# CONCLAVE Architecture

## Layer stack

```
 ┌─────────────────────────────────────────────────────────────┐
 │  Layer 6 — Demo UI (Camera View)                            │
 │  HTML dashboard: live mesh, redacted transcript, votes,     │
 │  on-chain anchor links, bond status                         │
 └─────────────────────────────────────────────────────────────┘
                                ▲
 ┌─────────────────────────────────────────────────────────────┐
 │  Layer 5 — mindX cognition (per member)                     │
 │  Soul (role) | Mind (reasoning) | Hands (MCP capabilities)  │
 │  conclave/agent.py wires this into Conclave.on_speak/motion │
 └─────────────────────────────────────────────────────────────┘
                                ▲
 ┌─────────────────────────────────────────────────────────────┐
 │  Layer 4 — CONCLAVE protocol                                │
 │  Convene / Acclaim / Open / Speak / Motion / Vote /         │
 │  Resolve / Adjourn — signed envelopes, seq replay-prot.     │
 │  conclave/protocol.py + messages.py + session.py            │
 └─────────────────────────────────────────────────────────────┘
                                ▲
 ┌────────────────────────────┐ │ ┌────────────────────────────┐
 │  Layer 3a — chain gating   │ │ │  Layer 3b — capability inv │
 │  Conclave.sol  (anchor,    │ │ │  AXL /mcp/{peer}/{service} │
 │   slash) on top of:        │ │ │  used during ACTIVE for    │
 │  • Tessera (credential)    │ │ │  cross-member tool calls   │
 │  • Censura (reputation)    │ │ │  whose RESULTS are private │
 │  • ConclaveBond (stake)    │ │ │  to the caller             │
 │  • Algorand bridge (PAI)   │ │ └────────────────────────────┘
 └────────────────────────────┘ │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  Layer 2 — AXL transport                                    │
 │  /send /recv /mcp/ /a2a/ /topology over Yggdrasil mesh,     │
 │  E2E encrypted, no central broker, 127.0.0.1:9002 bridge    │
 └─────────────────────────────────────────────────────────────┘
                                ▲
 ┌─────────────────────────────────────────────────────────────┐
 │  Layer 1 — Yggdrasil + gVisor TCP                           │
 │  IPv6 200::/7 mesh, userspace stack, no TUN, no port-fwd    │
 └─────────────────────────────────────────────────────────────┘
```

## Component map

| Component                      | Process            | Language | Notes |
|--------------------------------|--------------------|----------|-------|
| AXL node                       | one per member     | Go       | from `gensyn-ai/axl`, unmodified |
| `conclave.protocol.Conclave`   | one per member     | Python   | dispatch loop |
| `conclave.agent.MindXAgent`    | one per member     | Python   | mindX cognitive layer |
| MCP services (per member)      | one per capability | Python   | exposed via AXL's MCP Router (port 9003) |
| `Conclave.sol`                 | on chain           | Solidity | gating + anchoring + slashing |
| `ConclaveBond.sol`             | on chain           | Solidity | EVM honor stake; bridge to Algorand |
| Camera View dashboard          | one per observer   | HTML     | reads `/topology` and signed transcript |

## Data flow — convene → resolve

```
CEO mindX           CEO Conclave   CEO AXL    member AXL    member Conclave   member mindX
────────────────────────────────────────────────────────────────────────────────────────
  convene() ─────────► build manifest, sign
                       ──── /send envelope (per member) ──►
                                                            ──── /recv ────►  acclaim()
                                                                              sign Acclaim
                                                            ◄── /send envelope ────
                       ◄── /recv ────
                       quorum reached
                       broadcast SessionOpen
                                                            ──► state = ACTIVE
  propose_motion() ───► sign Motion
                       broadcast Motion
                                                            ──► on_motion(env)  ──► mind.vote_on_motion()
                                                            sign Vote
                                                            broadcast Vote
                       collect votes
                       evaluate_motion() == "passed"
                       sign Resolution
                       broadcast Resolution
                       Conclave.recordResolution()  ──── on chain ────►
  adjourn() ──────────► sign Adjourn
                       broadcast Adjourn; wipe state         ──► wipe state
```

## Why this passes the Gensyn rubric

| Criterion | How CONCLAVE addresses it |
|-----------|--------------------------|
| Depth of AXL integration | Uses **all four** primitives — `/send` for protocol envelopes, `/recv` for inbound dispatch, `/mcp/` for cross-member capability invocation, `/a2a/` for structured A2A request/response on Acclaim, plus `/topology` for the dashboard |
| Quality of code | Typed dataclasses, deterministic CBOR canonical encoding, explicit state machine, Foundry tests for the contract |
| Clear documentation | This file + `CONCLAVE.md` (protocol spec) + `THREAT_MODEL.md` + `EVALUATION.md` |
| Working examples | 8-node local bring-up script + per-role agent + scripted demo (M&A review, incident response, board exec session) |
| Real utility | M&A war rooms, board sessions, incident response, threat-intel sharing — none of which can use Slack/Telegram/cloud platforms |
| Cross-node not in-process | All transport is via real AXL bridges; even on one host, every member is a separate AXL process with its own keypair and bridge port |
| No central broker | The convener is *coordination*, not *transport*. They publish and resolve, but every byte goes over Yggdrasil between two pubkeys |
