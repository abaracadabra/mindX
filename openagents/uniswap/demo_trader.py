#!/usr/bin/env python3
"""
Uniswap V4 demo trader — agnostic BDI-style trading agent against Sepolia.

Composes three modules: `tools/uniswap_v4_tool.py` (V4 quote/swap),
`personas/trader.prompt` (the trading mandate), and any LLM handler from
`llm/llm_factory.py` (Mistral / 0G / Ollama / Gemini — whatever you have).

The agent runs a 30-minute (configurable) loop:

  perceive   → read pool state + agent balances via uniswap_v4_tool("info")
  deliberate → ask the LLM to evaluate candidate trades against the persona
               constraints (≤0.5% slippage, ≤$5 position, 30% USDC reserve)
  decide     → JSON action {action, token_in, token_out, amount_in, ...}
  execute    → uniswap_v4_tool("quote") + uniswap_v4_tool("swap")
  log        → append the full cycle to data/logs/uniswap_decisions.jsonl

Every decision row carries: ts, perceived_state, deliberation_text,
decision_json, executed (bool), tx_hash (if any), outcome.

Run:
  python openagents/uniswap/demo_trader.py                # 30 min default
  python openagents/uniswap/demo_trader.py --duration 5   # 5 minutes
  python openagents/uniswap/demo_trader.py --provider zerog --model zerog/gpt-oss-120b
  python openagents/uniswap/demo_trader.py --dry-run      # no swaps, just decisions
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from utils.logging_config import get_logger  # noqa: E402

logger = get_logger("openagents.uniswap.demo_trader")

LOG_PATH = ROOT / "data" / "logs" / "uniswap_decisions.jsonl"
PERSONA_PATH = ROOT / "personas" / "trader.prompt"


# ───── Helpers ────────────────────────────────────────────────────────── #

def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _append_row(row: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, separators=(",", ":")) + "\n")

def _load_persona() -> str:
    if not PERSONA_PATH.exists():
        return "You are a cautious Uniswap V4 trader. Be conservative."
    return PERSONA_PATH.read_text(encoding="utf-8")


# ───── Perception ─────────────────────────────────────────────────────── #

async def perceive(tool, trader_addr: Optional[str]) -> dict:
    """Read tool info + balances. Tolerant — partial reads return what they can."""
    info = await tool.execute("info")
    out: dict = {"info": info}
    if not trader_addr:
        return out
    addrs = info.get("addresses", {})
    for sym, addr_key in (("USDC", "usdc"), ("WETH", "weth")):
        addr = addrs.get(addr_key)
        if not addr:
            continue
        try:
            bal = await tool.execute("balance", {"token": addr, "account": trader_addr})
            out[f"{sym}_balance"] = bal
        except Exception as e:
            out[f"{sym}_balance"] = {"ok": False, "error": str(e)}
    return out


# ───── Deliberation ───────────────────────────────────────────────────── #

DELIB_PROMPT_TEMPLATE = """\
{persona}

CURRENT CYCLE STATE (JSON):
{state_json}

Your task this cycle: decide ONE action and reply ONLY with a JSON object,
no prose around it. Schema:

{{
  "action":      "quote" | "swap" | "hold",
  "token_in":    "<address>",                  # required if action != "hold"
  "token_out":   "<address>",                  # required if action != "hold"
  "amount_in":   "<decimal string in BASE units, e.g. 1000000 = 1 USDC>",
  "fee":         3000,                          # 0.30% tier default
  "tick_spacing": 60,
  "rationale":   "≤2 sentences",
  "confidence":  0.0..1.0
}}

Constraints (HARD — exceeding them invalidates your decision):
  - slippage ≤ 0.5%
  - amount_in (USD-equivalent) ≤ 5
  - if your USDC balance falls below 30% of the starting portfolio,
    you MUST choose action=hold

