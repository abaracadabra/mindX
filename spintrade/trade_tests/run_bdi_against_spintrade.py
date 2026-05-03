"""Self-contained BDI driver — runs perceive→deliberate→execute against SPINTRADE.

Standalone integration test for the SPINTRADE pair: any BDI consumer (mindX
openagents, OpenClaw, NanoClaw, your stack) can replicate the pattern by
swapping the deterministic `naive_decision()` below for an LLM-backed
deliberate step. SPINTRADE itself has zero dependencies on any caller —
this script imports only `spintrade_tool` (sibling module) + standard lib.

Pre-reqs:
  1. `bash spintrade/anvil/start.sh` running (anvil + SPINTRADE deployed)
  2. spintrade/deployments/anvil.json present

Usage:
  python spintrade/trade_tests/run_bdi_against_spintrade.py --cycles 3
  python spintrade/trade_tests/run_bdi_against_spintrade.py --cycles 5 --dry-run

Output:
  - Each cycle's perceive/deliberate/execute output to stdout
  - Cycle log appended to spintrade/trade_tests/results/<timestamp>.jsonl
  - Final reserves + price-impact summary
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── path setup — purely sibling resolution, no cross-repo coupling ─
HERE = Path(__file__).resolve().parent
SPINTRADE_ROOT = HERE.parent

sys.path.insert(0, str(HERE))

from spintrade_tool import SpinTradeTool  # noqa: E402

DEPLOYMENTS = SPINTRADE_ROOT / "deployments" / "anvil.json"
RESULTS_DIR = SPINTRADE_ROOT / "trade_tests" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def naive_decision(perceived: dict, cycle: int) -> dict:
    """Tiny rule-based stand-in for the BDI deliberate step.

    A real BDI trader (mindX or any other framework) would call an LLM here.
    This deterministic policy lets the trade test run without a network/LLM
    dependency:
      - cycle 0: hold (warm-up, just observe)
      - even cycles: sell BANKON if BANKON balance > 0
      - odd cycles:  sell PYTHAI if PYTHAI balance > 0
    """
    if cycle == 0:
        return {"action": "hold", "rationale": "warm-up cycle, observing reserves",
                "confidence": 1.0}
    sell = "BANKON" if (cycle % 2 == 0) else "PYTHAI"
    return {
        "action": "swap",
        "token_in": sell,
        "amount_in": 50 * 10**18,
        "min_out_bps_below_quote": 50,
        "rationale": f"cycle {cycle}: alternating direction stress-test",
        "confidence": 0.7,
    }


async def execute(tool: SpinTradeTool, decision: dict, dry_run: bool) -> dict:
    if decision["action"] != "swap":
        return {"executed": False, "reason": decision["action"]}
    payload = {"token_in": decision["token_in"], "amount_in": decision["amount_in"]}
    quote = await tool.execute("quote", payload)
    if not quote.get("ok"):
        return {"executed": False, "reason": "quote failed", "quote": quote}

    quoted_out = int(quote["amount_out"])
    bps_below = decision.get("min_out_bps_below_quote", 50)
    payload["min_out"] = quoted_out * (10000 - bps_below) // 10000

    if dry_run:
        return {"executed": False, "reason": "dry_run", "quote": quote, "would_send": payload}

    swap = await tool.execute("swap", payload)
    return {"executed": swap.get("ok", False), "quote": quote, "swap": swap}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true", help="quote-only, no broadcast")
    ap.add_argument("--deployments", default=str(DEPLOYMENTS))
    ap.add_argument("--pk", default=os.environ.get("TRADER_PK"))
    args = ap.parse_args()

    if not Path(args.deployments).exists():
        print(f"✗ {args.deployments} missing — run bash spintrade/anvil/start.sh first", file=sys.stderr)
        sys.exit(1)

    tool = SpinTradeTool.from_deployments_json(args.deployments, trader_pk=args.pk)

    log_path = RESULTS_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.jsonl"
    print(f"→ logging to {log_path}")
    print(f"→ deployments: {args.deployments}\n")

    info0 = await tool.execute("info")
    print("INITIAL RESERVES:")
    print(json.dumps(info0, indent=2))
    print()

    for cycle in range(args.cycles):
        print(f"═══ CYCLE {cycle} ═══════════════════════════════════════")

        # PERCEIVE
        info = await tool.execute("info")
        bal = await tool.execute("balance")
        perceived = {"info": info, "balance": bal}
        print(f"perceived: t0_per_t1={info['spot_price_t0_per_t1']:.4f}  "
              f"trader BANKON={int(bal['bankon'])/1e18:.2f}  PYTHAI={int(bal['pythai'])/1e18:.2f}")

        # DELIBERATE
        decision = await naive_decision(perceived, cycle)
        print(f"decision:  {decision['action']}  ({decision['rationale']})")

        # EXECUTE
        result = await execute(tool, decision, args.dry_run)
        if result.get("executed"):
            sw = result.get("swap", {})
            print(f"executed:  tx={sw.get('tx_hash','')[:16]}…  "
                  f"out={int(sw.get('amount_out') or 0)/1e18:.4f}  "
                  f"gas={sw.get('gas_used')}")
        elif decision["action"] == "swap":
            print(f"skipped:   {result.get('reason')}")
        else:
            print(f"holding")

        # LOG
        row = {
            "ts": _now(), "cycle": cycle,
            "perceived": perceived, "decision": decision, "result": result,
        }
        with log_path.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        print()

    final = await tool.execute("info")
    print("FINAL RESERVES:")
    print(json.dumps(final, indent=2))

    p0 = info0["spot_price_t0_per_t1"]
    p1 = final["spot_price_t0_per_t1"]
    if p0 and p1:
        impact = (p1 - p0) / p0 * 100
        print(f"\nTotal price impact (token0/token1): {impact:+.4f}%")
    print(f"Cycles logged: {log_path}")


if __name__ == "__main__":
    asyncio.run(main())
