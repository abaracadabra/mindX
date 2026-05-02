# Uniswap — $5,000

**Best Uniswap API Integration** — a single track. The submission qualifies on two fronts:

- **Working integration** — the V4 trader executes swaps on Sepolia with full BDI deliberation traces.
- **Required `FEEDBACK.md`** — track rules require documentation of DX friction and API gaps. See [`FEEDBACK.md`](FEEDBACK.md).

## Submission entry point

| Submission | Primary doc |
|---|---|
| mindX Uniswap V4 Trader (BDI-reasoning swap persona) | [`UNISWAP_TRADER.md`](UNISWAP_TRADER.md) |
| Required DX feedback | [`FEEDBACK.md`](FEEDBACK.md) |

## What ships

- `tools/uniswap_v4_tool.py` — `BaseTool` exposing `info` / `quote` / `swap` / `balance` actions.
- `openagents/uniswap/demo_trader.py` — 326 lines. Reads an opportunity from a Boardroom deliberation and executes the swap on Sepolia. Persona constraints: ≤0.5% slippage, ≤$5 position, 30% USDC reserve floor.
- `personas/trader.prompt` — the persona's mandate and hard constraints.
- `data/logs/uniswap_decisions.jsonl` — every decision, with the full BDI trace (Belief snapshot, Desire ranking, Intention selection, action result).

## Why this is "real execution" not just a wrapper

Most Uniswap-API demos call `quote`, log the answer, and stop. This trader:

1. Reads a real *opportunity belief* from a Boardroom session (multi-soldier deliberation with provider attestation).
2. Runs a BDI cycle that compares the opportunity against the persona's hard constraints (slippage budget, position size, reserve floor).
3. Calls `quote` to confirm the price stays within tolerance after pool snapshot.
4. Calls `swap` to settle on Sepolia.
5. Writes the full reasoning chain — beliefs, ranking, decision, receipt — to `uniswap_decisions.jsonl`.

The decision log is what makes the integration *agentic*: a judge can replay the agent's reasoning and verify it matches the on-chain receipt.

## How to verify

```bash
# 1. Set up the trader (requires SEPOLIA_RPC_URL and a funded private key in vault)
cd openagents/uniswap
python demo_trader.py --dry-run        # quote-only, no settlement
python demo_trader.py                   # full quote → swap on Sepolia

# 2. Inspect the decision log
tail -n1 data/logs/uniswap_decisions.jsonl | jq .

# 3. Read the persona constraints
cat personas/trader.prompt
```

## Files in this folder

- [`README.md`](README.md) — this file.
- [`UNISWAP_TRADER.md`](UNISWAP_TRADER.md) — module brief: tool surface, persona, decision-trace schema.
- [`FEEDBACK.md`](FEEDBACK.md) — **required by track**: DX friction + API gaps. Stub — fill in from integration logs.

## See also

- Tool: [`../../../tools/uniswap_v4_tool.py`](../../../tools/uniswap_v4_tool.py)
- Persona: [`../../../personas/trader.prompt`](../../../personas/trader.prompt)
- Demo: [`../../uniswap/demo_trader.py`](../../uniswap/demo_trader.py)
- Cross-cutting architecture: [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
