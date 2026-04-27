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


def render_boardroom_session(d: dict) -> str:
    """Plain-text rendering of /insight/boardroom/session/<id> — full record
    of one boardroom decision (CEO + 7 soldiers). For terminal monitoring."""
    if "error" in d and "session_id" not in d:
        return f"boardroom session error: {d['error']}\n"
    if d.get("error"):
        return f"session {d.get('session_id', '?')} not found ({d['error']})\n"
    sid = d.get("session_id", "?")
    outcome = (d.get("outcome") or "?").upper()
    score = d.get("weighted_score", 0)
    threshold = d.get("consensus_threshold", 0.666)
    ts = d.get("timestamp", "")
    importance = d.get("importance", "")
    directive = (d.get("directive") or "")
    votes = d.get("votes") or []
    dissent = d.get("dissent_branches") or []
    mr = d.get("model_report") or {}

    lines = ["═══ boardroom session ═══", ""]
    lines.append(f"  id          {sid}")
    lines.append(f"  timestamp   {human_ts_with_rel(ts)}")
    lines.append(f"  importance  {importance}")
    lines.append(f"  outcome     {outcome}    score {score:.3f} / threshold {threshold:.3f}")
    lines.append("")
    lines.append("─── directive ───")
    for ln in (directive or "(empty)").split("\n"):
        lines.append(f"  {ln}")
    lines.append("")
    lines.append(f"─── votes ({len(votes)}) ───")
    for v in votes:
        soldier = v.get("soldier", "?")
        weight = v.get("weight", 1.0)
        veto = " VETO" if v.get("veto_holder") else ""
        vote = (v.get("vote") or "").upper()
        sym = "✓" if vote == "APPROVE" else "✗" if vote == "REJECT" else "–"
        provider = v.get("provider", "")
        latency = v.get("latency_ms")
        confidence = v.get("confidence", 0)
        reasoning = (v.get("reasoning") or "").strip()
        lat_s = f"{int(latency)} ms" if isinstance(latency, (int, float)) else "?"
        lines.append(f"  {sym} {soldier:<22} weight {weight:.1f}{veto}  {provider}  {lat_s}  conf {confidence:.2f}")
        if reasoning:
            for ln in reasoning.split("\n"):
                lines.append(f"      {ln}")
        lines.append("")
    if mr:
        lines.append("─── model_report ───")
        if "priority" in mr:
            lines.append(f"  priority    {mr.get('priority_label') or mr.get('priority')}")
        if "preempted_autonomous" in mr:
            lines.append(f"  preempted   {mr['preempted_autonomous']}")
        if "members" in mr and isinstance(mr["members"], dict):
            lines.append("  members:")
            for k, v in mr["members"].items():
                lines.append(f"    {k:<22} {v}")
        if "inference_summary" in mr and isinstance(mr["inference_summary"], dict):
            lines.append("  inference:")
            for k, v in mr["inference_summary"].items():
                lines.append(f"    {k:<22} {v}")
        lines.append("")
    lines.append(f"─── dissent ({len(dissent)} branch{'es' if len(dissent) != 1 else ''}) ───")
    for branch in dissent[:5]:
        lines.append(f"  • {str(branch)[:200]}")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_boardroom_cards(d: dict) -> str:
    """Plain-text rendering of /insight/boardroom/cards — composed system
    prompts for CEO + 7 soldiers, sourced from agents/boardroom/*.{agent,persona}.
    """
    if "error" in d:
        return f"cards error: {d['error']}\n"
    cards = d.get("cards") or {}
    lines = ["═══ boardroom — loaded prompt + persona per member ═══", ""]
    lines.append(f"  agents dir:        {d.get('agents_dir', 'agents/boardroom/')}")
    lines.append(f"  loaded from files: {d.get('loaded_from_files', 0)} / {d.get('total', 0)}")
    if d.get("fallback"):
        lines.append(f"  ! fallback (no files): {d['fallback']}")
    lines.append("")
    for mid, c in cards.items():
        veto = " VETO" if c.get("veto_holder") else ""
        sources = c.get("sources_loaded") or []
        src = "✓ " + "+".join(sources) if sources else "○ fallback dict"
        lines.append(f"─── {mid}  ({c.get('title', '')}, weight {c.get('weight', 1.0)}{veto}) ───")
        prompt_loc = c.get("prompt_source") or "—"
        lines.append(
            f"   sources:       {src}"
        )
        lines.append(
            f"   .prompt:       {c.get('prompt_chars', 0)} chars  ({prompt_loc})"
        )
        lines.append(
            f"   .agent:        {c.get('agent_card_chars', 0)} chars"
        )
        lines.append(
            f"   composed:      system_prompt = {c.get('system_prompt_chars', 0)} chars"
        )
        sp = c.get("system_prompt") or ""
        for sp_line in sp.split("\n")[:30]:
            lines.append(f"   {sp_line}")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_boardroom_members(d: dict) -> str:
    """Plain-text rendering of /insight/boardroom/members (fitness leaderboard)
    or a single-member detail card."""
    if "error" in d and "members" not in d:
        return f"members error: {d['error']}\n"
    # Single member detail (when /insight/boardroom/members/{id} hit)
    if "soldier" in d and "members" not in d:
        m = d
        lines = [f"═══ boardroom — {m.get('soldier')} ═══", ""]
        lines.append(f"  model        {m.get('model', '')}")
        lines.append(f"  weight       {m.get('weight', 1.0)}{'  VETO' if m.get('veto_holder') else ''}")
        lines.append(f"  sessions     {d.get('sessions_scanned', 0)} scanned · {m.get('votes_total', 0)} votes")
        lines.append(f"  fitness      {m.get('fitness', 0):.4f}  (avg)  ·  {m.get('fitness_p50', 0):.4f}  (p50)")
        lines.append(f"  utterance    {m.get('utterance_avg', 0):.3f}  ·  signal {m.get('signal_avg', 0):.3f}")
        lines.append(f"  latency      p50 {m.get('latency_p50_ms', 0)} ms  ·  p95 {m.get('latency_p95_ms', 0)} ms")
        lines.append(f"  vote mix     ✓{m.get('approve', 0)}  ✗{m.get('reject', 0)}  –{m.get('abstain', 0)}  ·  abstain rate {m.get('abstain_rate', 0):.1%}")
        lines.append(f"  avg conf     {m.get('avg_confidence', 0):.2f}")
        provs = m.get("providers") or {}
        if provs:
            lines.append("  providers    " + ", ".join(f"{k}×{v}" for k, v in provs.items()))
        lines.append("")
        last = m.get("last_votes") or []
        if last:
            lines.append(f"─── last {len(last)} votes ───")
            for v in last:
                vote = (v.get("vote") or "?").upper()
                sym = "✓" if vote == "APPROVE" else "✗" if vote == "REJECT" else "–"
                lines.append(f"  {sym} {(v.get('session_id') or ''):<16} {(v.get('ts') or '')[:19]}  conf {v.get('confidence', 0):.2f}  {v.get('latency_ms', 0)}ms")
                if v.get("directive"):
                    lines.append(f"      → {v['directive'][:120]}")
        lines.append("")
        return "\n".join(lines) + "\n"
    # Leaderboard
    members = d.get("members") or {}
    lines = ["═══ boardroom — fitness leaderboard ═══", ""]
    lines.append(f"  sessions scanned: {d.get('sessions_scanned', 0)}  ·  target chars/vote: {d.get('fitness_target_chars', 1500)}")
    lines.append("")
    if not members:
        lines.append("  no soldier data in window")
        lines.append("")
        return "\n".join(lines) + "\n"
    rows = sorted(members.values(), key=lambda m: m.get("fitness", 0), reverse=True)
    lines.append(f"  {'soldier':<22} {'fit':<7} {'sig':<5} {'utt':<5} {'p50ms':<7} {'p95ms':<7} {'abst':<5} votes")
    lines.append("  " + "─" * 80)
    for m in rows:
        veto = "*" if m.get("veto_holder") else " "
        lines.append(
            f"  {m['soldier']:<22} {m.get('fitness', 0):<7.4f} "
            f"{m.get('signal_avg', 0):<5.2f} {m.get('utterance_avg', 0):<5.2f} "
            f"{m.get('latency_p50_ms', 0):<7} {m.get('latency_p95_ms', 0):<7} "
            f"{m.get('abstain_rate', 0):<5.0%} {m.get('votes_total', 0)}{veto}"
        )
    lines.append("  " + "─" * 80)
    lines.append("  legend: fit=fitness  sig=signal_avg  utt=utterance_avg  abst=abstain_rate  *=veto holder")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_boardroom_rollcall(d: dict) -> str:
    """Plain-text rendering of /insight/boardroom/rollcall — live ack from each soldier."""
    if "error" in d and not d.get("results"):
        return f"roll call failed: {d['error']}\n"
    lines = ["═══ boardroom — CEO calls roll ═══", ""]
    if d.get("cached"):
        lines.append(f"  (cached · {d.get('age_seconds', 0)}s old · next in {d.get('next_invocation_in', 0)}s)")
        lines.append("")
    present = d.get("present", 0)
    total = d.get("total", 0)
    quorum = d.get("quorum", False)
    all_present = d.get("all_present", False)
    cloud = d.get("cloud_used", False)
    lines.append(f"  attendance:  {present}/{total} present  ·  quorum {'✓' if quorum else '✗'}  ·  full assembly {'✓' if all_present else '✗'}")
    lines.append(f"  inference:   {'cloud (gpt-oss:120b-cloud)' if cloud else 'local Ollama'}")
    lines.append("")
    sym = {"present": "✓", "silent": "○", "error": "!"}
    color = {"present": "", "silent": "", "error": ""}
    if d.get("advice"):
        lines.append(f"  ADVICE: {d['advice']}")
        lines.append("")
    results = d.get("results") or {}
    if results:
        for sid, r in results.items():
            state = r.get("state", "?")
            veto = " VETO" if r.get("veto_holder") else ""
            ack = (r.get("ack") or "").strip().replace("\n", " ")
            if not ack and state == "silent":
                ack = "(no response within timeout)"
            elif not ack and state == "error":
                ack = f"({(r.get('error') or 'error')[:120]})"
            lines.append(
                f"  {sym.get(state, '?')} {sid:<22} weight {r.get('weight', 1.0):.1f}{veto}  "
                f"{r.get('model_kind', '?'):<6}  {r.get('latency_ms', 0):>6}ms"
            )
            if ack:
                lines.append(f"      {ack[:200]}")
            lines.append("")
    return "\n".join(lines) + "\n"


