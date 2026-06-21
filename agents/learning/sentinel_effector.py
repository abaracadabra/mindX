"""
sentinel_effector.py — the HANDS of self-improvement, gated to the safe sentinel target.

Per the manifesto: SimpleCoder is the only agent allowed to edit mindX internals from self.improvement,
wrapped in SIA-style safety. This module closes the self-improvement loop's missing apply step:

    SimpleCoder (cloud-routed capable model) generates the edit
        → versioned BACKUP
        → WRITE to the real target
        → SELF-TEST (the sentinel's own verify())
        → CRITIQUE gate (LLM, >= threshold)
        → ROLLBACK on any failure.

ALLOWLIST: only `agents/sentinel/sentinel_target.py` (the designed safe target — imports nothing from
production, no side effects, not imported by any production path). Any other target is refused.
This is the proof-of-effector: a campaign that lands here changes the sentinel and passes verify(),
turning the loop from "generates suggestions forever" into "actually applies an improvement".
"""
from __future__ import annotations

import importlib.util
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from utils.config import PROJECT_ROOT
except Exception:  # pragma: no cover
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

# The ONLY path this effector may edit.
_ALLOWED_REL = "agents/sentinel/sentinel_target.py"
_CRITIQUE_THRESHOLD = 0.6


def _strip_fences(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"```(?:python)?\s*([\s\S]*?)```", text)
    code = m.group(1) if m else text
    return code.strip()


def _selftest(path: Path) -> tuple[bool, str]:
    """Import the edited module in isolation and run its verify(). No production import."""
    try:
        spec = importlib.util.spec_from_file_location(f"_sentinel_selftest_{int(time.time()*1000)}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # compiles + executes top-level
        if not hasattr(mod, "verify"):
            return False, "no verify() in edited module"
        res = mod.verify()
        if not isinstance(res, dict) or not res.get("healthy"):
            return False, f"verify() unhealthy: {res!r}"
        return True, f"verify ok: {res!r}"
    except Exception as e:
        return False, f"import/verify raised: {e}"


async def _critique(directive: str, before: str, after: str, handler) -> float:
    """LLM critique gate — score 0..1 that the change is a genuine, safe improvement."""
    try:
        prompt = (
            "You are a strict code reviewer. Score 0.0-1.0 whether the AFTER is a genuine, safe "
            "improvement over BEFORE for the directive, preserving behaviour (add/describe_status/verify "
            "must still work). Reply with ONLY a number.\n\n"
            f"DIRECTIVE: {directive}\n\nBEFORE:\n{before}\n\nAFTER:\n{after}\n\nScore:"
        )
        out = await handler.generate_text(prompt, model=getattr(handler, "model_name_for_api", None),
                                          max_tokens=16, temperature=0.0)
        m = re.search(r"(\d*\.?\d+)", out or "")
        return max(0.0, min(1.0, float(m.group(1)))) if m else 0.0
    except Exception:
        return 0.0


async def apply_sentinel_improvement(directive: str, *, llm_handler, logger=None,
                                     critique_threshold: float = _CRITIQUE_THRESHOLD) -> Dict[str, Any]:
    """Apply one improvement to the sentinel target via SimpleCoder + SIA-style safety.

    `llm_handler` is SimpleCoder's coding model (route it to the capable cloud model upstream).
    Returns {applied: bool, ...}. NEVER raises — rolls back and reports on any failure.
    """
    def _log(msg):
        if logger:
            logger.info(f"SentinelEffector: {msg}")

    path = (PROJECT_ROOT / _ALLOWED_REL).resolve()
    # Hard allowlist gate — refuse anything but the sentinel.
    if path != (PROJECT_ROOT / _ALLOWED_REL).resolve() or not path.exists():
        return {"applied": False, "reason": f"target not allowed / missing ({_ALLOWED_REL})"}

    original = path.read_text(encoding="utf-8")
    backup = path.with_name(path.name + f".bak.{int(time.time())}")
    backup.write_text(original, encoding="utf-8")
    _log(f"backup → {backup.name}; generating edit for: {directive[:80]}")

    try:
        prompt = (
            "You are SimpleCoder, mindX's coding hands. Improve this self-contained Python module per the "
            "directive. You MUST keep the functions add(a,b), describe_status(), and verify() working and "
            "keep verify() returning a healthy dict. Improve clarity/docstrings/typing/edge-cases and you "
            "MAY bump SENTINEL_VERSION. Return ONLY the complete improved file content — no fences, no prose.\n\n"
            f"DIRECTIVE: {directive}\n\nCURRENT FILE ({_ALLOWED_REL}):\n{original}\n"
        )
        new_code = _strip_fences(await llm_handler.generate_text(
            prompt, model=getattr(llm_handler, "model_name_for_api", None), max_tokens=4096, temperature=0.1))
        if not new_code or "def verify" not in new_code or "def add" not in new_code:
            raise ValueError("generated code missing required functions")
        if new_code.strip() == original.strip():
            raise ValueError("no change produced")

        path.write_text(new_code, encoding="utf-8")
        ok, msg = _selftest(path)
        if not ok:
            raise ValueError(f"self-test failed: {msg}")
        score = await _critique(directive, original, new_code, llm_handler)
        if score < critique_threshold:
            raise ValueError(f"critique {score:.2f} < threshold {critique_threshold}")

        _log(f"APPLIED ✓ self-test ok, critique {score:.2f} — sentinel improved")
        return {"applied": True, "critique": round(score, 3), "selftest": msg,
                "backup": backup.name, "bytes": len(new_code)}
    except Exception as e:
        path.write_text(original, encoding="utf-8")  # ROLLBACK
        _log(f"rolled back — {e}")
        return {"applied": False, "reason": str(e), "rolled_back": True, "backup": backup.name}
