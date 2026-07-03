# mindx_backend_service/self_diagnostic.py
"""The one honest answer to "what is mindX actually improving?"

Aggregates the substance scattered across the improvement machinery into a
single public diagnostic — real changes (milestones, publications, adoptions,
recorded code diffs) separated from process churn (campaign statuses, backlog
health, loop pathology), plus the live agent-to-agent interaction picture.

Born from the 2026-06 system review (docs/SYSTEM_REVIEW_2026_06.md): the
improvement surfaces showed counters while production ground a treadmill —
83,318 backlog copies of 6 suggestions, 100 identical campaigns/7d with 0
successes, and zero recorded autonomous code diffs. This module renders that
truth (and its repair) instead of hiding it. Warts-and-all is the doctrine.

Design (house patterns):
- file I/O in worker threads (asyncio.to_thread) — never blocks the loop
- 60s TTL cache + single lock, serve-stale-while-refreshing (cf. _DIAG_CACHE_TTL)
- lazy imports only; the agent stacks (mastermind/coordinator) are NEVER
  imported here — the 3-line fingerprint helper is duplicated by design
- every free-text string passes text_render.sanitize_text at build time
"""
from __future__ import annotations

import asyncio
import glob as _glob
import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

CACHE_TTL_S = 60.0
_cache: Optional[Dict[str, Any]] = None
_cache_ts: float = 0.0
_lock = asyncio.Lock()

# Local copy of agents/orchestration/mastermind_agent.suggestion_fingerprint —
# duplicated so the web process never imports the agent stack.
_DECORATION_RE = re.compile(r"\s*\[target: .*$", re.DOTALL)


def _fingerprint(text: str) -> str:
    return _DECORATION_RE.sub("", text or "").strip().lower()[:120]


def _san(s: Any, max_len: int = 200) -> str:
    try:
        from mindx_backend_service.text_render import sanitize_text
        return sanitize_text(str(s or ""), max_len)
    except Exception:
        return str(s or "")[:max_len]


# ── sync readers (run in worker threads) ─────────────────────────────────────
def _tail_jsonl(path: Path, tail_bytes: int = 512 * 1024) -> List[dict]:
    """Bounded tail-read of a JSONL file, oldest-first. O(1) on file size."""
    if not path.exists():
        return []
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            sz = f.tell()
            start = max(0, sz - tail_bytes)
            f.seek(start)
            chunk = f.read()
        lines = chunk.splitlines()
        if start > 0 and lines:
            lines = lines[1:]  # drop the partial first line
        rows: List[dict] = []
        for raw in lines:
            try:
                rows.append(json.loads(raw.decode("utf-8", errors="replace")))
            except Exception:
                continue
        return rows
    except Exception as e:
        logger.debug(f"self_diagnostic tail_jsonl({path.name}) failed: {e}")
        return []


def _read_milestones(root: Path, limit: int = 5) -> List[dict]:
    rows = _tail_jsonl(root / "data" / "milestones" / "milestone_log.jsonl", 256 * 1024)
    out = []
    for r in reversed(rows):
        if len(out) >= limit:
            break
        out.append({
            "ts": r.get("date") or r.get("ts"),
            "sha": (r.get("short_sha") or "")[:12],
            "subject": _san(r.get("subject"), 140),
            "worthy": bool(r.get("worthy")),
        })
    return out


