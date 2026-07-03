#!/usr/bin/env python3
"""director of scene — compose a SET of personas into an ensemble training script.

Extends the mindXtrain theatre model:

    model   = actor              (the tiny model that trains)
    persona = identity / voice   (mindx/godel/mindxtrain/personas/*.json)
    script  = the training rows   (the impression left on the actor)
    coach   = trains the actor    (mindxtrain train / the Coach UI)
    SET     = the scene's context (environment + situation the cast is in)
    DIRECTOR = orchestrates the cast through the beats of the scene

A single persona script imprints one voice in isolation. A *directed scene*
puts several actors on a SET and runs them through BEATS — each beat is one
character's line in context — so the imprint carries not just a voice but a
voice that holds character *within a scene, against other characters*. The
director fronts every row with the speaker's persona system prompt + the SET,
and feeds the running dialogue so far as context.

Output is the same OpenAI-chat JSONL mindXtrain's `data.source: local` ingests,
so a directed scene trains/imprints exactly like a single-persona script.

Usage:
  python scripts/direct_scene.py the_sovereign_workshop \
      [--out data/godel/scenes/the_sovereign_workshop/script.jsonl]
  python scripts/direct_scene.py --all
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

ROOT = Path(__file__).parent.parent
PERSONA_DIR = ROOT / "mindx" / "godel" / "mindxtrain" / "personas"
SCENE_DIR = ROOT / "mindx" / "godel" / "mindxtrain" / "scenes"


def _persona(name: str) -> dict:
    pf = PERSONA_DIR / f"{name}.json"
    if not pf.exists():
        raise SystemExit(f"cast member persona not found: {pf}")
    return json.loads(pf.read_text(encoding="utf-8"))


def _system(persona: dict, scene: dict) -> str:
    sp = (persona.get("system_prompt") or "").strip() or f"You are {persona.get('name','actor')}."
    set_ctx = (scene.get("set") or "").strip()
    direction = (scene.get("director") or "").strip()
    parts = [sp]
    if set_ctx:
        parts.append(f"SET — {scene.get('scene','the scene')}: {set_ctx}")
    if direction:
        parts.append(f"DIRECTION: {direction}")
    return "\n\n".join(parts)


def direct(scene: dict) -> list:
    """Turn a scene (set + cast + beats) into ensemble training rows.

    Each beat row: system = speaker's persona + the SET + the director's note;
    user = the dialogue so far (or the beat's explicit cue); assistant = the
    speaker's line. The actor learns to deliver its character's line given the
    scene and the conversation up to that point.
    """
    cast = {name: _persona(name) for name in scene.get("cast", [])}
    rows: list = []
    transcript: list = []   # running dialogue for context
    for beat in scene.get("beats", []):
        speaker = beat["speaker"]
        persona = cast.get(speaker) or _persona(speaker)
        line = beat["line"]
        cue = beat.get("cue")
        if cue:
            user = cue
        elif transcript:
            user = "Continue the scene. So far:\n" + "\n".join(transcript[-6:])
        else:
            opener = scene.get("opening_cue") or f"The scene opens. You speak first as {persona.get('name')}."
            user = opener
        rows.append({"messages": [
            {"role": "system", "content": _system(persona, scene)},
            {"role": "user", "content": user},
            {"role": "assistant", "content": line},
        ]})
        transcript.append(f"{persona.get('name')}: {line}")
    return rows


def build_one(stem: str, out: Path | None = None) -> Path:
    sf = SCENE_DIR / f"{stem}.json"
    if not sf.exists():
        raise SystemExit(f"scene not found: {sf}")
    scene = json.loads(sf.read_text(encoding="utf-8"))
    rows = direct(scene)
    out = out or (ROOT / "data" / "godel" / "scenes" / stem / "script.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"scene '{scene.get('scene', stem)}': cast={scene.get('cast')} "
          f"{len(rows)} beats -> {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scene", nargs="?", help="scene name (file stem in scenes/)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.all:
        for sf in sorted(SCENE_DIR.glob("*.json")):
            build_one(sf.stem)
    elif args.scene:
        build_one(args.scene, args.out)
    else:
        ap.error("give a scene name or --all")


if __name__ == "__main__":
    main()
