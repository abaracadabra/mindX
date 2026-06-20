"""Sentinel status + seeding for the self-improvement verification target.

`status()` is a cheap, read-only health/observation report consumed by
`/insight/sentinel/status` and the feedback UI. `seed()` registers the sentinel
as a backlog item (so the live autonomous loop targets it) and records a
baseline content hash — so the UI can show whether the loop has actually
*changed* the sentinel (proof the effector works end-to-end on a safe target).

No imports from mindx_backend_service — the dependency points downward only.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict

from utils.config import PROJECT_ROOT

TARGET_REL = "agents/sentinel/sentinel_target.py"
STATE_FILE = PROJECT_ROOT / "data" / "system_state" / "sentinel.json"
BACKLOG_FILE = PROJECT_ROOT / "data" / "improvement_backlog.json"
_CAMPAIGN_FILES = [
    PROJECT_ROOT / "data" / "sea_campaign_history" / "strategic_evolution_agent.json",
    PROJECT_ROOT / "data" / "memory" / "agent_workspaces" / "mastermind_prime" / "mastermind_campaigns_history.json",
]


def _load_state() -> Dict[str, Any]:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _save_state(st: Dict[str, Any]) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(st, indent=2), encoding="utf-8")
    except Exception:
        pass


def _sha(src: str) -> str:
    return hashlib.sha256(src.encode("utf-8")).hexdigest()


def _backlog_status() -> Dict[str, Any]:
    try:
        items = json.loads(BACKLOG_FILE.read_text(encoding="utf-8")) or []
    except Exception:
        return {"present": False}
    for it in items:
        tcp = str(it.get("target_component_path") or "")
        if "sentinel_target" in tcp:
            return {
                "present": True,
                "status": it.get("status") or "pending",
                "priority": it.get("priority"),
                "occurrences": it.get("occurrences"),
            }
    return {"present": False}


def _campaign_hits() -> Dict[str, Any]:
    count = 0
    last = None
    for f in _CAMPAIGN_FILES:
        try:
            data = json.loads(f.read_text(encoding="utf-8")) or []
        except Exception:
            continue
        for entry in data:
            try:
                if "sentinel_target" in json.dumps(entry):
                    count += 1
                    last = {
                        "status": entry.get("overall_campaign_status") or entry.get("status"),
                        "message": (entry.get("final_message") or entry.get("message") or "")[:180],
                    }
            except Exception:
                continue
    return {"count": count, "last": last}


def status() -> Dict[str, Any]:
    """Read-only sentinel health + change observation."""
    target = PROJECT_ROOT / TARGET_REL
    out: Dict[str, Any] = {
        "target": TARGET_REL,
        "exists": target.exists(),
        "note": "safe external self-improvement target; modifying it cannot affect production",
    }
    if not target.exists():
        out["healthy"] = False
        return out

    src = target.read_text(encoding="utf-8")
    sha = _sha(src)
    out["sha8"] = sha[:8]
    out["lines"] = src.count("\n") + 1
    try:
        out["mtime"] = target.stat().st_mtime
    except Exception:
        out["mtime"] = None

    # Health: compile + exec the *current on-disk* file in isolation and run
    # its verify() — so a loop edit that breaks the sentinel shows as unhealthy.
    try:
        ns: Dict[str, Any] = {}
        exec(compile(src, str(target), "exec"), ns)
        v = ns.get("verify", lambda: {"healthy": False})()
        out["healthy"] = bool(v.get("healthy"))
        out["version"] = v.get("version")
    except Exception as e:
        out["healthy"] = False
        out["error"] = str(e)[:200]

    # Baseline comparison — has the autonomous loop actually changed it?
    st = _load_state()
    baseline = st.get("baseline_sha")
    out["seeded"] = bool(baseline)
    out["baseline_sha8"] = (baseline[:8] if baseline else None)
    out["changed_by_loop"] = bool(baseline and sha != baseline)
    if baseline:
        last_seen = st.get("last_seen_sha", baseline)
        if sha != last_seen:
            st["last_seen_sha"] = sha
            st["last_change_ts"] = time.time()
            if sha != baseline:
                st["change_count"] = int(st.get("change_count", 0)) + 1
            _save_state(st)
    out["change_count"] = int(st.get("change_count", 0))
    out["last_change_ts"] = st.get("last_change_ts")

    out["backlog"] = _backlog_status()
    out["campaigns"] = _campaign_hits()
    return out


def seed(priority: int = 8) -> Dict[str, Any]:
    """Idempotently: record the baseline hash and add the sentinel backlog item
    so the live autonomous loop will target it."""
    target = PROJECT_ROOT / TARGET_REL
    result: Dict[str, Any] = {"backlog_added": False, "baseline_recorded": False}
    if not target.exists():
        result["error"] = "sentinel target missing"
        return result
    sha = _sha(target.read_text(encoding="utf-8"))

    st = _load_state()
    if not st.get("baseline_sha"):
        st.update({"baseline_sha": sha, "seeded_ts": time.time(),
                   "last_seen_sha": sha, "change_count": 0})
        _save_state(st)
        result["baseline_recorded"] = True
    result["baseline_sha8"] = sha[:8]

    # Ensure the backlog item exists (don't duplicate).
    try:
        items = json.loads(BACKLOG_FILE.read_text(encoding="utf-8")) or []
    except Exception:
        items = []
    if not any("sentinel_target" in str(it.get("target_component_path") or "") for it in items):
        items.append({
            "target_component_path": TARGET_REL,
            "suggestion": ("Improve the sentinel target module: clarify docstrings and add type "
                           "hints, harden add() for edge cases, and bump SENTINEL_VERSION."),
            "justification": ("Sentinel: safe end-to-end verification of the autonomous "
                              "self-improvement loop without touching production code."),
            "priority": priority,
            "source": "sentinel",
            "status": "pending",
            "occurrences": 1,
            "first_seen": time.time(),
            "last_seen": time.time(),
        })
        try:
            BACKLOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            BACKLOG_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")
            result["backlog_added"] = True
        except Exception as e:
            result["error"] = f"backlog write failed: {e}"
    return result
