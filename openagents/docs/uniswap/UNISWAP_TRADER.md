# Uniswap V4 Trader — Module Brief

A BDI-reasoning swap agent for Uniswap V4 on Sepolia. The agent reads opportunities from a Boardroom deliberation, applies persona constraints, executes a swap, and writes a full decision trace to disk.

## Surface

### Tool: `tools/uniswap_v4_tool.py`

Extends `BaseTool` with four actions:

| Action | Purpose |
|---|---|
| `info` | Reports tool capabilities, supported chains, default reserve floor. |
| `quote` | Returns a quote for a `(token_in, token_out, amount_in)` triple at a given pool. Includes price impact and gas estimate. |
| `swap` | Executes a swap with explicit slippage and deadline. Returns the on-chain receipt. |
| `balance` | Returns the trader's USDC, WETH, and ETH balances. |

### Persona: `personas/trader.prompt`

Hard constraints (the BDI cycle rejects any action that violates these):

- **Slippage budget**: ≤ 0.5% per swap.
- **Position size**: ≤ $5 USDC equivalent.
- **Reserve floor**: maintain ≥ 30% USDC of total portfolio after the swap.
- **Decision freshness**: opportunity belief must be ≤ 60 seconds old when the swap is executed.

### Demo: `openagents/uniswap/demo_trader.py`

326 lines. Steps:

1. Initialize trader identity (BANKON ENS subname optional but supported).
2. Pull the most recent Boardroom deliberation for "opportunity" beliefs.
3. Compute the proposed swap parameters from belief.
4. Run the BDI cycle: Belief snapshot → Desire ranking → Intention selection.
5. Call `quote` to verify price stays in tolerance after pool snapshot.
6. Call `swap` if the gate clears; otherwise log the rejection and exit.
7. Write the full reasoning chain to `data/logs/uniswap_decisions.jsonl`.

## Decision-trace schema

Every entry in `uniswap_decisions.jsonl` is one swap attempt:

```json
{
  "timestamp": "2026-04-30T19:00:00Z",
  "trader_id": "trader-mindx-2k.bankon.eth",
  "opportunity_belief": {
    "source": "boardroom-session-...",
    "pair": "USDC/WETH",
    "direction": "USDC->WETH",
    "rationale": "..."
  },
  "bdi": {
    "beliefs_snapshot": { "...": "..." },
    "desire_ranking": [
      { "desire": "execute-swap", "score": 0.78, "constraints_passed": true }
    ],
    "intention": { "action": "swap", "args": { "...": "..." } }
  },
  "quote": { "amount_out": "...", "price_impact": "...", "gas_estimate": "..." },
  "decision": "execute" /* or "reject", with reason */,
  "receipt": { "tx_hash": "0x...", "block_number": 1234567, "gas_used": 165432 }
}
```

A judge replaying the file can verify the on-chain receipt matches the agent's reasoning step by step.

## Public verification

The Sepolia transaction history of the trader address (loaded from vault) is the canonical proof. Receipts in `uniswap_decisions.jsonl` link directly to Etherscan via `tx_hash`.

## See also

- Track positioning + reproduction: [`README.md`](README.md)
- Required DX feedback: [`FEEDBACK.md`](FEEDBACK.md)