def render_boardroom_health(d: dict) -> str:
    """Plain-text rendering of /insight/boardroom/health — CEO roll call."""
    if "error" in d:
        return f"boardroom health unavailable: {d['error']}\n"
    lines = ["═══ boardroom — CEO roll call ═══", ""]
    lines.append(f"  ollama:           {d.get('ollama_url', '')}")
    lines.append(f"  reachable:        {'✓' if d.get('ollama_reachable') else '✗'}")
    lines.append(f"  models pulled:    {d.get('models_pulled_total', 0)}")
    lines.append(f"  models loaded:    {d.get('models_loaded_total', 0)}")
    err = d.get("ollama_error")
    if err:
        lines.append(f"  ollama error:     {err}")
    lines.append("")
    sym = {"ready": "✓", "pulled": "○", "missing": "✗", "error": "!"}
    soldiers = d.get("soldiers") or {}
    if soldiers:
        lines.append(f"  {'soldier':<22} {'state':<10} {'model':<26} weight  veto")
        lines.append("  " + "─" * 84)
        for sid, info in soldiers.items():
            state = info.get("state", "?")
            veto = "✓" if info.get("veto_holder") else ""
            lines.append(
                f"  {sid:<22} {sym.get(state, '?')} {state:<8} "
                f"{info.get('model', ''):<26} {info.get('weight', 1.0):<6.1f} {veto}"
            )
    lines.append("")
    counts = d.get("counts") or {}
    lines.append(f"  ready={counts.get('ready', 0)}  pulled={counts.get('pulled', 0)}  missing={counts.get('missing', 0)}  error={counts.get('error', 0)}")
    lines.append(f"  cloud fallback:   {'✓ ' + (d.get('cloud_model') or '') if d.get('cloud_fallback_configured') else '✗ OFF (set OLLAMA_API_KEY)'}")
    lines.append(f"  convene_ok:       {'YES' if d.get('convene_ok') else 'NO'}  (quorum threshold: {d.get('ready_quorum_threshold', 4)} ready)")
    lines.append("")
    if d.get("advisory"):
        lines.append("  " + d["advisory"])
    lines.append("")
    return "\n".join(lines) + "\n"


