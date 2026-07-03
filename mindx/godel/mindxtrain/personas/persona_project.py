#!/usr/bin/env python3
"""persona_project.py — project a rich ``.persona`` to a mindXtrain imprint ``.json``.

A ``.persona`` (JSON) is the canonical identity: name, system_prompt, the BDI block
(beliefs/desires/intentions), skills, safety, embodiment, plus the imprint corpus
(``voice_examples`` + ``exchanges``). mindXtrain only reads the recognized imprint fields
(``name``, ``system_prompt``, ``voice_examples``, ``exchanges``), so this projector writes a
clean ``<persona>.json`` containing exactly those — the file ``scripts/build_persona_script.py``
already consumes. The rich ``.persona`` stays the source of truth; the ``.json`` is derived.

    python persona_project.py draiml          # writes draiml.json from draiml.persona
    python persona_project.py --all           # project every *.persona in this dir
    python persona_project.py draiml --check   # validate only (no write)

Validation enforces a real persona: the imprint fields, and — for a persona that *desires to be a
model* — at least one desire and a primary skill. Exit non-zero on failure (CI-friendly).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMPRINT_FIELDS = ("name", "system_prompt", "voice_examples", "exchanges")


def load_persona(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(p: dict, name: str) -> list[str]:
    errs: list[str] = []
    if not p.get("name"):
        errs.append("missing name")
    if not p.get("system_prompt"):
        errs.append("missing system_prompt")
    if not isinstance(p.get("voice_examples"), list) or not p["voice_examples"]:
        errs.append("voice_examples must be a non-empty list (the imprint baseline)")
    # a persona that desires to be a model must say so + declare where it starts
    bdi = p.get("bdi") or {}
    if not (bdi.get("desires") or []):
        errs.append("no bdi.desires — a persona that wants to be a model must state the desire")
    skills = p.get("skills") or {}
    if not skills.get("primary"):
        errs.append("no skills.primary — declare where the model starts (e.g. consulting)")
    return errs


def project(p: dict) -> dict:
    """Keep only the fields mindXtrain's clean-room loader recognizes."""
    return {k: p[k] for k in IMPRINT_FIELDS if k in p}


def run(name: str, check: bool) -> int:
    src = HERE / f"{name}.persona"
    if not src.exists():
        print(f"  ✗ {name}: no {src.name}")
        return 1
    p = load_persona(src)
    errs = validate(p, name)
    if errs:
        for e in errs:
            print(f"  ✗ {name}: {e}")
        return 1
    if check:
        d = (p.get("bdi") or {}).get("desires") or []
        print(f"  ✓ {name}: valid — primary skill '{p['skills']['primary']}', {len(d)} desire(s), "
              f"{len(p['voice_examples'])} voice examples")
        return 0
    out = HERE / f"{name}.json"
    out.write_text(json.dumps(project(p), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  ✓ {name} → {out.name} (imprint fields: {', '.join(k for k in IMPRINT_FIELDS if k in p)})")
    return 0


def main(argv: list[str]) -> int:
    check = "--check" in argv
    args = [a for a in argv if not a.startswith("--")]
    if "--all" in argv or not args:
        names = sorted(s.stem for s in HERE.glob("*.persona"))
    else:
        names = args
    rc = 0
    for n in names:
        rc |= run(n, check)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
