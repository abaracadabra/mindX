# Gensyn AXL — $5,000

**Best Application of Agent eXchange Layer (AXL)** — peer-to-peer agent communication or multi-agent simulations using AXL, with no centralized message brokers and observable communication across separate AXL nodes.

## Submission entry point

| Submission | Primary doc |
|---|---|
| **Conclave** — P2P signed-envelope mesh deliberation; Cabinet pattern (CEO + 7 Counsellors) over AXL | [`../../conclave/SUBMISSION.md`](../../conclave/SUBMISSION.md) |

> **Conclave is a self-contained submodule** with its own `pyproject.toml`, Solidity contracts, and docs tree. It is the most agnostic module in this roster — it imports nothing from mindX. The full documentation lives at [`openagents/conclave/`](../../conclave/) (one level up from this folder).

## Why Conclave clears the AXL bar

The track requires:

1. **AXL for inter-node communication, no central brokers** — Conclave message envelopes traverse AXL only; there is no message bus, queue, or relay. Each Counsellor binary speaks AXL natively.
2. **Communication across separate AXL nodes** — `examples/run_local_8node.sh` boots eight AXL nodes (one CEO + seven Counsellors) and runs a full deliberation across them. The integration tests assert on cross-node message ordering, not just same-process passing.
3. **Public GitHub + working examples** — repository is public; demos run locally with no external dependencies once AXL is installed.

## What ships

- 19 Python files in `conclave/conclave/` (crypto, roles, session FSM, AXL client, agent wrapper, protocol state machine, on-chain anchoring).
- 2 Solidity contracts in `conclave/contracts/src/`:
  - `Conclave.sol` (9485 bytes) — gating + anchoring + slashing; integrates BONAFIDE (Tessera, Senatus, Censura).
  - `ConclaveBond.sol` (4999 bytes) — x402 / Algorand honor-stake module; settles trade-secret bonds via Parsec rail.
- 19 Python protocol tests + 10 Foundry contract tests, all green.
- `mindx_boardroom_adapter.py` — the only mindX-facing file in the package, and it explicitly does *not* import mindX. It exposes a `route()` callback that any framework's boardroom analogue can drive.

## How to verify

```bash
cd openagents/conclave

# Python protocol tests
pytest tests/                              # 19 protocol tests

# Solidity contract tests
cd contracts && forge test                 # 10 contract tests

# Run an 8-node local mesh
cd ..
./examples/run_local_8node.sh              # boots CEO + 7 Counsellors over AXL

# Live mesh visualization (open in a browser while the mesh is running)
xdg-open examples/camera_view.html
```

## Live verification

By design, AXL has **no public endpoint** — communication is mesh-to-mesh between the 8 nodes. The 8-node demo above is the AXL evidence; the on-chain artifacts (`Conclave.sol` resolution anchor + `ConclaveBond.sol` slash path) are the audit trail. See [`../LIVE_EVIDENCE.md`](../LIVE_EVIDENCE.md) for the full per-track verification page.

## Boardroom adapter (the symmetry)

`integrations/mindx_boardroom_adapter.py` shows how Conclave is the **distributed** Boardroom: same deliberation contract, P2P over AXL, with on-chain bond + slash instead of a single-host vote tally. The adapter exposes `route()` as a callback any framework's boardroom analogue can drive — it does *not* import mindX. Read [`../boardroom/BOARDROOM.md`](../boardroom/BOARDROOM.md) for the centralized contract this mirrors.

## Files in this folder

- [`README.md`](README.md) — this file.
- [`AXL_CEO_SEVENSOLDIERS.md`](AXL_CEO_SEVENSOLDIERS.md) — Cabinet pattern (CEO + 7 Counsellors) mapped onto the AXL mesh.

## Conclave's own documentation tree

- [`../../conclave/README.md`](../../conclave/README.md) — package overview.
- [`../../conclave/CONCLAVE.md`](../../conclave/CONCLAVE.md) — full protocol spec v0.1 (session FSM, role schema, Ed25519 identity, message envelope, quorum rules).
- [`../../conclave/SUBMISSION.md`](../../conclave/SUBMISSION.md) — ETHGlobal submission packet.
- [`../../conclave/BUILD_STATUS.md`](../../conclave/BUILD_STATUS.md) — build & test status snapshot.
- [`../../conclave/docs/ARCHITECTURE.md`](../../conclave/docs/ARCHITECTURE.md) — layer-by-layer design.
- [`../../conclave/docs/THREAT_MODEL.md`](../../conclave/docs/THREAT_MODEL.md) — security model.
- [`../../conclave/docs/EVALUATION.md`](../../conclave/docs/EVALUATION.md) — performance evaluation.

## See also

- Cross-cutting architecture: [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
- Boardroom governance (the consumer Conclave was designed for): [`../boardroom/BOARDROOM.md`](../boardroom/BOARDROOM.md)
