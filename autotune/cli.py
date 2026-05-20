"""``python -m autotune`` — run the AOT probe and write a plan, or inspect hardware.

    python -m autotune bench [--device 0] [--dry-run] [--out plan.json]
    python -m autotune detect

Plain ``argparse`` so the package has no CLI dependency. Apache-2.0.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from autotune.benchmark import run_autotune
from autotune.profile import detect_hardware


def _cmd_bench(args: argparse.Namespace) -> int:
    plan = run_autotune(device_index=args.device, dry_run=args.dry_run)
    blob = plan.model_dump_json(indent=2)
    if args.out:
        Path(args.out).write_text(blob)
        print(
            f"wrote {args.out} (dry_run={plan.dry_run}, vendor={plan.hardware.vendor}, "
            f"attention={plan.attention_backend}, gemm={plan.gemm_heuristic}, "
            f"collective={plan.collective_config})"
        )
    else:
        print(blob)
    return 0


def _cmd_detect(_args: argparse.Namespace) -> int:
    print(detect_hardware().model_dump_json(indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="autotune", description="Agnostic ahead-of-time tuner.")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("bench", help="run the AOT probe and emit an AutotunePlan")
    b.add_argument("--device", type=int, default=0, help="GPU/HIP device index")
    b.add_argument("--dry-run", action="store_true", help="skip GPU probes; emit reference plan")
    b.add_argument("--out", "-o", default=None, help="write the plan JSON to this path")
    b.set_defaults(func=_cmd_bench)

    d = sub.add_parser("detect", help="print the detected HardwareProfile")
    d.set_defaults(func=_cmd_detect)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
