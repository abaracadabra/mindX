# CONCLAVE — Submission for ETHGlobal OpenAgents 2026

**Track:** Gensyn ($5K AXL prize)
**Tagline:** *Peer-to-peer agent conclave for trade-secret-grade
executive coordination.*

## What it is

A small, signed protocol on top of Gensyn AXL that lets a fixed set of
cryptographically-identified `mindX` agents convene in private,
deliberate, and resolve — with no central server, no cloud account,
and no third-party message broker ever touching the payload.

The canonical instance is the **Cabinet pattern**: one Convener (CEO)
plus seven Counsellors (COO / CFO / CTO / CISO / GC / COS / OPS).

## Why it wins the AXL track

1. **Uses every AXL primitive.** `/send`, `/recv`, `/mcp/`, `/a2a/`,
   `/topology` — see `docs/ARCHITECTURE.md` for the layer map.
2. **A real B2B use case.** M&A war rooms, board exec sessions,
   incident response, threat-intel sharing between rival CISOs,
   family-office governance. None of those can use Slack.
3. **Cross-process from byte 1.** Every member is a separate AXL node
   with its own keypair — no in-process shortcuts. Eight processes on
   one host or eight hosts in eight cities, the protocol doesn't care.
4. **On-chain accountability without on-chain content.** Membership is
   gated by BONAFIDE Tessera + Censura + ConclaveBond. Resolutions are
   anchored on chain; deliberations never leave the mesh. The full
   slash path (Algorand PAI bond via x402 + parsec-wallet relayer)
   ships as `conclave/algorand.py` + `ConclaveBond.attestAlgorandBond`.
5. **The privacy property is novel.** During ACTIVE, members invoke
   each other's local MCP services for tool calls whose **results stay
   private to the caller** — the CEO can ask the CFO's local model
   for a number without seeing the model, the inputs, or the
   intermediate computation, only the CFO's interpreted counsel in the
   subsequent signed `Speak`.

## What runs

- 8-node local Cabinet on one workstation: `examples/run_local_8node.sh`
- 9 Python protocol unit tests, 0.3 s wall: `pytest tests/`
- 10 Foundry tests on the contract: `forge test -vvv`
- Live `Camera View` HTML dashboard polling `/topology`:
  `examples/camera_view.html`

## Three-minute video script

| t (s)   | Frame                                                    |
|---------|----------------------------------------------------------|
| 0–15    | Hook: "Where do you put a multi-agent board meeting that can't go through a SaaS?" Show Slack. Show Slack's privacy policy. Cut. |
| 15–35   | Reveal CONCLAVE: 8 terminals, one per Cabinet seat. `./run_local_8node.sh` boots the mesh. Camera View dashboard fills in 8 green dots. |
| 35–80   | Run `ceo_node.py --title "Acme acquisition"`. Watch the manifest fan out, acclaims come back, SessionOpen broadcast, motion proposed. CFO gets called via `/mcp/`; cut to terminal showing the response is local-only. |
| 80–110  | Vote phase: 6 yea, 1 abstain, 1 nay. Resolution anchored on chain — show the tx hash, click through to the explorer. |
| 110–145 | Slash demo: replay the leaked transcript, run `slash.py`, watch `MemberSlashed` event fire, COO's bond burnt, Censura score drop. |
| 145–170 | Close: BONAFIDE stack diagram, "this is the same trust primitive that runs DELTAVERSE." Repo URL and ETHGlobal handle on screen. |
| 170–180 | "Built for OpenAgents 2026. Try it: github.com/codephreak/conclave." |

## Judges' quickstart

```bash
git clone <this repo> conclave && cd conclave
git clone https://github.com/gensyn-ai/axl.git && (cd axl && make build)
pip install -e .
pytest tests/                      # 9 protocol tests
cd contracts && forge test -vvv    # 10 contract tests
cd ..
./examples/run_local_8node.sh      # leave running
# in another terminal:
python examples/ceo_node.py --title "Q3 M&A Review" --agenda demos/agenda-acme.md
# open examples/camera_view.html in a browser
```

Ten minutes from clone to a resolved on-chain anchor on a fresh laptop.

## What's intentionally out of scope at v0.1

- A zk leak proof — the convener is socially trusted to validate the
  proof bytes; v0.2 will use Noir or Risc0.
- N-of-M co-signing of on-chain anchors — convener can currently
  fabricate a passed Resolution if every named voter is seated.
  Mitigation today: the signed transcript is the audit, and any honest
  member can publicly counter-claim.
- Cover traffic / chaff against traffic analysis. The mesh hides
  contents; it doesn't hide that two peers are talking a lot.

These are flagged in `docs/THREAT_MODEL.md` rather than hidden.

## Repository

- Protocol spec: `CONCLAVE.md`
- Architecture: `docs/ARCHITECTURE.md`
- Threat model: `docs/THREAT_MODEL.md`
- Eval scenarios: `docs/EVALUATION.md`
- Python package: `conclave/`
- Solidity: `contracts/src/`, `contracts/test/`
- Examples: `examples/`

## Authors

Built by Professor Codephreak (PYTHAI / DELTAVERSE) for ETHGlobal
OpenAgents 2026. CONCLAVE is the eighth contract in a Latin-named
family that already includes Tessera, Censura, Senatus, Sponsio
Pactum, Genius, Tabularium, and Fides — the BONAFIDE constitutional
stack. CONCLAVE meets in the *curia*; its counsellors carry the same
*tessera* their other DAIO roles do.
