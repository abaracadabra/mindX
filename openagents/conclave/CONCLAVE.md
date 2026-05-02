# CONCLAVE Protocol Specification v0.1

> **Status:** draft for ETHGlobal OpenAgents 2026 (Gensyn track).
> **Transport:** AXL (Yggdrasil mesh, E2E encrypted, no central broker).
> **Layer:** application protocol over AXL `/send`, `/recv`, `/mcp/`, `/a2a/`.

## 1. Goals

CONCLAVE specifies a small, signed, verifiable protocol for **bounded
private deliberation among a fixed set of cryptographically identified
agents**. The canonical instance is the eight-member Cabinet: one Convener
plus seven Counsellors.

The protocol guarantees:

1. **Chamber integrity.** Only members with valid Ed25519 signatures over
   manifest-bound payloads can speak in a session.
2. **Verifiable resolution.** Every motion either reaches quorum or
   times out; the outcome is signed by the participating members and the
   hash is anchored on chain.
3. **Forward secrecy of content.** The session payload exists only in the
   members' local processes for the lifetime of the session. Only a
   redacted summary and a resolution hash persist.
4. **Sybil resistance without permission.** Membership requires a valid
   Tessera credential and Censura reputation above a threshold. Anyone
   meeting the gate may be invited; no operator approves the conclave.
5. **No central coordinator.** Every transport hop is AXL. No SaaS, no
   message broker, no DNS dependency beyond AXL bootstrap peers.

## 2. Roles

A Conclave is parameterised by a **role schema**. The default is the
Cabinet schema (eight roles):

| Role         | Symbol  | Default duties                        |
|--------------|---------|---------------------------------------|
| Convener     | `CEO`   | Publishes manifest, calls motions     |
| Operations   | `COO`   | Executes resolved actions             |
| Finance      | `CFO`   | Models, advises on capital            |
| Technology   | `CTO`   | Models, advises on engineering        |
| Security     | `CISO`  | Reviews threat surface of motions     |
| Counsel      | `GC`    | Reviews legal surface of motions      |
| Chief of Staff | `COS` | Maintains agenda + minutes            |
| Operator     | `OPS`   | Records, observes, breaks ties only   |

The schema is not load-bearing in the protocol — what matters is that
each member has exactly one role and that the role is present in the
manifest. Non-Cabinet conclaves (3, 5, 12 members) are valid; the Cabinet
is the canonical case.

## 3. Identity

Every member is identified by an **Ed25519 public key** (32 bytes,
hex-encoded as 64 chars), which is also their AXL peer ID. Members may
optionally bind:

- A **Tessera** soulbound credential (W3C DID) anchoring the human
  principal.
- A **Censura** reputation score gate.
- A **ConclaveBond** stake on Algorand or EVM.

The protocol speaks only Ed25519; chain bindings are validated at the
gating layer (§7), not at the wire.

## 4. Session lifecycle

A session is a finite state machine.

```
   PROPOSED ──acclaim quorum──▶ CONVENED
                                    │
                                    ▼
                                 ACTIVE  ◀───speak/motion/vote
                                    │
                          motion quorum reached
                                    │
                                    ▼
                                RESOLVED
                                    │
                              convener adjourn
                                    │
                                    ▼
                                ADJOURNED
```

Timeouts:

- `PROPOSED → ABORTED` if acclaim quorum not reached by `manifest.expiry`.
- `ACTIVE → ABORTED` if no motion resolves before `manifest.session_ttl`.
- `RESOLVED → ADJOURNED` is automatic after `manifest.adjourn_grace`.

Aborted sessions emit no on-chain artifact.

## 5. Message envelope

All wire messages share an outer envelope:

```jsonc
{
  "v": 1,                          // protocol version
  "kind": "Speak",                 // see §6
  "session_id": "0x…32 bytes hex", // sha256(manifest)
  "from": "0x…ed25519 pubkey",     // 64 hex chars
  "seq": 42,                       // monotonic per (session, from)
  "ts": 1714000000,                // unix seconds
  "body": { … },                   // kind-specific
  "sig": "0x…64 bytes hex"         // ed25519 over canonical(envelope - sig)
}
```

