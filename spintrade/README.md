# SPINTRADE

A standalone, framework-agnostic local Uniswap V2-style constant product
market maker (CPMM) with two test tokens — **BANKON** and **PYTHAI**.

SPINTRADE is its own module. It deploys a complete swap venue on anvil
(chain 31337) and exposes a Python tool with the canonical action surface
(`info` / `balance` / `quote` / `swap`). Any BDI consumer — mindX
openagents, OpenClaw, NanoClaw, your stack — can plug in by reading
`deployments/anvil.json` and importing `trade_tests/spintrade_tool.py`.

There is **no dependency on any specific framework** in either direction:
the contracts, the Foundry tests, the Python tool, and the BDI driver all
run from `cd spintrade && …` with nothing else checked out.

## What's in this repo

```
src/
├── tokens/
│   ├── BankonToken.sol      ERC20 with owner-mint, 1M initial supply
│   └── PythaiToken.sol      ERC20 with owner-mint, 1M initial supply
├── interfaces/
│   └── ISpinTradePair.sol   Read + write surface (events + custom errors)
├── SpinTradePair.sol        x*y=k AMM with 0.30% fee, LP shares as ERC20
└── SpinTradeFactory.sol     Idempotent createPair, canonical token0<token1

test/
└── SpinTrade.t.sol          18 unit tests — all passing
                             (factory, liquidity, quote, swap, slippage, k-invariant)

script/
└── DeploySpinTrade.s.sol    Deploys + seeds 100k BANKON / 400k PYTHAI

anvil/
├── start.sh                 boot anvil + deploy + write deployments/anvil.json
└── stop.sh                  kill the anvil process

trade_tests/
├── spintrade_tool.py        Python wrapper — info / balance / quote / swap
├── run_bdi_against_spintrade.py   driver: BDI cycles vs. live SPINTRADE
└── results/<timestamp>.jsonl     per-cycle perceive / decide / execute log
```

## Quick start

Requires: `forge`, `anvil`, `cast`, `jq`, `python3` with `web3`+`eth_account`.

```bash
cd spintrade

# 0. First-time setup — install Foundry deps (lib/ is gitignored)
forge install foundry-rs/forge-std --no-commit --no-git
forge install OpenZeppelin/openzeppelin-contracts --no-commit --no-git

# 1. Run unit tests
forge test
# → 18 passed; 0 failed

# 2. Boot anvil + deploy + seed liquidity
bash anvil/start.sh
# → writes deployments/anvil.json with addresses

# 3. Drive the BDI trader against the live pair
python3 trade_tests/run_bdi_against_spintrade.py --cycles 4
# → 4 perceive→deliberate→execute cycles
# → real swaps; tx hashes, gas, amount_out all real
# → cycle log at trade_tests/results/<timestamp>.jsonl

# 4. Stop anvil when done
bash anvil/stop.sh
```

## Why this exists

A reusable execution venue that any BDI trader can use as its "real but
deterministic" target — useful for unit tests, CI runs, repeatable demos,
or as a stand-in when an external API path is gated, rate-limited, or down.

SPINTRADE gives any consumer a **real swap target with no external
dependencies**:
- One Foundry command boots a chain
- One bash command deploys the pair + seeds liquidity
- The standard `info`/`balance`/`quote`/`swap` actions broadcast against
  this pair, with real gas, real receipts, real reserve movement
- `trade_tests/results/*.jsonl` is durable evidence per cycle

For mindX, this is one of three execution venues the openagents Uniswap
trader can target via `--backend`. The other two — `v4-stub` (Sepolia
quoter, dry-run swap) and `trade-api` (the real Uniswap Trading API) — are
defined inside openagents/. SPINTRADE doesn't know about any of them.

## How openagents uses it

The BDI trader at `openagents/uniswap/demo_trader.py` is unchanged. It now
points at `spintrade/trade_tests/spintrade_tool.py` instead of the V4 stub
when the `--spintrade` flag (or `SPINTRADE_DEPLOYMENTS` env var) is set.

See `docs/INTEGRATION.md` for the full BDI ↔ SPINTRADE wiring.

## Test results

Sample evidence from `trade_tests/results/`:

```
CYCLE 0: hold  (warm-up)
CYCLE 1: swap PYTHAI → BANKON  out=12.4672 BANKON   gas=69874
CYCLE 2: swap BANKON → PYTHAI  out=199.2510 PYTHAI  gas=69819
CYCLE 3: swap PYTHAI → BANKON  out=12.4765 BANKON   gas=69874

Initial price: 1 BANKON = 4.0000 PYTHAI
Final price:   1 BANKON = 3.9980 PYTHAI
Total impact: +0.0499% (matches expected 0.3% fee × 3 swaps)
```

K-invariant test (`test_swap_preserves_k_after_fee`) confirms the AMM
mathematics: post-swap `k = reserveIn * reserveOut` strictly increases
because the 0.3% fee stays in the pool.

## Math reference

Standard Uniswap V2 swap formula:

```
amountOut = (reserveOut × amountIn × 997)
          / (reserveIn × 1000 + amountIn × 997)
```

LP minting on first deposit:

```
lp = sqrt(amount0 × amount1) - MINIMUM_LIQUIDITY  (1000 dust burned)
```

LP minting on subsequent deposits:

```
lp = min(amount0 × totalSupply / reserve0,
        amount1 × totalSupply / reserve1)
```

## Deployment notes

- **Local only.** SPINTRADE is for testing. The pair contract has no admin,
  so it's safe to leave running, but the tokens are owner-mintable. Don't
  deploy these tokens to a chain anyone else uses.
- **Anvil chain id 31337.** Default `--rpc-url http://127.0.0.1:8545`.
- **Default deployer.** Anvil account #0 (`0xf39F…2266`) holds 1M of each
  token plus the LP shares.
- **Initial price.** 1 BANKON = 4 PYTHAI. Change in
  `script/DeploySpinTrade.s.sol` if you want a different starting curve.

## License

GPL-3.0 — © BANKON · cypherpunk2048 standard
