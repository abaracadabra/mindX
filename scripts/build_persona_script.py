#!/usr/bin/env python3
"""Build a mindXtrain persona-imprint script.jsonl from a mindX persona file.

mindXtrain's mental model: a model is an *actor*; an actor has a *persona*
(identity/voice) and a *script* (the training rows that leave the impression).
This turns a mindX persona JSON ({name, system_prompt, voice_examples,
exchanges}) into the OpenAI-chat JSONL that `data.source: local` ingests —
matching mindxtrain.data.scripts.build_script_rows exactly, so it runs without
importing mindXtrain (the personas are authored mindX-side, read clean-room).

Then imprint it:
  uv run --project ~/mindXtrain mindxtrain init -t mindx_persona_imprint_local -o run.yaml
  # set data.path to the script this writes
  uv run --project ~/mindXtrain mindxtrain train run.yaml --out out/runs --cpu-percent 25
  uv run --project ~/mindXtrain mindxtrain imprint run.yaml --out out/runs --n 5

Usage:
  python scripts/build_persona_script.py professor_codephreak \
      [--out out/datasets/professor_codephreak/script.jsonl]
  python scripts/build_persona_script.py --all
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
PERSONA_DIR = ROOT / "mindx" / "godel" / "mindxtrain" / "personas"


def system_prompt(p: dict) -> str:
    sp = (p.get("system_prompt") or "").strip()
    return sp or f"You are {p.get('name','actor')}. Stay in character and answer in your own voice."


def build_rows(p: dict) -> list:
    """Identical shape to mindxtrain.data.scripts.build_script_rows."""
    name = p.get("name", "actor")
    system = system_prompt(p)
    rows = []
    for ex in p.get("exchanges", []) or []:
        rows.append({"messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": ex["user"]},
            {"role": "assistant", "content": ex["assistant"]},
        ]})
    for sample in p.get("voice_examples", []) or []:
        rows.append({"messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Say something as {name}."},
            {"role": "assistant", "content": sample},
        ]})
    return rows


def build_one(name: str, out: Path | None = None) -> Path:
    pf = PERSONA_DIR / f"{name}.json"
    if not pf.exists():
        raise SystemExit(f"persona not found: {pf}")
    p = json.loads(pf.read_text(encoding="utf-8"))
    rows = build_rows(p)
    out = out or (ROOT / "data" / "godel" / "personas" / name / "script.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{p.get('name')}: {len(rows)} rows -> {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("persona", nargs="?", help="persona name (file stem in personas/)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--all", action="store_true", help="build every persona")
    args = ap.parse_args()
    if args.all:
        for pf in sorted(PERSONA_DIR.glob("*.json")):
            build_one(pf.stem)
    elif args.persona:
        build_one(args.persona, args.out)
    else:
        ap.error("give a persona name or --all")


if __name__ == "__main__":
    main()