If perception is incomplete (no balances), prefer action=quote over swap.
Reply with the JSON object and nothing else.
"""


async def deliberate(handler, persona: str, perceived: dict, model: str) -> dict:
    """Ask the LLM to choose ONE action; parse the JSON it returns.

    Returns a dict with at least {action, rationale, confidence}. Falls back
    to {action:"hold", reason:"<error>"} if the LLM is unreachable or the
    response isn't parseable JSON.
    """
    if handler is None:
        return {"action": "hold", "rationale": "no llm handler configured", "confidence": 0.0}

    prompt = DELIB_PROMPT_TEMPLATE.format(
        persona=persona,
        state_json=json.dumps(perceived, indent=2, default=str),
    )
    try:
        raw = await handler.generate_text(
            prompt=prompt, model=model, max_tokens=400, temperature=0.3, json_mode=True,
        )
    except Exception as e:
        return {"action": "hold", "rationale": f"llm call failed: {e}", "confidence": 0.0}

    if not raw:
        return {"action": "hold", "rationale": "empty llm response", "confidence": 0.0}

    # Strip prose: take everything between the first { and the last }.
    txt = raw.strip()
    i = txt.find("{")
    j = txt.rfind("}")
    if i == -1 or j == -1 or j <= i:
        return {"action": "hold", "rationale": "no json in llm output",
                "confidence": 0.0, "_raw": raw[:200]}
    try:
        parsed = json.loads(txt[i:j + 1])
    except Exception as e:
        return {"action": "hold", "rationale": f"bad json: {e}",
                "confidence": 0.0, "_raw": raw[:200]}

    parsed.setdefault("action", "hold")
    parsed.setdefault("rationale", "")
    parsed.setdefault("confidence", 0.0)
    return parsed


# ───── Execution ──────────────────────────────────────────────────────── #

async def execute_action(tool, decision: dict, dry_run: bool) -> dict:
    """Run quote or swap based on the deliberation outcome."""
    action = decision.get("action", "hold").lower()
    if action == "hold":
        return {"executed": False, "result": {"action": "hold"}}

    payload = {
        "token_in":  decision.get("token_in"),
        "token_out": decision.get("token_out"),
    }
    if decision.get("amount_in") is not None:
        try:
            payload["amount_in"] = int(decision["amount_in"])
        except Exception:
            payload["amount_in"] = 0
    if decision.get("fee") is not None:
        payload["fee"] = int(decision["fee"])
    if decision.get("tick_spacing") is not None:
        payload["tick_spacing"] = int(decision["tick_spacing"])

    if action == "quote":
        return {"executed": True, "result": await tool.execute("quote", payload)}

    if action == "swap":
        if dry_run:
            return {
                "executed": False,
                "result": {"ok": True, "dry_run": True, "intent": payload, "note": "--dry-run flag set"},
            }
        # Two-step: get a fresh quote so we can compute min_out for slippage
        q = await tool.execute("quote", payload)
        if not q.get("ok"):
            return {"executed": False, "result": q}
        amount_out = int(q.get("amount_out", "0"))
        # 0.5% slippage cap from the persona
        min_out = (amount_out * 9950) // 10000
        payload["min_out"] = min_out
        payload["deadline"] = int(time.time()) + 300
        swap = await tool.execute("swap", payload)
        return {"executed": True, "result": swap, "quote": q}

    return {"executed": False, "result": {"ok": False, "error": f"unknown action: {action}"}}


# ───── Main loop ──────────────────────────────────────────────────────── #

async def trading_loop(args) -> dict:
    """Run perceive → deliberate → execute → log on a fixed cadence."""
    from tools.uniswap_v4_tool import UniswapV4Tool

    tool = UniswapV4Tool()
    info = tool._info()
    trader_addr = info.get("trader_address")  # may be None in dry-run

    # Lazy-load LLM handler so the script still runs without a configured provider.
    handler = None
    persona = _load_persona()
    if not args.no_llm:
        try:
            from llm.llm_factory import create_llm_handler
            handler = await create_llm_handler(provider_name=args.provider, model_name=args.model)
            logger.info(f"trader llm: {handler.__class__.__name__} model={args.model}")
        except Exception as e:
            logger.warning(f"LLM handler unavailable, deliberation will short-circuit: {e}")

    end_at = time.time() + args.duration * 60
    cycles = 0
    quote_count = 0
    swap_count  = 0
    hold_count  = 0
    err_count   = 0

    print("=" * 78)
    print(f" mindX Uniswap V4 demo trader · network={info.get('network')} · "
          f"trader={trader_addr or 'NOT-CONFIGURED'} · "
          f"duration={args.duration}m · dry_run={args.dry_run}")
    print(f" log → {LOG_PATH}")
    print("=" * 78)

    while time.time() < end_at:
        cycle_start = time.time()
        cycles += 1
        try:
            perceived = await perceive(tool, trader_addr)
            decision  = await deliberate(handler, persona, perceived, args.model)
            outcome   = await execute_action(tool, decision, dry_run=args.dry_run)

            row = {
                "ts":          _now_iso(),
                "cycle":       cycles,
                "trader":      trader_addr,
                "perceived":   perceived,
                "decision":    decision,
                "outcome":     outcome,
                "executed":    outcome.get("executed", False),
                "action":      decision.get("action", "hold"),
                "rationale":   decision.get("rationale", ""),
                "confidence":  decision.get("confidence", 0.0),
            }
            _append_row(row)

            act = decision.get("action", "hold")
            if   act == "quote": quote_count += 1
            elif act == "swap":  swap_count  += 1
            else:                hold_count  += 1

            print(f"[{_now_iso()}] cycle {cycles:>3}  action={act:<5}  "
                  f"executed={row['executed']!s:<5}  "
                  f"conf={float(row['confidence']):.2f}  "
                  f"{row['rationale'][:60]}")
        except Exception as e:
            err_count += 1
            logger.exception(f"cycle {cycles} crashed")
            _append_row({
                "ts": _now_iso(), "cycle": cycles, "error": str(e),
            })

        # Pace the loop. Ten 30-second cycles in 5 min if duration ≤ 5; else 60s.
        elapsed = time.time() - cycle_start
        sleep_for = max(0, (30.0 if args.duration <= 5 else 60.0) - elapsed)
        if time.time() + sleep_for > end_at:
            break
        await asyncio.sleep(sleep_for)

    if handler and hasattr(handler, "close"):
        await handler.close()

    summary = {
        "ok": True,
        "cycles": cycles,
        "quote_count": quote_count,
        "swap_count":  swap_count,
        "hold_count":  hold_count,
        "errors":      err_count,
        "duration_min": args.duration,
        "log": str(LOG_PATH),
    }
    print("\n" + "=" * 78)
    print(" SUMMARY")
    print("=" * 78)
    print(json.dumps(summary, indent=2))
    return summary


def main():
    ap = argparse.ArgumentParser(description="mindX Uniswap V4 demo trader")
    ap.add_argument("--duration", type=int, default=30, help="minutes to run (default 30)")
    ap.add_argument("--provider", default=os.environ.get("TRADER_PROVIDER", "zerog"),
                    help="LLM provider (zerog | mistral | gemini | ollama | …)")
    ap.add_argument("--model", default=os.environ.get("TRADER_MODEL", "zerog/gpt-oss-120b"),
                    help="model name (provider-prefixed)")
    ap.add_argument("--dry-run", action="store_true",
                    help="don't execute swaps, just record decisions + quotes")
    ap.add_argument("--no-llm", action="store_true",
                    help="skip the LLM step entirely (will hold every cycle)")
    args = ap.parse_args()
    return asyncio.run(trading_loop(args))


if __name__ == "__main__":
    main()
