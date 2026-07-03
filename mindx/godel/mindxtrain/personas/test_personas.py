#!/usr/bin/env python3
"""test_personas.py — validate every .persona + the draiml desire-to-be-a-model contract.

    python test_personas.py     (exit 0 = pass)
"""
import json
import sys
from pathlib import Path

from persona_project import load_persona, validate, project, IMPRINT_FIELDS

HERE = Path(__file__).resolve().parent
passed = 0


def check(name, cond):
    global passed
    if cond:
        passed += 1
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}")
        sys.exit(1)


# 1. every *.persona validates and projects to the imprint schema
for src in sorted(HERE.glob("*.persona")):
    p = load_persona(src)
    check(f"{src.stem}.persona validates", validate(p, src.stem) == [])
    proj = project(p)
    check(f"{src.stem} projects to imprint fields only", set(proj) <= set(IMPRINT_FIELDS) and "name" in proj)

# 2. draiml: the medical-consulting, desire-to-be-a-model contract
d = load_persona(HERE / "draiml.persona")
check("draiml is medical", d.get("kind") == "medical")
check("draiml primary skill is consulting", d["skills"]["primary"] == "medical_consulting")
check("draiml desires to BECOME A MODEL", any("model" in x.lower() for x in d["bdi"]["desires"]))
check("draiml starts with consulting", any("consult" in x.lower() for x in d["bdi"]["intentions"]))
check("draiml has a safety disclaimer + escalation", bool(d["safety"]["disclaimer"]) and bool(d["safety"]["escalation"]))
check("draiml has an embodiment (face+voice clone binding)", "face" in d["embodiment"] and "voice" in d["embodiment"])
check("draiml does NOT claim to prescribe/diagnose", "not" in d["safety"]["scope"].lower() or "NOT" in d["safety"]["scope"])

# 3. projected draiml.json matches the roster schema exactly
j = json.loads((HERE / "draiml.json").read_text())
check("draiml.json keys == imprint fields", set(j.keys()) == set(IMPRINT_FIELDS))
check("draiml.json has a non-empty imprint corpus", len(j["voice_examples"]) >= 5 and len(j["exchanges"]) >= 3)

print(f"\n{passed} passed")
