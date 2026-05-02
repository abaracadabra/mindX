# SPINTRADE ↔ openagents BDI trader integration

## The two repos

```
agenticplace/openagents     ← BDI trader, perceive/deliberate/execute loop
agenticplace/spintrade      ← Local pair + tokens + foundry tests + trade test driver
```

Locally these are siblings:

```
~/mindX/
├── openagents/
│   └── uniswap/
│       └── demo_trader.py    ← perceive → LLM deliberate → execute
└── spintrade/
    ├── src/, test/, script/   ← Solidity (this repo)
    ├── anvil/start.sh         ← boots local execution venue
    ├── deployments/anvil.json ← addresses written here
    └── trade_tests/
        ├── spintrade_tool.py            ← real swap broadcaster
        └── run_bdi_against_spintrade.py ← driver that runs the BDI loop
```

## Where the BDI loop becomes real

In `openagents/uniswap/demo_trader.py` the call chain is:

```
trading_loop()
  → perceive()      reads pool state via tool.execute("info")
  → deliberate()    LLM call returning {action, token_in, amount_in}
  → execute_action() routes to tool.execute("quote") then tool.execute("swap")
```

When `tool` is `tools/uniswap_v4_tool.UniswapV4Tool`, the `swap` action
returns a dry-run JSON envelope without broadcasting (the V4 calldata
encoding for UniversalRouter is non-trivial without the official SDK).

When `tool` is `spintrade.trade_tests.spintrade_tool.SpinTradeTool`, the
`swap` action:
1. Approves the pair to spend the input token (idempotent via `allowance`)
2. Builds + signs + broadcasts `pair.swap(amountIn, tokenIn, minOut, to)`
3. Waits for receipt, parses the `Swap` event, returns `{tx_hash, gas_used,
   amount_out, block}`

Same action surface, real execution.

## Switching the BDI trader to SPINTRADE

There are two paths:

### A. Use the SPINTRADE driver directly (what we do today)

```bash
cd ~/mindX/spintrade
bash anvil/start.sh           # boot venue
python3 trade_tests/run_bdi_against_spintrade.py --cycles 5
```

This driver imports `spintrade_tool.SpinTradeTool` directly and runs a
self-contained BDI loop (with a deterministic naive policy in place of the
LLM call so the test is reproducible without an LLM dependency).

### B. Plug SpinTradeTool into the existing demo_trader (one-line config)

In `openagents/uniswap/demo_trader.py:214`:

```python
async def trading_loop(args):
    if os.environ.get("SPINTRADE_DEPLOYMENTS"):
        from spintrade.trade_tests.spintrade_tool import SpinTradeTool
        tool = SpinTradeTool.from_deployments_json(
            os.environ["SPINTRADE_DEPLOYMENTS"]
        )
    else:
        from tools.uniswap_v4_tool import UniswapV4Tool
        tool = UniswapV4Tool(...)
    ...
```

Then:

```bash
export SPINTRADE_DEPLOYMENTS=~/mindX/spintrade/deployments/anvil.json
python openagents/uniswap/demo_trader.py --cycles 4 --provider zerog
```

The BDI cycle is unchanged. Only the execution venue swaps from "Sepolia V4
quoter, dry-run swap" to "anvil SPINTRADE, real swap".

## Action contract (so other tools can replace SpinTradeTool)

Both tools implement the same async surface:

| Action | Input | Output |
|---|---|---|
| `info`  | `{}` | `{ok, pair, token0/1: {address, symbol, reserve}, spot_price_*}` |
| `balance` | `{address?}` | `{bankon, pythai, lp}` (uint256 strings) |
| `quote` | `{token_in, amount_in}` | `{amount_out, implied_rate}` |
| `swap`  | `{token_in, amount_in, min_out?, to?}` | `{tx_hash, gas_used, amount_out, block}` |

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