def _read_catalogue_kinds(root: Path) -> Dict[str, List[dict]]:
    """One tail pass over the catalogue, bucketed by the kinds we surface."""
    rows = _tail_jsonl(root / "data" / "logs" / "catalogue_events.jsonl", 1024 * 1024)
    buckets: Dict[str, List[dict]] = {
        "publications": [], "adoptions": [], "code_change_events": [],
    }
    for r in reversed(rows):  # newest first
        kind = r.get("kind") or ""
        payload = r.get("payload") or {}
        if kind == "publication.published" and len(buckets["publications"]) < 5:
            buckets["publications"].append({
                "ts": r.get("ts"),
                "note": _san(payload.get("note") or payload.get("title") or payload.get("trigger_id"), 120),
            })
        elif kind == "library.discover" and len(buckets["adoptions"]) < 5:
            buckets["adoptions"].append({
                "ts": r.get("ts"),
                "package": _san(payload.get("package_name") or payload.get("name"), 60),
                "decision": _san(payload.get("decision") or payload.get("chosen"), 20),
            })
        elif kind in ("dreaming.improved", "improvement.executed") and len(buckets["code_change_events"]) < 5:
            buckets["code_change_events"].append({
                "ts": r.get("ts"),
                "kind": kind,
                "detail": _san(payload.get("new_hash") or payload.get("final_message")
                               or payload.get("summary"), 120),
            })
        if all(len(v) >= 5 for v in buckets.values()):
            break
    return buckets


def _read_sia_diffs(root: Path) -> Dict[str, Any]:
    pattern = str(root / "data" / "self_improvement_work_sia" / "**" / "improvement_history.jsonl")
    files = _glob.glob(pattern, recursive=True)
    count = 0
    samples: List[dict] = []
    for fp in files:
        rows = _tail_jsonl(Path(fp), 256 * 1024)
        for r in rows:
            if r.get("diff_patch") and "No functional code changes" not in str(r.get("diff_patch")):
                count += 1
                if len(samples) < 3:
                    samples.append({
                        "ts": r.get("timestamp"),
                        "target": _san(Path(str(r.get("target_file") or "?")).name, 60),
                        "success": bool(r.get("success")),
                        "diff_head": _san(str(r.get("diff_patch"))[:300], 300),
                    })
    note = None
    if count == 0:
        note = ("no recorded autonomous code diffs — every code change to date "
                "is operator-assisted (see milestones)")
    return {"count": count, "samples": samples, "note": note}


def _read_latest_dream(root: Path) -> Dict[str, Any]:
    dream_dir = root / "data" / "memory" / "dreams"
    if not dream_dir.is_dir():
        return {}
    reports = sorted(dream_dir.glob("*_dream_report.json"))
    if not reports:
        return {}
    try:
        r = json.loads(reports[-1].read_text(encoding="utf-8"))
    except Exception:
        return {}
    ts = r.get("timestamp")
    cadence_ok = None
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
        shift_h = float((r.get("timing") or {}).get("shift_interval_hours") or 8)
        cadence_ok = age_h <= (shift_h * 1.5)
    except Exception:
        pass
    return {
        "last_dream_ts": ts,
        "agents_dreamed": r.get("agents_dreamed"),
        "insights": r.get("insights_generated"),
        "ltm_promotions": r.get("memories_promoted_to_ltm"),
        "stm_bytes_freed": (r.get("diagnostic") or {}).get("stm_bytes_freed"),
        "cadence_ok": cadence_ok,
    }


def _read_self_improvement(root: Path) -> Dict[str, Any]:
    """The GROUND TRUTH of autonomous code self-improvement: the sentinel
    effector's real applies, measured by version progress in
    data/system_state/sentinel.json. The campaign-wrapper status undercounts
    this badly (it rarely reaches terminal SUCCESS even when the effector edits
    + verifies code), which is why the front page read "0/138, nothing happened"
    while v187 sat on disk. v1 is the seed; each apply bumps the version."""
    out = {"version": None, "applies": 0, "healthy": None, "changed_by_loop": None}
    # The version lives in the sentinel TARGET file's verify() return, not in
    # sentinel.json — sentinel.status() execs the target in isolation to read it.
    # The module is stdlib + utils.config only (no agent stack), safe here.
    try:
        from agents.sentinel.sentinel import status as _sentinel_status
        s = _sentinel_status()
        v = s.get("version")
        out["version"] = v
        out["healthy"] = s.get("healthy")
        out["changed_by_loop"] = s.get("changed_by_loop")
        if isinstance(v, int):
            out["applies"] = max(0, v - 1)
    except Exception:
        # Fallback: changed_by_loop/healthy from the state file if the import fails.
        try:
            st = json.loads((root / "data" / "system_state" / "sentinel.json").read_text(encoding="utf-8")) or {}
            out["healthy"] = st.get("healthy")
            out["changed_by_loop"] = st.get("changed_by_loop")
        except Exception:
            pass
    return out