def render_boardroom_roles(d: dict) -> str:
    """Plain-text rendering of /insight/boardroom/roles."""
    if "error" in d:
        return f"boardroom roles unavailable: {d['error']}\n"
    lines = ["═══ boardroom — CEO + 7 soldiers ═══", ""]
    ceo = d.get("ceo") or {}
    lines.append(f"  CEO  {ceo.get('title', '')}")
    lines.append(f"       {ceo.get('role', '')}")
    lines.append("")
    soldiers = d.get("soldiers") or {}
    if soldiers:
        lines.append(f"  {'soldier':<22} {'weight':<8} {'veto':<6} {'local model':<24} title")
        lines.append("  " + "─" * 92)
        for sid, info in soldiers.items():
            veto = "✓" if info.get("veto_holder") else ""
            lines.append(
                f"  {sid:<22} {info.get('weight', 1.0):<8.1f} {veto:<6} "
                f"{(info.get('local_model') or ''):<24} {info.get('title', '')}"
            )
    lines.append("")
    lines.append(f"  consensus threshold:  {d.get('consensus_threshold', 0.666):.3f}")
    lines.append(f"  cloud model:          {d.get('cloud_model', '')}")
    lines.append("")
    knobs = d.get("llm_knobs") or {}
    if knobs:
        lines.append("  ─── adjustable LLM knobs (env-overridable) ───")
        lines.append(f"  max_concurrent:       {knobs.get('max_concurrent')}      BOARDROOM_MAX_CONCURRENT")
        lines.append(f"  num_ctx:              {knobs.get('num_ctx')}     BOARDROOM_NUM_CTX")
        lines.append(f"  num_predict:          {knobs.get('num_predict')}      BOARDROOM_NUM_PREDICT")
        lines.append(f"  temperature:          {knobs.get('temperature')}      BOARDROOM_TEMPERATURE")
        lines.append(f"  rollcall_num_predict: {knobs.get('rollcall_num_predict')}       BOARDROOM_ROLLCALL_NUM_PREDICT")
        lines.append("")
    if d.get("note"):
        lines.append(f"  NOTE: {d['note']}")
    lines.append("")
    return "\n".join(lines) + "\n"


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


