# Build status — CONCLAVE v0.1

Snapshot of the repo as it ships for ETHGlobal OpenAgents 2026.

## What is verified

| Subsystem            | State    | How to verify                                  |
|----------------------|----------|------------------------------------------------|
| Python protocol      | ✅ green | `pytest tests/` → 9 passed, ~0.4 s             |
| Python imports       | ✅ green | `python -c "from conclave import *"`           |
| Solidity (Conclave)  | ⚠ untested locally — needs `forge` | `cd contracts && forge test -vvv` |
| AXL client           | ✅ shape | `httpx` calls match AXL's documented `/topology`, `/send`, `/recv`, `/mcp/`, `/a2a/` endpoints |
| Algorand x402 helper | ✅ shape | `pai_stake_payload(...)` builds an x402-spec-shaped body |
| Camera View HTML     | ✅ static | open in browser; expects AXL bridges on 9002, 9012, … |

## What's a stub for v0.1 (flagged honestly in `docs/THREAT_MODEL.md`)

- The slash-leak proof is the raw transcript bytes. v0.2 wants a Noir
  or Risc0 zk proof of "this signed envelope was leaked outside the
  mesh by peer X" so the proof itself doesn't re-leak the content.
- The convener can technically anchor a Resolution that names every
  voter without their consent. Mitigation today: the signed transcript
  is the audit trail and any honest member can publicly counter-claim.
  v0.2 wants n-of-m co-signed anchors.
- `MindXMind` in `agent.py` is a thin façade over an HTTP call to
  `mindx.pythai.net/api`; the demo Cabinet uses `StaticMind` so the
  demo runs offline.
- Cover traffic / chaff. The mesh hides contents but not the fact
  that two peers are talking a lot.

## What was added since the build was paused

- `examples/ceo_node.py` now accepts `--motion-class {standard,
  trade_secret, membership}` so Scenario 2 in `docs/EVALUATION.md`
  runs from the same script.
- `demos/leak.py` — simulates a transcript leak to feed `slash.py`.
- `demos/slash.py` — submits `Conclave.slashForLeak(...)` over web3
  and prints the receipt. Uses the same ABI bundled in
  `conclave/chain.py`.
- This file.

## Reproduction order for a judge

```bash
git clone <this repo> conclave && cd conclave
pip install -e .
pytest tests/                                  # protocol — must be green
git clone https://github.com/gensyn-ai/axl.git
(cd axl && make build)
cd contracts && forge test -vvv && cd ..       # contracts — must be green
./examples/run_local_8node.sh                  # leave running
python examples/ceo_node.py --title "Acme" --agenda demos/agenda-acme.md
# in a second shell:
python -m http.server -d examples 8081 &
xdg-open http://localhost:8081/camera_view.html
```

Total wall time on a fresh laptop: under ten minutes.