def _read_training(root: Path) -> Dict[str, Any]:
    """The mindXtrain right-apex objective eval: dream→(dojo)→model imprints.

    machine.dream turns mindX's own memory (its logged actions) into training
    data; mindXtrain/the-dojo train *the mindX model* on it; a positive imprint
    (proof-of-recall) means the model absorbed the dream corpus — an improvement
    of mindX's actions learned from memory. This is REAL self-improvement that
    the code-diff counter cannot see. Source: data/logs/ascend_log.jsonl."""
    out = {"total": 0, "accepted": 0, "rate": None, "last_delta": None, "last_stage": None}
    rows = _tail_jsonl(root / "data" / "logs" / "ascend_log.jsonl", 256 * 1024)
    if not rows:
        return out
    recent = rows[-10:]
    out["total"] = len(recent)
    out["accepted"] = sum(1 for r in recent if r.get("accepted") or r.get("promoted"))
    out["rate"] = round(out["accepted"] / len(recent), 3) if recent else None
    last = recent[-1]
    out["last_delta"] = last.get("imprint_delta") or last.get("delta")
    out["last_stage"] = _san(last.get("stage") or last.get("status"), 40)
    return out


def _read_inference_appetite(root: Path) -> Dict[str, Any]:
    """Daily inference budget + per-model interaction health — the public display
    of mindX's inference 'appetite' (the operator directive). Shows how little of
    the free-tier ceiling is consumed and which models are live/dead."""
    out: Dict[str, Any] = {}
    try:
        from llm.inference_budget import daily_budget
        out["budget"] = daily_budget()
    except Exception:
        out["budget"] = {}
    try:
        from llm.model_health import snapshot as _mh_snapshot
        snap = _mh_snapshot()
        out["models"] = snap.get("summary", {})
        out["dead_slugs"] = snap.get("dead_slugs", [])[:12]
    except Exception:
        out["models"] = {}
        out["dead_slugs"] = []
    try:
        from llm.token_appetite import snapshot as _ta_snapshot
        out["lifetime"] = _ta_snapshot()  # seeded 347M, monotonic, incl. CPU tokens
    except Exception:
        out["lifetime"] = {}
    return out


# The Book of mindX publishes one full-moon edition per ~29.53-day lunar cycle,
# compiled from 27 daily chapters written across the cycle (AuthorAgent). The
# schedule eval below is honest cadence-keeping (warts-and-all): is the edition
# overdue, and how complete is the current cycle's daily coverage.
_LUNAR_CYCLE_DAYS = 29.53
_BOOK_GRACE_DAYS = 2.0  # full moon timing drift + compile latency