_COG_STATUS_GLYPH = {
    "real": "✓",
    "ready": "○",
    "stale": "·",
    "stub_no_key": "·",
    "open_loop": "·",
    "not_implemented": "✗",
    "not_running": "✗",
    "dead": "✗",
    "error": "!",
    "closed": "✓",
}


def render_cognition(d: dict) -> str:
    chain = d.get("chain") or {}
    rows: list[tuple[str, str, str]] = []  # (label, status_glyph status, detail)
    inf = chain.get("information") or {}
    rows.append(("information", inf.get("status", "?"), f"{inf.get('agents_with_stm', 0)} agents with STM"))
    cons = chain.get("consolidation") or {}
    age = cons.get("last_dream_age_seconds")
    age_str = human_duration(age) + " ago" if age is not None else "never"
    rows.append(("consolidation", cons.get("status", "?"),
                 f"{cons.get('dreams_total', 0)} dreams · {cons.get('dreams_24h', 0)} in 24h · last {age_str}"))
    kn = chain.get("knowledge") or {}
    kn_age = kn.get("last_updated_age_seconds")
    kn_age_s = human_duration(kn_age) + " ago" if kn_age is not None else "never"
    rows.append(("knowledge", kn.get("status", "?"),
                 f"{human_count(kn.get('ltm_files', 0))} LTM files · last {kn_age_s}"))
    cn = chain.get("concepts") or {}
    rows.append(("concepts", cn.get("status", "?"),
                 f"{cn.get('extracted_total', 0)} extracted · {cn.get('since_24h', 0)} in 24h"))
    w = chain.get("wisdom") or {}
    rows.append(("wisdom", w.get("status", "?"),
                 f"{w.get('verified_total', 0)} verified · {w.get('pending_verification', 0)} pending"))
    t = chain.get("thot") or {}
    minter = "key set" if t.get("minter_key_set") else "no key"
    rows.append(("thot", t.get("status", "?"),
                 f"{t.get('minted_total', 0)} minted · {t.get('pending_mint', 0)} queued · {minter}"))
    ing = chain.get("ingested") or {}
    rows.append(("ingested", ing.get("status", "?"),
                 f"{ing.get('external_wisdom_count', 0)} external"))
    fb = chain.get("feedback") or {}
    rows.append(("feedback", fb.get("status", "?"),
                 f"applied {fb.get('wisdom_applied_24h', 0)}/24h · violated {fb.get('wisdom_violated_24h', 0)}/24h"))

    out: list[str] = []
    out.append("information → knowledge → concept → wisdom → THOT → ingestion → feedback")
    out.append("─" * 78)
    for label, status, detail in rows:
        glyph = _COG_STATUS_GLYPH.get(status, "?")
        out.append(f"  {glyph}  {label:<14}  {status:<18}  {detail}")
    out.append("")
    out.append("  ✓ real / closed     ○ ready (gated)     · stale / stub")
    out.append("  ✗ not implemented   ! error")
    if d.get("narrative"):
        out.append("")
        out.append(d["narrative"])
    return "\n".join(out) + "\n"


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


