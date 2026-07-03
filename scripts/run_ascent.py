#!/usr/bin/env python3
"""Operator driver for a Schmidhüber ascent through the mindXtrain bridge.

Runs the proven recipe flow (init → train → imprint → serve) via
ascend_recipe, which writes the live training-status file (powering the
dashboard's TRAINING light + elapsed timer) and streams the train log.
Appends the result to data/logs/ascend_log.jsonl so /insight/godel/ascend
surfaces the finished generation.

Usage:
  MINDX_ENABLE_MINDXTRAIN=1 python scripts/run_ascent.py \
      --recipe mindx_fallback_qwen3_1_5b_cpu_real --generation 1 \
      [--cpu-percent 25] [--no-promote]
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import PROJECT_ROOT
from mindx.godel.mindxtrain.ascend import ascend_recipe
from mindx.godel.mindxtrain.settings import regimen, measure_efficiency

_R = regimen()


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recipe", default="mindx_fallback_qwen3_1_5b_cpu_real")
    ap.add_argument("--generation", type=int, default=1)
    # defaults come from the CPU training regimen in settings (33% / 24h)
    ap.add_argument("--cpu-percent", type=int, default=_R.get("cpu_percent", 33))
    ap.add_argument("--cpu-nice", type=int, default=19)
    ap.add_argument("--no-promote", action="store_true")
    ap.add_argument("--train-timeout", type=int, default=_R.get("wall_hours", 24) * 3600)
    args = ap.parse_args()

    work = PROJECT_ROOT / "data" / "godel" / "ascend" / f"gen{args.generation}"
    print(f"[ascent] recipe={args.recipe} generation={args.generation} work={work}")
    result = await ascend_recipe(
        work_dir=work,
        generation=args.generation,
        data_memory_dir=PROJECT_ROOT / "data" / "memory",
        recipe=args.recipe,
        cpu_percent=args.cpu_percent,
        cpu_nice=args.cpu_nice,
        use_imprint=True,
        promote=not args.no_promote,
        register_fallback=False,   # served but not auto-routed to production
        train_timeout=args.train_timeout,
    )
    rec = result.as_dict()
    rec["ts"] = time.time()
    rec["trigger"] = "operator"
    rec["recipe"] = args.recipe
    # measure impact (imprint delta) per unit cost on the single CPU+RAM profile
    delta = (result.recall or {}).get("delta")
    cost_cpu_seconds = round(result.wall_seconds * args.cpu_percent / 100.0, 1) or None
    rec["measurement"] = measure_efficiency(delta, cost_cpu_seconds)
    log = PROJECT_ROOT / "data" / "logs" / "ascend_log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")
    print(f"[ascent] DONE stage={result.stage} promoted={result.promoted} "
          f"model={result.ollama_model} recall={result.recall}")
    for n in result.notes:
        print("  -", n)


if __name__ == "__main__":
    asyncio.run(main())
