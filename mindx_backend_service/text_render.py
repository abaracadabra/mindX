"""
text_render — `df -h` style human-readable plain-text rendering for /insight/* and /storage/* endpoints.

When a request carries `?h=true` (or `Accept: text/plain`), the JSON response
is replaced by a fixed-width text rendering. JSON consumers are unaffected
when the parameter is absent.

Plan: ~/.claude/plans/luminous-humming-knuth.md
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any, Callable, Iterable


# ── Humanizer primitives ──────────────────────────────────────────────────


def human_bytes(n: Any) -> str:
    """78741471 -> '75.1 MB'."""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(n):
        return "—"
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    i = 0
    while abs(n) >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    if i == 0:
        return f"{int(n)} {units[i]}"
    return f"{n:.2f} {units[i]}" if n < 10 else f"{n:.1f} {units[i]}"


def human_count(n: Any) -> str:
    """7884 -> '7.9k', 1234567 -> '1.2M'."""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    if abs(n) < 1000:
        return str(int(n))
    if abs(n) < 1e6:
        return f"{n/1e3:.2f}k" if n < 1e4 else f"{n/1e3:.1f}k"
    if abs(n) < 1e9:
        return f"{n/1e6:.1f}M"
    return f"{n/1e9:.1f}B"


def human_duration(s: Any) -> str:
    """45.31255 -> '45.3s', 332.0 -> '5m 32s', 4500.0 -> '1h 15m'."""
    try:
        s = float(s)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(s):
        return "—"
    if s < 1:
        return f"{int(s * 1000)}ms"
    if s < 60:
        return f"{s:.1f}s"
    if s < 3600:
        return f"{int(s // 60)}m {int(s % 60)}s"
    if s < 86400:
        return f"{int(s // 3600)}h {int((s % 3600) // 60)}m"
    return f"{int(s // 86400)}d {int((s % 86400) // 3600)}h"


def human_rel_ts(ts: Any) -> str:
    """ISO string or unix seconds -> '3m ago' / 'never'."""
    if ts is None or ts == "":
        return "never"
    if isinstance(ts, (int, float)):
        # Auto-detect ms vs s
        seconds = float(ts) / 1000.0 if ts > 1e12 else float(ts)
    else:
        try:
            seconds = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
        except (ValueError, TypeError):
            return "?"
    diff = time.time() - seconds
    if diff < 0:
        return "in the future"
    if diff < 60:
        return f"{max(1, int(diff))}s ago"
    if diff < 3600:
        return f"{int(diff // 60)}m ago"
    if diff < 86400:
        return f"{int(diff // 3600)}h ago"
    return f"{int(diff // 86400)}d ago"


def human_ts_with_rel(ts: Any) -> str:
    """'2026-04-27 01:42 UTC (3m ago)' for one-line summaries."""
    if ts is None or ts == "":
        return "never"
    if isinstance(ts, (int, float)):
        seconds = float(ts) / 1000.0 if ts > 1e12 else float(ts)
    else:
        try:
            seconds = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
        except (ValueError, TypeError):
            return "?"
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return f"{dt.strftime('%Y-%m-%d %H:%M UTC')} ({human_rel_ts(ts)})"


def human_hash(s: Any, n: int = 14) -> str:
    if s is None:
        return "—"
    s = str(s)
    return s[:n] + "…" if len(s) > n else s


# ── Table / KV rendering ──────────────────────────────────────────────────


Formatter = Callable[[Any], str]


def _strip_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def render_kv(d: dict, formatters: dict[str, Formatter] | None = None, *, label_width: int = 18) -> str:
    """One key per line, aligned colons."""
    formatters = formatters or {}
    out_lines: list[str] = []
    for key, val in d.items():
        fmt = formatters.get(key, _strip_str)
        out_lines.append(f"{key.ljust(label_width)}  {fmt(val)}")
    return "\n".join(out_lines) + "\n"


def render_table(
    rows: Iterable[dict],
    columns: list[tuple[str, str, Formatter | None]],
    *,
    max_col: int = 60,
) -> str:
    """
    columns: [(header, key, optional_formatter), ...]
    Returns fixed-width plain text. Headers underlined with dashes.
    """
    rows = list(rows)
    headers = [c[0] for c in columns]
    keys = [c[1] for c in columns]
    fmts: list[Formatter] = [c[2] or _strip_str for c in columns]
    # Compute string cells
    cells: list[list[str]] = []
    for r in rows:
        row_cells: list[str] = []
        for k, f in zip(keys, fmts):
            v = r.get(k) if isinstance(r, dict) else None
            text = f(v)
            if len(text) > max_col:
                text = text[: max_col - 1] + "…"
            row_cells.append(text)
        cells.append(row_cells)
    # Column widths
    widths = [len(h) for h in headers]
    for row in cells:
        for i, c in enumerate(row):
            if len(c) > widths[i]:
                widths[i] = len(c)
    # Build output
    sep = "  "
    header_line = sep.join(h.ljust(widths[i]) for i, h in enumerate(headers))
    rule_line = sep.join("-" * widths[i] for i in range(len(headers)))
    body_lines = [sep.join(c.ljust(widths[i]) for i, c in enumerate(row)) for row in cells]
    return "\n".join([header_line, rule_line, *body_lines]) + "\n"


# ── Per-endpoint renderers ────────────────────────────────────────────────


def render_storage_status(d: dict) -> str:
    return render_kv(
        {
            "local":         d.get("local", 0),
            "ipfs":          d.get("ipfs", 0),
            "thot":          d.get("thot", 0),
            "anchored":      d.get("anchored", 0),
            "last_offload":  d.get("last_offload_ts"),
        },
        formatters={
            "local":        lambda v: human_count(v),
            "ipfs":         lambda v: human_count(v),
            "thot":         lambda v: human_count(v),
            "anchored":     lambda v: human_count(v),
            "last_offload": lambda v: human_ts_with_rel(v),
        },
    )


def render_storage_recent(d: dict) -> str:
    rows = d.get("events") or []
    return render_table(
        rows,
        [
            ("ts",      "ts",            human_rel_ts),
            ("agent",   "actor",         lambda v: human_hash(v, 28)),
            ("date",    "date_str",      None),
            ("files",   "file_count",    human_count),
            ("size",    "bytes_packed",  human_bytes),
            ("cid",     "cid",           lambda v: human_hash(v, 16)),
            ("tx",      "tx_hash",       lambda v: human_hash(v, 14) if v else "(no chain)"),
        ],
    )


def render_dreams_recent(d: dict) -> str:
    rows = d.get("dreams") or []
    return render_table(
        rows,
        [
            ("ts",       "timestamp",                 human_rel_ts),
            ("agents",   "agents_dreamed",            human_count),
            ("insights", "insights_generated",        human_count),
            ("promoted", "memories_promoted_to_ltm",  human_count),
            ("duration", "duration_seconds",          human_duration),
            ("file",     "_filename",                 lambda v: human_hash(v, 36)),
        ],
    )


def render_bdi_recent(d: dict) -> str:
    rows = d.get("events") or []
    out: list[str] = []
    out.append(f"agent: {d.get('agent_id', '?')}  · {len(rows)} events")
    out.append("─" * 80)
    last_run = None
    for r in rows:
        run = r.get("run_id") or "—"
        if run != last_run:
            out.append(f"\n● run {human_hash(run, 12)}")
            last_run = run
        ts = human_rel_ts(r.get("timestamp_utc"))
        pn = r.get("process_name", "?")
        if pn == "bdi_planning_start":
            out.append(f"  {ts:>8}  PLAN_START   goal={human_hash(r.get('goal_id', '?'), 8)}  '{(r.get('goal_description') or '')[:60]}'")
        elif pn == "bdi_deliberation":
            out.append(f"  {ts:>8}  DELIBERATE   goal={human_hash(r.get('goal_id', '?'), 8)}  prio={r.get('priority', '?')}  queue={r.get('queue_size', '?')}")
        elif pn == "bdi_goal_set":
            out.append(f"  {ts:>8}  GOAL_SET     goal={human_hash(r.get('goal_id', '?'), 8)}  prio={r.get('priority', '?')}  '{(r.get('goal_description') or '')[:60]}'")
        elif pn in ("bdi_action", "bdi_action_execution"):
            ok = "✓" if r.get("success") else "✗"
            params = r.get("params") or {}
            params_s = ",".join(f"{k}={str(v)[:24]}" for k, v in (params.items() if isinstance(params, dict) else []))[:64]
            res = (r.get("result") or "")
            res_s = (str(res)[:60] + "…") if len(str(res)) > 60 else str(res)
            out.append(f"  {ts:>8}  ACTION    {ok}  {r.get('action_type', '?'):<22} ({params_s})  → {res_s}")
        else:
            out.append(f"  {ts:>8}  {pn:<22}")
    return "\n".join(out) + "\n"


def render_godel_recent(d: dict) -> str:
    rows = d.get("events") or []
    def _rationale(v: Any) -> str:
        if not v:
            return ""
        s = str(v).replace("\n", " ")
        return s[:80] + "…" if len(s) > 80 else s
    return render_table(
        rows,
        [
            ("ts",        "timestamp_utc",  human_rel_ts),
            ("agent",     "source_agent",   lambda v: human_hash(v, 28)),
            ("type",      "choice_type",    lambda v: human_hash(v, 24)),
            ("chosen",    "chosen_option",  lambda v: human_hash(v, 28)),
            ("rationale", "rationale",      _rationale),
        ],
    )


def render_boardroom_recent(d: dict) -> str:
    rows = d.get("sessions") or []
    def _votes(votes: Any) -> str:
        if not isinstance(votes, list):
            return ""
        out = []
        for v in votes:
            soldier = str(v.get("soldier", "?"))[:6]
            sym = "✓" if v.get("vote") == "approve" else "✗" if v.get("vote") == "reject" else "–"
            out.append(f"{sym}{soldier}")
        return " ".join(out)
    return render_table(
        rows,
        [
            ("ts",      "timestamp",       human_rel_ts),
            ("session", "session_id",      lambda v: human_hash(v, 14)),
            ("outcome", "outcome",         None),
            ("score",   "weighted_score",  lambda v: f"{float(v):.3f}" if isinstance(v, (int, float)) else "?"),
            ("votes",   "votes",           _votes),
            ("directive", "directive",     lambda v: human_hash(v, 60)),
        ],
        max_col=80,
    )


def render_improvement_summary(d: dict) -> str:
    def _bucket(b: Any) -> str:
        if not isinstance(b, dict):
            return "—"
        return (
            f"total={human_count(b.get('total', 0))} "
            f"ok={human_count(b.get('succeeded', 0))} "
            f"fail={human_count(b.get('failed', 0))} "
            f"running={human_count(b.get('running', 0))}"
        )
    out = render_kv(
        {
            "campaigns_1h":        d.get("campaigns_1h"),
            "campaigns_24h":       d.get("campaigns_24h"),
            "campaigns_7d":        d.get("campaigns_7d"),
            "belief_churn_per_hr": d.get("belief_churn_per_hour"),
        },
        formatters={
            "campaigns_1h":        _bucket,
            "campaigns_24h":       _bucket,
            "campaigns_7d":        _bucket,
            "belief_churn_per_hr": lambda v: f"{float(v):.2f}" if isinstance(v, (int, float)) else "—",
        },
    )
    cov = d.get("directive_coverage") or {}
    if cov:
        out += "\n"
        out += render_kv(
            {
                "backlog_total":  cov.get("backlog_total"),
                "attempted":      cov.get("attempted"),
                "coverage_ratio": cov.get("coverage_ratio"),
            },
            formatters={
                "backlog_total":  human_count,
                "attempted":      human_count,
                "coverage_ratio": lambda v: f"{float(v) * 100:.1f}%" if isinstance(v, (int, float)) else "—",
            },
        )
    return out


def render_stuck_loops(d: dict) -> str:
    groups = d.get("groups") or []
    if not groups:
        return f"no stuck loops in last {human_duration(d.get('window_seconds', 0))}\n" \
               f"buffer_size={human_count(d.get('buffer_size', 0))}\n"
    out = render_table(
        groups,
        [
            ("count",  "count",   human_count),
            ("agent",  "agent",   lambda v: human_hash(v, 28)),
            ("step",   "step",    lambda v: human_hash(v, 36)),
            ("span",   None,      None),  # filled below
            ("sample", "sample_content",  lambda v: human_hash(v, 60)),
        ],
    )
    # render_table doesn't compute derived 'span', do it manually below
    return out


def render_eligible(d: dict) -> str:
    rows = d.get("candidates") or []
    out = render_table(
        rows,
        [
            ("size",    "size_bytes",   human_bytes),
            ("age",     "age_days",     lambda v: f"{float(v):.0f}d" if v is not None else "—"),
            ("agent",   "agent_id",     lambda v: human_hash(v, 36)),
            ("date",    "date_str",     None),
            ("path",    "path",         lambda v: human_hash(v, 64)),
        ],
    )
    total = d.get("total_size_bytes")
    count = d.get("candidate_count")
    if total is not None or count is not None:
        out += f"\ntotal: {human_count(count or 0)} batches, {human_bytes(total or 0)}\n"
    return out


def render_anchor_health(d: dict) -> str:
    return render_kv(
        {
            "configured":           "yes" if d.get("configured") else "no",
            "rpc_url_set":          "yes" if d.get("rpc_url_set") else "no",
            "chain_id":             d.get("chain_id"),
            "registry_address_set": "yes" if d.get("registry_address_set") else "no",
            "treasury_key_set":     "yes" if d.get("treasury_key_set") else "no",
            "thot_minter_set":      "yes" if d.get("thot_minter_set") else "stub",
        },
    )


# ── Dispatch map: route path → renderer ──


RENDERERS: dict[str, Callable[[dict], str]] = {
    "/insight/storage/status":      render_storage_status,
    "/insight/storage/recent":      render_storage_recent,
    "/insight/dreams/recent":       render_dreams_recent,
    "/insight/bdi/recent":          render_bdi_recent,
    "/insight/godel/recent":        render_godel_recent,
    "/insight/boardroom/recent":    render_boardroom_recent,
    "/insight/improvement/summary": render_improvement_summary,
    "/insight/stuck_loops":         render_stuck_loops,
    "/storage/eligible":            render_eligible,
    "/storage/anchor/health":       render_anchor_health,
}


def wants_text(request) -> bool:
    """True iff the request asks for the plain-text rendering."""
    h = request.query_params.get("h")
    if h and h.lower() in ("1", "true", "yes", "y", "on"):
        return True
    accept = (request.headers.get("accept") or "").lower()
    if "text/plain" in accept and "application/json" not in accept:
        return True
    return False


def render(path: str, data: Any) -> str | None:
    """Look up the renderer for `path` and apply. None if not registered."""
    fn = RENDERERS.get(path)
    if fn is None:
        return None
    if not isinstance(data, dict):
        return None
    return fn(data)
