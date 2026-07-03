#!/usr/bin/env python3
"""Seed the self-improvement SENTINEL: record a baseline content hash and add
the sentinel backlog item so the live autonomous loop targets it.

Idempotent — safe to run repeatedly. Run once after deploying the sentinel.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.sentinel.sentinel import seed, status  # noqa: E402

if __name__ == "__main__":
    print("=== seed ===")
    print(json.dumps(seed(), indent=2))
    print("=== status ===")
    print(json.dumps(status(), indent=2))