def render_system(d: dict) -> str:
    """Plain-text rendering of /insight/system (psutil snapshot)."""
    if "error" in d:
        return f"system snapshot error: {d['error']}\n"
    c = d.get("compact") or {}
    snap = d.get("snapshot")  # only present when ?full=true
    lines = ["═══ system pulse (psutil) ═══", ""]
    lines.append(f"  cpu          {c.get('cpu_percent', 0):>5.1f}%   iowait {c.get('cpu_iowait', 0):>4.1f}%   steal {c.get('cpu_steal', 0):>4.1f}%   load1m {c.get('load_1m', 0):>5.2f}")
    lines.append(f"  memory       {c.get('memory_percent', 0):>5.1f}%   {c.get('memory_available_gb', 0):>5.2f} GB free")
    lines.append(f"  swap         {c.get('swap_percent', 0):>5.1f}%")
    lines.append(f"  disk /       {c.get('disk_root_percent', 0):>5.1f}%")
    lines.append(f"  sockets      {c.get('sockets_established', 0)} established")
    lines.append("")
    lines.append("─── self process (mindX backend) ───")
    lines.append(f"  rss          {c.get('self_rss_mb', 0):.1f} MB")
    lines.append(f"  cpu          {c.get('self_cpu_percent', 0):.1f}%")
    lines.append(f"  threads      {c.get('self_threads', 0)}")
    fds = c.get('self_fds', -1)
    lines.append(f"  fds          {fds if fds >= 0 else 'n/a'}")
    lines.append(f"  uptime       {human_duration(c.get('self_uptime_seconds', 0))}")
    if snap:
        lines.append("")
        lines.append("─── full snapshot (truncated) ───")
        cpu = snap.get("cpu", {}) or {}
        if cpu.get("times_percent"):
            tp = cpu["times_percent"]
            lines.append(f"  cpu times    user {tp.get('user', 0):.1f} system {tp.get('system', 0):.1f} idle {tp.get('idle', 0):.1f} iowait {tp.get('iowait', 0):.1f}")
        host = snap.get("host", {}) or {}
        if host.get("uptime_seconds"):
            lines.append(f"  host uptime  {human_duration(host['uptime_seconds'])}")
        if host.get("process_count"):
            lines.append(f"  processes    {host['process_count']}")
        net = snap.get("net", {}) or {}
        if isinstance(net.get("sockets"), dict):
            s = net["sockets"]
            lines.append(f"  sockets      tcp={s.get('tcp', 0)} udp={s.get('udp', 0)} listen={s.get('listen', 0)}")
        nics = (net.get("if_stats") or {})
        if nics:
            up = [n for n, s in nics.items() if s.get("isup")]
            lines.append(f"  nics up      {', '.join(up) if up else '(none)'}")
        sensors = snap.get("sensors", {}) or {}
        temps = sensors.get("temperatures") or {}
        if temps:
            for chip, entries in temps.items():
                for e in entries[:1]:
                    lines.append(f"  temp {chip[:12]:<12} {e.get('current', 0):.1f}°C ({e.get('label', '')})")
    lines.append("")
    return "\n".join(lines) + "\n"


RENDERERS: dict[str, Callable[[dict], str]] = {
    "/insight/storage/status":      render_storage_status,
    "/insight/storage/recent":      render_storage_recent,
    "/insight/dreams/recent":       render_dreams_recent,
    "/insight/bdi/recent":          render_bdi_recent,
    "/insight/cognition":           render_cognition,
    "/insight/system":              render_system,
    "/insight/godel/recent":        render_godel_recent,
    "/insight/boardroom/recent":    render_boardroom_recent,
    "/insight/boardroom/session":   render_boardroom_session,
    "/insight/boardroom/roles":     render_boardroom_roles,
    "/insight/boardroom/health":    render_boardroom_health,
    "/insight/boardroom/rollcall":  render_boardroom_rollcall,
    "/insight/boardroom/members":   render_boardroom_members,
    "/insight/boardroom/cards":     render_boardroom_cards,
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
