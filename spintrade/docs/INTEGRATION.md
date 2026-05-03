# SPINTRADE — Consumer integration guide

SPINTRADE is a standalone module. It does not import from, depend on, or
assume the existence of any consuming framework. This doc explains how a
*consumer* (mindX openagents is one example among many) can plug
SpinTradeTool into its own BDI loop.

## SPINTRADE itself

```
spintrade/
├── src/, test/, script/   ← Solidity (this repo)
├── anvil/start.sh         ← boots local execution venue
├── deployments/anvil.json ← addresses written here
└── trade_tests/
    ├── spintrade_tool.py            ← real swap broadcaster (zero framework deps)
    └── run_bdi_against_spintrade.py ← self-contained BDI driver, deterministic
                                        policy, runnable with no LLM
```

Everything above runs from `cd spintrade && …`. No sibling repos required.

## Action contract — adopt this verbatim

Any BDI trader integrates SPINTRADE by calling four async actions on the
tool object:

| Action | Input | Output |
|---|---|---|
| `info`  | `{}` | `{ok, pair, token0/1: {address, symbol, reserve}, spot_price_*}` |
| `balance` | `{address?}` | `{bankon, pythai, lp}` (uint256 strings) |
| `quote` | `{token_in, amount_in}` | `{amount_out, implied_rate}` |
| `swap`  | `{token_in, amount_in, min_out?, to?}` | `{tx_hash, gas_used, amount_out, block}` |

The standalone driver `trade_tests/run_bdi_against_spintrade.py` is the
canonical reference implementation — copy `naive_decision()` into your own
trader and replace it with an LLM-backed deliberate step.

## Plugging SpinTradeTool into an external trader

For a Python consumer, the integration is one import + one method call:

```python
import sys
sys.path.insert(0, "/path/to/spintrade/trade_tests")
from spintrade_tool import SpinTradeTool

tool = SpinTradeTool.from_deployments_json(
    "/path/to/spintrade/deployments/anvil.json",
    trader_pk="0x...",   # optional; required only for swap action
)

# In your perceive/deliberate/execute loop:
info  = await tool.execute("info")
quote = await tool.execute("quote", {"token_in": "BANKON", "amount_in": 50 * 10**18})
swap  = await tool.execute("swap",  {"token_in": "BANKON", "amount_in": 50 * 10**18, "min_out": 0})
```

mindX's openagents trader uses this exact pattern when invoked with
`--backend spintrade` (see `openagents/uniswap/demo_trader.py`). That
import is lazy — openagents doesn't load SPINTRADE unless the operator
explicitly selects it.

## Trade-test evidence

Each cycle is appended to `spintrade/trade_tests/results/<timestamp>.jsonl`:

```json
{
  "ts": "2026-05-02T21:38:18Z",
  "cycle": 1,
  "perceived": { "info": {...}, "balance": {...} },
  "decision": { "action": "swap", "token_in": "PYTHAI", "amount_in": 5e19,
                "rationale": "...", "confidence": 0.7 },
  "result": {
    "executed": true,
    "quote": { "amount_out": "12500469050828024594" },
    "swap":  { "tx_hash": "0x82a7…", "gas_used": 69874,
               "amount_out": "12467188703918842247", "block": 4 }
  }
}
```

This is durable evidence: the tx hashes resolve to anvil receipts; gas used
matches forge gas estimates; the price impact compounds correctly across
cycles (verified by `test_swap_preserves_k_after_fee` in the suite).

## Why not fork mainnet Uniswap?

`anvil --fork-url <mainnet>` would let the trader hit real Uniswap, but:
- Requires a paid mainnet RPC (eth_call is not free)
- Pool state isn't deterministic across runs (fork at different blocks → different reserves)
- BANKON / PYTHAI don't exist on mainnet, so we'd need a different pair
- Fees on the fork accrue to wherever, not us — no test of LP economics

SPINTRADE deploys deterministic state every time `start.sh` runs. The same
test sequence produces the same reserves, the same gas, the same tx hashes
modulo nonces. That's what makes it a useful test venue.