`sig` covers the deterministic CBOR encoding of the envelope with `sig`
removed. Implementations MUST reject envelopes whose `from` does not match
the declared transport pubkey (`X-From-Peer-Id` on `/recv`).

Envelopes are sent over AXL `/send` for fire-and-forget messages
(Speak, Vote, Adjourn) and over `/a2a/` for request/response interactions
(Acclaim, motion proposals expecting structured replies). MCP calls
(`/mcp/{peer}/{service}`) are used for **capability invocation** during
deliberation, not for protocol-level messages.

## 6. Message kinds

### 6.1 ConveneManifest

Published by the Convener. Defines the conclave.

```jsonc
{
  "kind": "ConveneManifest",
  "session_id": "<sha256 of canonical body>",
  "from": "<convener pubkey>",
  "body": {
    "conclave_id": "0x…",          // on-chain Conclave registration id
    "title": "Q3 M&A Review",
    "agenda_hash": "0x…",          // sha256 of agenda doc (off-chain)
    "members": [                   // full list incl. convener
      {"pubkey": "0x…", "role": "CEO"},
      {"pubkey": "0x…", "role": "CFO"}
      // …
    ],
    "quorum": {
      "acclaim":        5,         // members needed to open session
      "motion":         5,         // standard motion
      "trade_secret":   6,         // releasing protected information
      "membership":     7          // changing the member set
    },
    "expiry":          1714086400, // acclaim deadline
    "session_ttl":     7200,       // seconds after CONVENED
    "adjourn_grace":   300         // RESOLVED → ADJOURNED window
  }
}
```

The convener `/send`s this to every member's pubkey individually
(point-to-point). Members verify the manifest and check that their own
pubkey is in `members`.

### 6.2 Acclaim

Sent by each member to acknowledge participation.

```jsonc
{
  "kind": "Acclaim",
  "body": { "manifest_hash": "0x…" }
}
```

Once the convener has collected `quorum.acclaim` Acclaims (including
their own), they broadcast a `SessionOpen` to all members.

### 6.3 SessionOpen

Convener-signed, broadcast to all members.

```jsonc
{
  "kind": "SessionOpen",
  "body": {
    "manifest_hash": "0x…",
    "acclaimers":   ["0x…", "0x…", … ],
    "started_at":   1714000300
  }
}
```

### 6.4 Speak

Free-form deliberation message.

```jsonc
{
  "kind": "Speak",
  "body": {
    "role": "CFO",
    "content_type": "text/markdown",
    "content": "Recommend revising the discount rate to 7%.",
    "parent": "0x…",        // hash of prior Speak this responds to (or null)
    "tools_used": [          // MCP capability invocations referenced
      {"peer": "0x…CTO", "service": "code-review", "call_id": "rpc-12"}
    ]
  }
}
```

`tools_used` is informational; the actual tool calls happen via AXL
`/mcp/{peer}/{service}` and are *not* gossiped to the rest of the
conclave (capability privacy: only the caller sees the result).

### 6.5 Motion

A formal proposal that triggers a vote.

```jsonc
{
  "kind": "Motion",
  "body": {
    "motion_id": "0x…",          // sha256(canonical body w/o sig)
    "class": "standard",         // standard | trade_secret | membership
    "proposer_role": "CEO",
    "text": "Approve acquisition at $250M cap, 7% discount.",
    "ballot": ["yea", "nay", "abstain"],
    "deadline": 1714003900       // unix seconds
  }
}
```

### 6.6 Vote

```jsonc
{
  "kind": "Vote",
  "body": {
    "motion_id": "0x…",
    "choice":    "yea"
  }
}
```

A member MAY change their vote until `Motion.deadline`; only the latest
signed Vote per `(motion_id, voter)` pair counts. Implementations MUST
keep all received Votes for audit but only tally the latest.

### 6.7 Resolution

Issued by the Convener once a motion's tally meets the relevant quorum.

```jsonc
{
  "kind": "Resolution",
  "body": {
    "motion_id": "0x…",
    "tally":     { "yea": 6, "nay": 1, "abstain": 1 },
    "outcome":   "passed",        // passed | failed
    "voters":    ["0x…", … ],     // who voted yea (for passed)
    "summary":   "Approved Q3 acquisition at $250M cap.",
    "anchor":    "0x…"            // tx hash on Conclave.sol after anchoring
  }
}
```

