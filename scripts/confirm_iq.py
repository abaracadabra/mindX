#!/usr/bin/env python3
"""Run mindXtrain's interview of the promoted mindX model and record the verdict.

  python scripts/confirm_iq.py               # full interview, mindXeval judging
  python scripts/confirm_iq.py --no-judge    # ask only (fast; no LLM judge)
  python scripts/confirm_iq.py --model mindx-gen16:latest

Every exchange is recorded to the public interaction feed as it happens, so the
interview is visible at mindx.pythai.net/mindx.html while it runs. The verdict
lands in data/godel/iq_confirmation.json and is served at
/insight/iq/confirmation.

This is inference on a 2-core box that also runs the autonomous loop — expect
minutes, not seconds, and prefer running it when the loop is idle.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mindx.godel.mindxtrain.converse import confirm_iq


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="ollama tag to interview (default: last promoted generation)")
    ap.add_argument("--no-judge", action="store_true", help="skip the mindXeval LLM judge")
    ap.add_argument("--judge-model", default=None,
                    help="override the mindXeval judge (default qwen3:1.7b is too weak to "
                         "grade reliably — it returned unparseable output on 5 of 6 probes "
                         "on 2026-08-10; gpt-oss:120b-cloud is validated in both directions)")
    ap.add_argument("--judge-provider", default=None, help="judge provider (default ollama)")
    args = ap.parse_args()

    # Set before importing anything that constructs a judge.
    import os
    if args.judge_model:
        os.environ["MINDX_EVAL_JUDGE_MODEL"] = args.judge_model
    if args.judge_provider:
        os.environ["MINDX_EVAL_JUDGE_PROVIDER"] = args.judge_provider

    v = await confirm_iq(args.model, judge=not args.no_judge)
    if not v.get("ok"):
        print("could not confirm:", v.get("error"), "-", v.get("hint", ""))
        return 1

    s, me, g = v["subject"], v["mindxeval"], v["godel"]
    print("=" * 72)
    print(f"subject          : {s['model']}  (generation {s['generation']})")
    print(f"gödel imprint Δ  : {g['imprint_delta']}")
    print(f"mindXeval        : {me['composite']}  (judge: {me.get('judge_model')})")
    print(f"answered/judged  : {v['answered']}/{v['probes']} answered, {v['judged']} judged")
    print(f"confirmed        : {v['confirmed']}")
    print(f"duration         : {v['duration_s']}s")
    print("=" * 72)
    for t in v["turns"]:
        score = "unjudged" if t.get("score") is None else f"{t['score']:.2f}"
        print(f"\n[{t['id']}] {score}  ({t['latency_ms']:.0f}ms)")
        print(f"  Q: {t['ask']}")
        print(f"  A: {(t['answer'] or '(no answer)')[:300]}")
        if t.get("reason"):
            print(f"  judge: {t['reason'][:180]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