def _read_book_schedule(root: Path) -> Dict[str, Any]:
    """Eval of the Book-of-mindX publishing schedule. Reads the daily-chapter
    archive + full-moon editions (docs/publications/) and reports cadence: days
    since last edition, overdue flag, and current-cycle daily coverage."""
    out: Dict[str, Any] = {
        "last_edition_date": None, "days_since_edition": None, "overdue": None,
        "cycle_days_elapsed": None, "cycle_chapters_written": 0,
        "cycle_expected": None, "coverage_ratio": None, "verdict": "unknown",
    }
    daily_dir = root / "docs" / "publications" / "daily"
    if not daily_dir.is_dir():
        return out
    import re as _re
    from datetime import datetime as _dt, timezone as _tz
    _date_re = _re.compile(r"day_(\d{1,2})_.*?(\d{8})\.md$")

    def _parse(p: Path):
        m = _date_re.search(p.name)
        if not m:
            return None
        try:
            return int(m.group(1)), _dt.strptime(m.group(2), "%Y%m%d").replace(tzinfo=_tz.utc)
        except Exception:
            return None

    parsed = [r for r in (_parse(p) for p in daily_dir.glob("day_*.md")) if r]
    if not parsed:
        return out
    # Full-moon editions are the day-28 compile events.
    editions = sorted(d for (n, d) in parsed if n >= 28)
    now = _dt.now(_tz.utc)
    if editions:
        last_ed = editions[-1]
        out["last_edition_date"] = last_ed.strftime("%Y-%m-%d")
        days_since = (now - last_ed).total_seconds() / 86400.0
        out["days_since_edition"] = round(days_since, 1)
        out["overdue"] = days_since > (_LUNAR_CYCLE_DAYS + _BOOK_GRACE_DAYS)
        # Current cycle = chapters dated after the last edition.
        cycle_days = list(d for (n, d) in parsed if d > last_ed and n < 28)
        distinct = {d.strftime("%Y%m%d") for d in cycle_days}
        out["cycle_chapters_written"] = len(distinct)
        out["cycle_days_elapsed"] = round(days_since, 1)
        out["cycle_expected"] = min(27, int(days_since))
        exp = out["cycle_expected"] or 0
        out["coverage_ratio"] = round(out["cycle_chapters_written"] / exp, 2) if exp > 0 else None
    if out["overdue"]:
        out["verdict"] = "overdue"
    elif out["coverage_ratio"] is not None and out["coverage_ratio"] < 0.5:
        out["verdict"] = "behind"
    elif out["last_edition_date"]:
        out["verdict"] = "on_track"
    return out


def _read_campaigns(root: Path) -> Dict[str, Any]:
    path = (root / "data" / "memory" / "agent_workspaces" / "mastermind_prime"
            / "mastermind_campaigns_history.json")
    try:
        campaigns = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except Exception:
        campaigns = []
    if not isinstance(campaigns, list):
        campaigns = []
    now = time.time()
    # Only ts-stamped records can prove they're recent; legacy rows without ts
    # must not masquerade as this week's activity. Fall back to the last 100
    # when nothing is stamped (matches /insight/improvement/summary's 7d slice).
    week = [c for c in campaigns if isinstance(c, dict) and c.get("ts")
            and (now - float(c["ts"])) < 7 * 86400] or campaigns[-100:]

    buckets = Counter()
    shapes = Counter()
    fps = Counter()
    for c in week:
        status = str(c.get("overall_campaign_status") or "").upper()
        msg = str(c.get("final_bdi_message") or "")
        mu = msg.upper()
        if "COMPLETED_GOAL_ACHIEVED" in mu or status == "SUCCESS":
            buckets["succeeded"] += 1
        elif "CYCLE EXCEPTION" in mu:
            buckets["errored"] += 1
        elif "TIMED_OUT" in mu or status == "TIMED_OUT":
            buckets["timed_out"] += 1
        elif "FAILED" in mu:
            buckets["failed"] += 1
        elif "MAX_CYCLES_REACHED" in mu or status == "MAX_CYCLES_REACHED" or "RUNNING" in mu:
            buckets["max_cycles_reached"] += 1
        else:
            buckets["failed"] += 1
        shape = _san(re.sub(r"\s+", " ", msg).strip()[:80] or status, 80)
        if shape:
            shapes[shape] += 1
        fp = _fingerprint(c.get("directive") or "")
        if fp:
            fps[fp] += 1

    looped = []
    for fp, n in fps.most_common(3):
        if n > 3:
            looped.append({
                "directive": _san(fp, 100),
                "count": n,
                "diagnosis": ("repeating (agent, step) — typically a selector/fingerprint "
                              "mismatch or non-terminal BDI status"),
            })
    return {
        "campaigns_7d": {"total": len(week), **{k: buckets.get(k, 0) for k in
                         ("succeeded", "failed", "timed_out", "max_cycles_reached", "errored")}},
        "top_failure_shapes": [{"shape": s, "count": n} for s, n in shapes.most_common(3)],
        "looped_directives": looped,
    }


