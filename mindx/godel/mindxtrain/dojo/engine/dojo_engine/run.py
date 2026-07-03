"""Engine entry point: ``python -m dojo_engine.run --config job.json``.

Run modes:
  --config PATH   Execute the job described by the JSON file.
  --doctor        Print an environment capability report (JSON) and exit.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback

from . import events
from .env import doctor
from .tasks import get_trainer


def _run_job(config_path: str) -> int:
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            job = json.load(fh)
    except Exception as exc:
        events.error(f"Could not read job config {config_path!r}: {exc}")
        return 1

    try:
        trainer = get_trainer(job)
    except Exception as exc:
        events.error(str(exc))
        return 1

    try:
        trainer.run()
        return 0
    except KeyboardInterrupt:
        events.error("Interrupted")
        return 130
    except Exception as exc:
        events.error(f"{type(exc).__name__}: {exc}")
        # Full traceback goes to stderr for debugging in the log pane.
        traceback.print_exc(file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dojo_engine.run", description="The Dojo training engine")
    parser.add_argument("--config", help="Path to a job config JSON file")
    parser.add_argument("--doctor", action="store_true", help="Print environment report and exit")
    args = parser.parse_args(argv)

    if args.doctor:
        print(json.dumps(doctor()))
        return 0

    if not args.config:
        parser.error("one of --config or --doctor is required")

    return _run_job(args.config)


if __name__ == "__main__":
    raise SystemExit(main())
