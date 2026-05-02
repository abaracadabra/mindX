# CONCLAVE Evaluation Plan

Three end-to-end scenarios that exercise different parts of the protocol
surface. Each is a scripted demo runnable from the same 8-node local
bring-up; together they take ≈10 minutes to record and ≈3 minutes to
narrate for the submission video.

---

## Scenario 1 · M&A war room (canonical happy path)

**What it proves:** the full Convene → Acclaim → Speak → Motion → Vote →
Resolution → Adjourn loop, including `/mcp/` cross-member capability
invocation during deliberation.

**Setup:**
```bash
./examples/run_local_8node.sh                  # 8 AXL + 7 counsellors
python examples/ceo_node.py --title "Acquire Acme @ $250M" \
    --agenda demos/agenda-acme.md
```

**Script (≈90 s narration):**

| t (s) | Event                                          | Layer        |
|-------|------------------------------------------------|--------------|
| 0     | CEO publishes manifest to 7 counsellors        | `/send`      |
| 0–4   | All 7 acclaim; SessionOpen broadcast           | protocol     |
| 5     | CEO `Speak`: "agenda — Acme acquisition"       | `/send`      |
| 6     | CEO calls CFO's `cfo-counsel` MCP service      | `/mcp/`      |
| 7     | CFO model returns DCF range; result private    | MCP privacy  |
| 8     | CFO `Speak`: "recommend $245M cap, 7% disc."   | `/send`      |
| 9     | CTO `Speak` cites their `code-review` capability call to evaluate Acme's stack |
| 12    | CEO `Motion`: "Approve at $250M / 7%"          | protocol     |
| 13–18 | 6 yea, 1 abstain (OPS), 1 nay (CISO)           | `/send`      |
| 19    | Convener resolves: passed (6 ≥ 5)              | protocol     |
| 20    | `Conclave.recordResolution()` → tx hash        | on chain     |
| 22    | `Adjourn`; merkle root printed                 | protocol     |

**Assertions to display:**
- Resolution hash on chain matches local merkle root.
- CFO's DCF computation **does not appear** in the transcript — only
  the CFO's interpreted `Speak` does. (This is the privacy property.)
- CISO's nay is preserved in the signed transcript despite the
  outcome being "passed" — minority dissent is auditable.

---

## Scenario 2 · Trade-secret gate (quorum escalation)

**What it proves:** different motion classes have different quorums.

**Setup:**

```bash
# Same Cabinet, but propose a TRADE_SECRET-class motion
python examples/ceo_node.py --title "Release threat-intel to industry peer" \
    --motion-class trade_secret
```

**Script (≈45 s narration):**

| t (s) | Event                                               |
|-------|-----------------------------------------------------|
| 0     | CEO proposes `trade_secret` motion                  |
| 1     | 5 yea, 1 abstain, 2 nay — would pass for STANDARD   |
| 2     | Conclave evaluates: trade_secret class promotes abstain to nay → 5 yea, 3 nay |
| 3     | 5 < 6 (`quorum.trade_secret`) → **failed**          |
| 4     | No on-chain anchor; signed Resolution shows failure |

**Assertion:** `Conclave.resolutionOf(...)` is `bytes32(0)` because the
convener correctly does NOT anchor a failed motion. The protocol's
counter-coercion property: even a CEO who wants to leak cannot anchor
without quorum.

---

## Scenario 3 · Slash for leak (bond + reputation hit)

**What it proves:** end-to-end honor stake + on-chain slash + Censura
report when a member leaks.

**Setup:**

```bash
# Run scenario 1 to produce a Resolution.
# Then "leak" the transcript:
python demos/leak.py --session $SESSION_ID > /tmp/leaked-transcript.json

# CEO submits the leak proof:
python demos/slash.py --leaker $COO_ADDR --proof /tmp/leaked-transcript.json
```

**Script (≈30 s narration):**

| t (s) | Event                                              |
|-------|----------------------------------------------------|
| 0     | `Conclave.slashForLeak(...)` tx submitted          |
| 1     | `MemberSlashed` event (full bond burned)           |
| 1     | `MemberUnseated` event (reason=3 / slashed)        |
| 2     | `Censura.report()` slashes 50 reputation points    |
| 3     | `isMemberSeated(COO)` flips to false               |
| 4     | Subsequent conclaves require COO to re-bond AND    |
|       | re-earn Censura — a multi-week cost                |

**Assertion:** `bondCtr.bondOf(CONCLAVE_ID, COO) == 0` and
`isMemberSeated(...) == false`.

---

## Negative-path coverage (Foundry)

`forge test -vvv` exercises:

- `test_register_and_seated`
- `test_unseated_when_tessera_revoked`
- `test_unseated_when_censura_below_min`
- `test_record_resolution_with_quorum`
- `test_record_reverts_when_voter_unseated`
- `test_double_anchor_reverts`
- `test_only_convener_anchors`
- `test_slash_unseats_and_burns_bond`
- `test_register_rejects_length_mismatch`
- `test_register_rejects_duplicate`

All ten paths are deterministic and complete in ≈300 ms locally.

---

## Live demo data

The demo agenda for Scenario 1 is committed at
`demos/agenda-acme.md`. Its sha256 matches the `agenda_hash` field of
the `ConveneManifest` shown in the video.

---

## Judge quickstart

```bash
git clone <this repo> conclave && cd conclave
git clone https://github.com/gensyn-ai/axl.git && (cd axl && make build)
pip install -e .
cd contracts && forge test -vvv && cd ..
./examples/run_local_8node.sh   # leave running in terminal A
# in terminal B:
python examples/ceo_node.py --title "Q3 M&A Review"
```

Total wall-clock from clone to a resolved on-chain anchor: under ten
minutes on a fresh laptop.