def _read_backlog(root: Path) -> Dict[str, Any]:
    path = root / "data" / "improvement_backlog.json"
    try:
        items = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except Exception:
        items = []
    if not isinstance(items, list):
        items = []
    fps = {_fingerprint((i.get("suggestion") or i.get("description") or "")) for i in items
           if isinstance(i, dict)}
    fps.discard("")
    unique = len(fps)
    attempted = sum(1 for i in items if isinstance(i, dict)
                    and str(i.get("status") or "").lower() in ("attempted", "complete", "completed"))
    return {
        "size": len(items),
        "unique": unique,
        "dup_factor": round(len(items) / max(1, unique), 1),
        "attempted": attempted,
        "coverage_ratio": round(attempted / max(1, len(items)), 4),
        "dedup_live": len(items) == unique,
    }


def _read_heartbeat_sample(root: Path, limit: int = 3) -> List[dict]:
    rows = _tail_jsonl(root / "data" / "logs" / "heartbeat_dialogues.jsonl", 128 * 1024)
    out = []
    for r in reversed(rows):
        if len(out) >= limit:
            break
        out.append({
            "ts": r.get("timestamp"),
            "model": _san(r.get("model"), 60),
            "thought": _san(r.get("response"), 200),
        })
    return out


# ── async assembly ───────────────────────────────────────────────────────────
async def _stuck_loops_summary() -> Dict[str, Any]:
    try:
        from mindx_backend_service.activity_feed import ActivityFeed
        feed = ActivityFeed.get_instance()
        cutoff = time.time() - 900
        groups = Counter()
        for ev in feed.recent(limit=200):  # list of dicts, newest first
            if float(ev.get("timestamp") or 0) < cutoff:
                continue
            agent = ev.get("agent") or "?"
            step = str(ev.get("content") or ev.get("type") or "").split(":", 1)[0][:80]
            groups[(agent, step)] += 1
        loops = [{"agent": _san(a, 60), "step": _san(s, 80), "count": n}
                 for (a, s), n in groups.most_common(5) if n >= 5]
        return {"count": len(loops), "groups": loops}
    except Exception:
        return {"count": 0, "groups": []}


async def _eval_gate_summary() -> Dict[str, Any]:
    try:
        from agents.memory_agent import _eval_health
        snap = _eval_health.snapshot()
        return {k: snap.get(k) for k in ("gate_open", "attempts", "hits", "misses", "mean_score")}
    except Exception:
        return {"gate_open": None}


async def _interactions() -> Dict[str, Any]:
    try:
        from agents.memory_pgvector import get_interaction_matrix, get_recent_interactions
        matrix = await get_interaction_matrix()
        recent = await get_recent_interactions(15)
        for e in matrix.get("edges", []):
            e["from"] = _san(e.get("from"), 60)
            e["to"] = _san(e.get("to"), 60)
        for r in recent:
            r["summary"] = _san(r.get("summary"), 100)
        return {"matrix": matrix, "recent": recent}
    except Exception:
        return {"matrix": {"edges": [], "agents": []}, "recent": []}