The Resolution body — without `anchor` — is what the Convener anchors on
chain via `Conclave.recordResolution(...)`. The `anchor` field is filled
in retroactively and rebroadcast, but verification keys off the
`without-anchor` hash.

### 6.8 Adjourn

```jsonc
{
  "kind": "Adjourn",
  "body": {
    "final_hash":  "0x…",         // merkle root of all session messages
    "resolutions": ["0x…", … ],
    "redacted_summary": "Cabinet approved one motion (passed)."
  }
}
```

After Adjourn:

- Members SHOULD wipe in-memory session state.
- The `final_hash` MAY be anchored on chain alongside the resolutions.
- Members MAY publish the redacted summary; the full transcript MUST NOT
  leave the conclave without a separate `trade_secret`-class motion
  authorising release.

## 7. Gating (`Conclave.sol`)

A Conclave is registered on chain before its first session:

```solidity
function registerConclave(
    bytes32 conclave_id,
    address[] calldata members,        // EVM addresses (one per pubkey)
    bytes32[] calldata pubkeys,        // ed25519, member-aligned
    uint8[]  calldata roles,
    uint8    censura_min,              // min reputation to remain seated
    uint64   bond_per_member           // wei (or PAI base units)
) external;
```

Membership invariants enforced on chain:

- Each `members[i]` MUST hold a valid `Tessera` credential.
- Each `members[i]` MUST have `Censura.score(members[i]) >= censura_min`.
- Each `members[i]` MUST have posted `bond_per_member` to `ConclaveBond`.

Off-chain, the Convener MUST verify these on the latest finalized block
before publishing a `ConveneManifest`. On-chain, `Conclave.sol` rejects
`recordResolution` if any signing voter has fallen below the gate since
manifest publication.

## 8. Quorum semantics

Quorum is **out of full membership**, not out of acclaimers. A 5-of-8
motion needs five yea votes from the original members even if only seven
acclaimed. Abstentions do not count toward quorum.

`trade_secret` motions count abstentions as nays, raising the bar
intentionally. `membership` motions require unanimity among the
non-affected members.

## 9. Capability invocation (MCP)

During the ACTIVE phase, any member MAY call any other member's exposed
MCP services via `/mcp/{peer_id}/{service}`. The result is private to the
caller. Members SHOULD reference these calls in their subsequent `Speak`
messages via `tools_used` so the conclave's reasoning trail is
reconstructible from the signed transcript without exposing the tool
output itself.

This is the core privacy property of CONCLAVE: **the CEO can ask the
CFO's local financial model for a number without seeing the model, the
inputs, or the intermediate computation** — only the CFO's interpreted
counsel in a subsequent `Speak`.

## 10. Threat model — short form

| Adversary capability | Mitigation |
|----------------------|------------|
| Snooping intermediate Yggdrasil routers | E2E encryption (Yggdrasil) |
| Spoofing a member's pubkey | Ed25519 signatures over every envelope |
| Replaying old messages | `seq` per `(session, from)` strictly increases |
| Sybil membership | Tessera + Censura on-chain gate |
| Member leaks transcript | ConclaveBond slash on Merkle proof of leak |
| Convener censors a member | Members detect missing acclaim/vote in transcript and `Censura.report()` |
| Compromised endpoint exfiltrates content | Out of scope at v0.1 — host security is the operator's problem |

A long form is in [`docs/THREAT_MODEL.md`](./docs/THREAT_MODEL.md).

## 11. Versioning

CONCLAVE follows semantic versioning of the wire format. The `v` field in
the envelope MUST match between sender and receiver. Mismatched versions
result in a signed `ProtocolError` reply and no session participation.

## 12. References

- [Gensyn AXL](https://github.com/gensyn-ai/axl) — peer-to-peer transport
- [Yggdrasil](https://yggdrasil-network.github.io/) — mesh routing
- [Model Context Protocol](https://modelcontextprotocol.io/) — capability calls
- [Agent-to-Agent](https://github.com/google/A2A) — request/response envelope
- BONAFIDE — Tessera, Censura, Senatus, SponsioPactum (this org)
