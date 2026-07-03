#!/usr/bin/env python3
"""Imprint a persona/scene script onto a tiny actor with mindXtrain — with the
live training light (status file + streamed log) the dashboard reads.

Runs the persona-imprint loop: init the mindx_persona_imprint_local recipe →
point data.path at the script.jsonl → train (CPU) → imprint (recall before vs
after). Writes data/godel/ascend/training_status.json around it so the landing
page + feedback.html show the TRAINING light, chronos-18dp elapsed, and per-core
CPU while the scene imprints.

Usage:
  MINDX_ENABLE_MINDXTRAIN=1 python scripts/imprint_persona.py \
      --script data/godel/scenes/the_sovereign_workshop/script.jsonl \
      --label the_sovereign_workshop [--cpu-percent 35]
"""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import PROJECT_ROOT
from mindx.godel.mindxtrain import bridge as _bridge
from mindx.godel.mindxtrain import status as _status
from mindx.godel.mindxtrain.imprint import imprint_verdict_factory
from mindx.godel.mindxtrain import is_enabled

RECIPE = "mindx_persona_imprint_local"


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--script", required=True, help="path to the script.jsonl to imprint")
    ap.add_argument("--label", required=True, help="short name for the run/light")
    ap.add_argument("--cpu-percent", type=int, default=35)
    ap.add_argument("--cpu-nice", type=int, default=19)
    ap.add_argument("--n", type=int, default=5, help="imprint recall probes")
    ap.add_argument("--train-timeout", type=int, default=2 * 3600)
    args = ap.parse_args()

    if not is_enabled():
        print("dormant: set MINDX_ENABLE_MINDXTRAIN=1"); return
    cap = _bridge.discover()
    if not cap.cpu_train_active:
        print(f"mindXtrain not CPU-train-active (version {cap.version})"); return

    script = (PROJECT_ROOT / args.script) if not os.path.isabs(args.script) else Path(args.script)
    if not script.exists():
        print(f"script not found: {script}"); return
    work = PROJECT_ROOT / "data" / "godel" / "imprints" / args.label
    work.mkdir(parents=True, exist_ok=True)
    cfg = "run.yaml"
    train_log = work / "train.log"

    # 1. init the persona recipe + point it at the scene script
    init = _bridge.run_cli(["init", "-t", RECIPE, "-o", cfg], cap=cap, cwd=work, timeout=300)
    if not init.get("ok"):
        print(f"init failed: {init.get('stderr') or init.get('error')}"); return
    text = (work / cfg).read_text(encoding="utf-8")
    import re
    text = re.sub(r"(?m)^(\s*path:\s*).*$", rf"\1{script}", text, count=1)
    (work / cfg).write_text(text, encoding="utf-8")

    # 2. chronos start + status light on
    started = time.time()
    ch_started, ch_consensus, ch_conf = await _status.chronos_now()
    _status.write_status("running", recipe=f"{RECIPE}:{args.label}", generation=args.label,
                         started_ts=started, ended_ts=None, log_path=str(train_log),
                         stage="training", chronos_started=ch_started,
                         chronos_consensus=ch_consensus, chronos_confidence_ms=ch_conf,
                         driver_pid=os.getpid())
    print(f"[imprint] training {args.label} on {script.name} ...")

    # 3. train (streamed)
    train = _bridge.run_cli_streamed(
        ["train", cfg, "--out", "out/runs", "--cpu-percent", str(args.cpu_percent),
         "--cpu-nice", str(args.cpu_nice)],
        cap=cap, cwd=work, log_path=train_log, timeout=args.train_timeout)
    if not train.get("ok"):
        _status.write_status("failed", recipe=f"{RECIPE}:{args.label}", generation=args.label,
                             started_ts=started, ended_ts=time.time(), log_path=str(train_log),
                             stage="train_failed")
        print(f"[imprint] train failed: {(train.get('tail') or train.get('error') or '')[-300:]}")
        return

    # 4. imprint proof-of-recall
    _status.write_status("running", recipe=f"{RECIPE}:{args.label}", generation=args.label,
                         started_ts=started, ended_ts=None, log_path=str(train_log),
                         stage="imprint", chronos_started=ch_started,
                         chronos_consensus=ch_consensus, driver_pid=os.getpid())
    verdict = imprint_verdict_factory(cap, work, cfg, n_probes=args.n)
    v = await verdict(None)
    recall = {k: v.get(k) for k in ("recall_before", "recall_after", "delta", "imprinted") if v.get(k) is not None}
    state = "promoted" if v.get("accepted") else "rejected"
    _status.write_status(state, recipe=f"{RECIPE}:{args.label}", generation=args.label,
                         started_ts=started, ended_ts=time.time(), log_path=str(train_log),
                         stage="imprint", recall=recall)

    rec = {"ts": time.time(), "trigger": "operator_persona", "recipe": f"{RECIPE}:{args.label}",
           "label": args.label, "script": str(script), "stage": state,
           "accepted": v.get("accepted"), "recall": recall, "reason": v.get("reason")}
    log = PROJECT_ROOT / "data" / "logs" / "ascend_log.jsonl"
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")
    print(f"[imprint] DONE {args.label}: accepted={v.get('accepted')} recall={recall}")
    print(f"  {v.get('reason')}")


if __name__ == "__main__":
    asyncio.run(main())