def _build_verdict(real: Dict[str, Any], cons: Dict[str, Any], ph: Dict[str, Any]) -> Dict[str, Any]:
    evidence: List[str] = []
    c7 = ph.get("campaigns_7d") or {}
    bl = ph.get("backlog") or {}
    if cons.get("ltm_promotions"):
        evidence.append(f"memory consolidation real: {cons['ltm_promotions']} LTM promotions last dream cycle")
    if real.get("milestones"):
        evidence.append(f"{len(real['milestones'])} recent milestones (operator-assisted git history)")
    if real.get("publications"):
        evidence.append(f"{len(real['publications'])} recent publications")
    if real.get("adoptions"):
        evidence.append(f"{len(real['adoptions'])} external-package adoption decisions")
    sia = (real.get("sia_diffs") or {})
    evidence.append(f"{sia.get('count', 0)} autonomous code diffs recorded")
    looped = ph.get("looped_directives") or []
    if looped:
        worst = looped[0]
        evidence.append(f"improvement loop pathology: {len(looped)} looping directive(s), worst repeated {worst['count']}x")
    if bl:
        evidence.append(f"backlog {bl.get('size')} items / {bl.get('unique')} unique"
                        + (" (dedup live)" if bl.get("dedup_live") else f" (dup_factor {bl.get('dup_factor')}x)"))
    ok = c7.get("succeeded", 0)
    total = c7.get("total", 0)
    diffs = sia.get("count", 0)
    ltm = cons.get("ltm_promotions", 0)
    pubs = len(real.get("publications") or [])
    stuck = (ph.get("stuck_loops") or {}).get("count", 0)

    # The GROUND-TRUTH self-improvement signals that the campaign-wrapper and the
    # code-diff counter both miss (the cause of the "0/138, nothing happened"
    # stale headline). Real change has THREE channels, not one:
    #   1. sentinel code self-improvement loop (version applies)
    #   2. dream → (dojo) → mindXtrain MODEL imprints (the mindX model learning
    #      from its own memory) — see EVALUATION_AUDIT.md §4
    #   3. memory consolidation (LTM promotions)
    si = real.get("self_improvement") or {}
    train = real.get("training") or {}
    applies = si.get("applies", 0)
    si_version = si.get("version")
    si_healthy = si.get("healthy")
    imprints_ok = train.get("accepted", 0)
    imprints_total = train.get("total", 0)
    if applies:
        evidence.append(f"sentinel self-improvement: {applies} applies (v{si_version}, "
                        f"{'healthy' if si_healthy else 'unverified'})")
    if imprints_total:
        evidence.append(f"mindXtrain model imprints from dream-training: {imprints_ok}/{imprints_total} took")

    # Compose the verdict live from what is actually true right now — no frozen
    # narrative or dates, so the line can never read stale. Warts-and-all.
    # LEAD with the real gains (the honest mirror), not the campaign 0/X.
    gains = []
    if applies:
        gains.append(f"applied {applies} self-improvements (sentinel v{si_version})")
    if imprints_ok:
        gains.append(f"imprinted {imprints_ok}/{imprints_total} model trainings from its own dreams")
    if ltm:
        gains.append(f"consolidated {ltm} memories to long-term last dream")
    if pubs:
        gains.append(f"published {pubs}")
    lead = "mindX " + (", ".join(gains) if gains else "shows no real gains this window")

    # Campaign rate is process health, NOT the headline — and is qualified so a
    # known-failing wrapper can't read as "mindX did nothing."
    health = []
    if applies and not diffs:
        health.append(f"code self-improvement via the sentinel effector (v{si_version}); "
                      f"0 free-form code diffs recorded")
    elif diffs:
        health.append(f"autonomous code self-improvement producing ({diffs} recorded diffs)")
    else:
        health.append("autonomous code self-improvement not yet real (0 diffs)")
    if total:
        health.append(f"campaign wrapper {ok}/{total} in 7d"
                      + (" — wrapper under-reports; effector applies are the truth" if (applies and not ok) else ""))
    if looped:
        health.append(f"{len(looped)} looping directive(s)")
    if stuck:
        health.append(f"{stuck} stuck loop(s)")
    # Book-of-mindX publishing-schedule eval (cadence-keeping, warts-and-all).
    bk = ph.get("book_schedule") or {}
    if bk.get("verdict") and bk.get("verdict") != "unknown":
        if bk.get("verdict") == "overdue":
            health.append(f"Book edition overdue ({bk.get('days_since_edition')}d since last, cycle ~{_LUNAR_CYCLE_DAYS:.0f}d)")
        elif bk.get("verdict") == "behind":
            health.append(f"Book daily chapters behind ({bk.get('cycle_chapters_written')}/{bk.get('cycle_expected')} this cycle)")
        else:
            health.append(f"Book on schedule ({bk.get('cycle_chapters_written')}/{bk.get('cycle_expected')} chapters, last edition {bk.get('days_since_edition')}d ago)")

    # Verdict tag from the FULL picture of real change, not campaigns alone.
    real_change = bool(applies or imprints_ok or diffs)
    if real_change and ok:
        tag = "process and real change are aligned"
    elif real_change:
        tag = "real change is happening through the effector/training loop even as the campaign wrapper lags"
    else:
        tag = "the gap between process and real change is the watch"

    line = f"{lead}; {'; '.join(health)}. {tag}."
    return {"line": line, "evidence": evidence}


async def compute_self_diagnostic(root: Optional[Path] = None) -> Dict[str, Any]:
    """Assemble the full diagnostic. `root` overrides PROJECT_ROOT for tests."""
    base = Path(root) if root else PROJECT_ROOT

    (milestones, catalogue, sia, dream, campaigns, backlog, heartbeat,
     self_improvement, training, appetite, book_schedule) = await asyncio.gather(
        asyncio.to_thread(_read_milestones, base),
        asyncio.to_thread(_read_catalogue_kinds, base),
        asyncio.to_thread(_read_sia_diffs, base),
        asyncio.to_thread(_read_latest_dream, base),
        asyncio.to_thread(_read_campaigns, base),
        asyncio.to_thread(_read_backlog, base),
        asyncio.to_thread(_read_heartbeat_sample, base),
        asyncio.to_thread(_read_self_improvement, base),
        asyncio.to_thread(_read_training, base),
        asyncio.to_thread(_read_inference_appetite, base),
        asyncio.to_thread(_read_book_schedule, base),
    )
    stuck, eval_gate, interactions = await asyncio.gather(
        _stuck_loops_summary(), _eval_gate_summary(), _interactions()
    )

    real_changes = {
        "milestones": milestones,
        "publications": catalogue["publications"],
        "adoptions": catalogue["adoptions"],
        "code_change_events": catalogue["code_change_events"],
        "sia_diffs": sia,
        "self_improvement": self_improvement,
        "training": training,
    }
    process_health = {
        **campaigns,
        "backlog": backlog,
        "stuck_loops": stuck,
        "eval_gate": eval_gate,
        "inference_appetite": appetite,
        "book_schedule": book_schedule,
    }
    return {
        "generated_at": time.time(),
        "real_changes": real_changes,
        "consolidation": dream,
        "process_health": process_health,
        "self_interaction": {
            "matrix": interactions["matrix"],
            "recent": interactions["recent"],
            "heartbeat_sample": heartbeat,
        },
        "verdict": _build_verdict(real_changes, dream, process_health),
    }


async def get_cached(root: Optional[Path] = None) -> Dict[str, Any]:
    """60s-TTL cached diagnostic; serves stale while a refresh is in flight."""
    global _cache, _cache_ts
    now = time.time()
    if _cache is not None and (now - _cache_ts) < CACHE_TTL_S:
        out = dict(_cache)
        out["cache_age_s"] = round(now - _cache_ts, 1)
        return out
    if _lock.locked() and _cache is not None:
        out = dict(_cache)
        out["cache_age_s"] = round(now - _cache_ts, 1)
        out["stale"] = True
        return out
    async with _lock:
        # double-check after acquiring
        if _cache is not None and (time.time() - _cache_ts) < CACHE_TTL_S:
            return dict(_cache)
        _cache = await compute_self_diagnostic(root)
        _cache_ts = time.time()
        return dict(_cache)
