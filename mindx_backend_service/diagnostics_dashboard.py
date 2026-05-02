"""
mindX Public Diagnostics Dashboard
Non-interactive, read-only, auto-refreshing activity view.
Served at / for public. No secrets exposed.
"""

import time
import json
import os
import psutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["diagnostics"])

_start_time = time.time()


def _safe_read_jsonl(path: Path, limit: int = 20) -> List[dict]:
    """Read last N lines from a JSONL file."""
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        lines = [l for l in lines if l.strip()]
        entries = []
        for line in lines[-limit:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        entries.reverse()
        return entries
    except Exception:
        return []


def _count_files(directory: Path, pattern: str = "*.json") -> int:
    """Count files matching pattern in directory tree."""
    try:
        return sum(1 for _ in directory.rglob(pattern))
    except Exception:
        return 0


@router.get("/diagnostics/live", response_class=JSONResponse)
async def diagnostics_live():
    """Aggregated diagnostics data for the dashboard. No secrets."""
    now = time.time()
    uptime_seconds = now - _start_time

    # System resources
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        system = {
            "cpu_percent": cpu_percent,
            "memory_used_gb": round(mem.used / (1024**3), 2),
            "memory_total_gb": round(mem.total / (1024**3), 2),
            "memory_percent": mem.percent,
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_percent": round(disk.percent, 1),
        }
    except Exception:
        system = {}

    # Uptime
    days, rem = divmod(int(uptime_seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    uptime_str = f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m"

    # Beliefs
    beliefs_path = PROJECT_ROOT / "data" / "memory" / "beliefs.json"
    belief_count = 0
    belief_sample = []
    try:
        if beliefs_path.exists():
            beliefs = json.loads(beliefs_path.read_text())
            belief_count = len(beliefs)
            for k, v in list(beliefs.items())[:6]:
                val = v.get("value", "")
                if isinstance(val, str) and len(val) > 50:
                    val = val[:50] + "..."
                belief_sample.append({"key": k, "value": val})
    except Exception:
        pass

    # Memory stats
    stm_path = PROJECT_ROOT / "data" / "memory" / "stm"
    stm_count = _count_files(stm_path, "*.memory.json")
    workspace_path = PROJECT_ROOT / "data" / "memory" / "agent_workspaces"
    agent_workspace_count = sum(1 for d in workspace_path.iterdir() if d.is_dir()) if workspace_path.exists() else 0

    # Godel choices
    godel_path = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
    godel_choices = _safe_read_jsonl(godel_path, limit=10)
    godel_display = []
    for g in godel_choices:
        godel_display.append({
            "timestamp": g.get("timestamp", ""),
            "agent": g.get("source_agent", "unknown"),
            "type": g.get("choice_type", ""),
            "chosen": str(g.get("chosen", ""))[:100],
        })

    # Agent identity registry
    registry_path = PROJECT_ROOT / "data" / "identity" / "production_registry.json"
    agents = []
    try:
        if registry_path.exists():
            reg = json.loads(registry_path.read_text())
            for a in reg.get("agents", []):
                agents.append({
                    "entity_id": a["entity_id"],
                    "address": a["address"],
                    "role": a.get("role", ""),
                })
    except Exception:
        pass

    # Inference sources
    inference = {"total": 0, "available": 0, "sources": {}}
    try:
        from llm.inference_discovery import InferenceDiscovery
        discovery = await InferenceDiscovery.get_instance()
        summary = discovery.status_summary()
        inference = {
            "total": summary.get("total_sources", 0),
            "available": summary.get("available", 0),
            "local_inference": summary.get("local_inference", False),
            "cloud_inference": summary.get("cloud_inference", False),
            "sources": summary.get("sources", {}),
        }
    except Exception:
        pass

    # Vault status (no secrets)
    vault_status = {}
    try:
        from mindx_backend_service.bankon_vault.vault import BankonVault
        v = BankonVault()
        vault_status = v.info()
        vault_status.pop("vault_dir", None)
    except Exception:
        pass

    # Recent log entries (last 15 lines of runtime log, sanitized)
    log_path = PROJECT_ROOT / "data" / "logs" / "mindx_runtime.log"
    recent_logs = []
    try:
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8").strip().split("\n")
            for line in lines[-15:]:
                # Strip sensitive info
                if "API_KEY" in line or "private_key" in line.lower() or "WALLET_PK" in line:
                    continue
                recent_logs.append(line[:200])
            recent_logs.reverse()
    except Exception:
        pass

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": uptime_str,
        "uptime_seconds": int(uptime_seconds),
        "system": system,
        "agents": agents,
        "beliefs": {"count": belief_count, "sample": belief_sample},
        "memory": {
            "stm_records": stm_count,
            "agent_workspaces": agent_workspace_count,
        },
        "godel_choices": godel_display,
        "inference": inference,
        "vault": vault_status,
        "recent_logs": recent_logs,
    }


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mindX — Live Diagnostics</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace; background: #0a0e14; color: #c5cdd9; min-height: 100vh; overflow-x: hidden; }
.header { padding: 20px 24px 12px; border-bottom: 1px solid #1a1f2e; display: flex; justify-content: space-between; align-items: center; }
.header h1 { font-size: 18px; color: #e6edf3; letter-spacing: 1px; }
.header h1 span { color: #58a6ff; }
.status-badge { font-size: 11px; padding: 4px 10px; border-radius: 12px; background: #0d3321; color: #3fb950; border: 1px solid #238636; }
.status-badge.warn { background: #3d2b00; color: #d29922; border-color: #9e6a03; }
.uptime { font-size: 11px; color: #6e7681; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 1px; background: #1a1f2e; padding: 1px; }
.card { background: #0d1117; padding: 16px; }
.card-title { font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #6e7681; margin-bottom: 10px; }
.metric { font-size: 28px; font-weight: 600; color: #e6edf3; line-height: 1.2; }
.metric-sm { font-size: 13px; color: #8b949e; margin-top: 2px; }
.bar-container { height: 4px; background: #21262d; border-radius: 2px; margin-top: 8px; overflow: hidden; }
.bar { height: 100%; border-radius: 2px; transition: width 0.8s ease; }
.bar-green { background: #3fb950; }
.bar-yellow { background: #d29922; }
.bar-red { background: #f85149; }
.agent-row { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #161b22; font-size: 12px; }
.agent-row:last-child { border: none; }
.agent-name { color: #c9d1d9; }
.agent-addr { color: #58a6ff; font-size: 11px; }
.agent-role { color: #6e7681; font-size: 10px; margin-top: 1px; }
.source-row { display: flex; justify-content: space-between; padding: 3px 0; font-size: 12px; }
.dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 6px; position: relative; top: -1px; }
.dot-green { background: #3fb950; }
.dot-red { background: #f85149; }
.dot-yellow { background: #d29922; }
.dot-gray { background: #484f58; }
.log-line { font-size: 10px; color: #6e7681; padding: 2px 0; border-bottom: 1px solid #0d1117; word-break: break-all; line-height: 1.5; }
.log-line:hover { color: #8b949e; }
.godel-entry { padding: 6px 0; border-bottom: 1px solid #161b22; font-size: 11px; }
.godel-agent { color: #58a6ff; }
.godel-type { color: #d2a8ff; }
.godel-choice { color: #c9d1d9; margin-top: 2px; }
.wide { grid-column: 1 / -1; }
.belief-row { font-size: 11px; padding: 3px 0; color: #8b949e; }
.belief-key { color: #7ee787; }
.pulse { animation: pulse 2s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }
.footer { padding: 12px 24px; border-top: 1px solid #1a1f2e; font-size: 10px; color: #484f58; text-align: center; }

/* Insight sections — above-the-fold proof of thinking / improving / evolving */
.insight { padding: 0 24px 12px; }
.insight-section { border: 1px solid #1a1f2e; background: #0d1117; padding: 12px 14px; margin-top: 10px; }
.insight-section[hidden] { display: none; }
.insight-title { font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #6e7681; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: baseline; }
.insight-title .sub { font-size: 10px; color: #484f58; text-transform: none; letter-spacing: 0; }

/* Now Thinking */
.think-list { max-height: 140px; overflow-y: auto; }
.think-row { display: grid; grid-template-columns: 72px 1fr 70px; gap: 8px; padding: 4px 0; border-bottom: 1px solid #161b22; font-size: 11px; align-items: start; }
.think-row:last-child { border: none; }
.think-room { font-weight: 600; font-size: 10px; padding: 2px 6px; border-radius: 3px; text-align: center; letter-spacing: 1px; }
.room-thinking    { background: rgba(88,166,255,0.15);  color: #58a6ff; }
.room-improvement { background: rgba(63,185,80,0.15);   color: #3fb950; }
.room-godel       { background: rgba(210,168,255,0.15); color: #d2a8ff; }
.room-boardroom   { background: rgba(210,153,34,0.18);  color: #d29922; }
.think-body { color: #c9d1d9; line-height: 1.45; word-break: break-word; }
.think-body .agent { color: #58a6ff; font-weight: 600; margin-right: 6px; }
.think-time { color: #484f58; font-size: 10px; text-align: right; }
.sse-state { font-size: 9px; color: #484f58; }
.sse-state.live { color: #3fb950; }

/* Improvement ledger */
.ledger-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.ledger-pill { width: 10px; height: 18px; border-radius: 2px; position: relative; cursor: help; }
.ledger-pill.ok      { background: #3fb950; }
.ledger-pill.failed  { background: #f85149; opacity: 0.75; }
.ledger-pill.running { background: #d29922; animation: pulse 1.8s ease-in-out infinite; }
.ledger-totals { margin-left: auto; font-size: 10px; color: #8b949e; }
.ledger-totals .num { color: #e6edf3; font-weight: 600; }

/* Fitness leaderboard */
.fit-table { width: 100%; font-size: 11px; border-collapse: collapse; }
.fit-table th { font-weight: 500; color: #6e7681; font-size: 9px; text-align: left; padding: 4px 6px; letter-spacing: 1px; text-transform: uppercase; }
.fit-table td { padding: 4px 6px; border-top: 1px solid #161b22; vertical-align: middle; }
.fit-rank { color: #484f58; width: 22px; }
.fit-agent { color: #c9d1d9; font-weight: 500; }
.fit-score { width: 60px; text-align: right; color: #e6edf3; font-variant-numeric: tabular-nums; }
.fit-bar-wrap { width: 80px; height: 4px; background: #21262d; border-radius: 2px; overflow: hidden; }
.fit-bar { height: 100%; border-radius: 2px; }
.axes-heat { display: flex; gap: 2px; }
.axis-dot { width: 8px; height: 8px; border-radius: 1px; }
.fit-trend.up   { color: #3fb950; }
.fit-trend.dn   { color: #f85149; }
.fit-trend.flat { color: #6e7681; }

/* Selection events */
.sel-row { display: grid; grid-template-columns: 70px 1fr 80px; gap: 8px; padding: 4px 0; border-bottom: 1px solid #161b22; font-size: 11px; align-items: center; }
.sel-row:last-child { border: none; }
.sel-badge { font-size: 9px; letter-spacing: 1px; padding: 2px 6px; border-radius: 3px; font-weight: 600; text-align: center; }
.sel-badge.shadow     { background: rgba(110,118,129,0.2); color: #8b949e; }
.sel-badge.advisory   { background: rgba(210,153,34,0.2);  color: #d29922; }
.sel-badge.autonomous { background: rgba(248,81,73,0.2);   color: #f85149; }
.sel-event { color: #c9d1d9; }
.sel-event.retire { color: #f85149; }
.sel-event.spawn  { color: #3fb950; }
.sel-time { color: #484f58; text-align: right; font-size: 10px; }
.insight-empty { color: #484f58; font-size: 11px; padding: 6px 0; }
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>mind<span>X</span> — production diagnostics</h1>
    <div class="uptime" id="uptime">connecting...</div>
  </div>
  <div>
    <span class="status-badge" id="status-badge">...</span>
    <span class="pulse" id="pulse" style="color:#3fb950;margin-left:8px;font-size:8px;">&#9679;</span>
  </div>
</div>
<div class="insight">
  <section class="insight-section" id="sec-think" hidden>
    <div class="insight-title">
      <span>now thinking <span class="sub" id="think-stream-state">connecting...</span></span>
      <span class="sub">SSE /insight/thinking/live &middot; rooms: thinking &middot; improvement &middot; godel &middot; boardroom</span>
    </div>
    <div class="think-list" id="think-list"></div>
  </section>
  <section class="insight-section" id="sec-ledger" hidden>
    <div class="insight-title">
      <span>self-improvement ledger</span>
      <span class="sub">recent mastermind campaigns &middot; hover for directive</span>
    </div>
    <div class="ledger-row" id="ledger-row"></div>
  </section>
  <section class="insight-section" id="sec-fitness" hidden>
    <div class="insight-title">
      <span>per-agent fitness &middot; darwinian leaderboard</span>
      <span class="sub">weighted rollup of 7 axes &middot; /insight/fitness every 30s</span>
    </div>
    <div id="fit-body"></div>
  </section>
  <section class="insight-section" id="sec-selection" hidden>
    <div class="insight-title">
      <span>selection events</span>
      <span class="sub" id="sel-mode">mode: shadow</span>
    </div>
    <div id="sel-body"></div>
  </section>
</div>
<div class="grid" id="grid">
  <div class="card"><div class="card-title">loading</div><div class="metric">...</div></div>
</div>
<div class="footer">
  mindX autonomous multi-agent system &mdash; <span id="ts"></span> &mdash; auto-refresh 8s
</div>
<script>
const API = '/diagnostics/live';
let lastData = null;

function pct_bar(pct) {
  const cls = pct > 85 ? 'bar-red' : pct > 65 ? 'bar-yellow' : 'bar-green';
  return `<div class="bar-container"><div class="bar ${cls}" style="width:${pct}%"></div></div>`;
}

function short_addr(a) { return a ? a.slice(0,6)+'...'+a.slice(-4) : '?'; }

function render(d) {
  const s = d.system || {};
  const inf = d.inference || {};
  const v = d.vault || {};
  let html = '';

  // Row 1: System vitals
  html += `<div class="card"><div class="card-title">cpu</div><div class="metric">${s.cpu_percent||0}%</div>${pct_bar(s.cpu_percent||0)}</div>`;
  html += `<div class="card"><div class="card-title">memory</div><div class="metric">${s.memory_used_gb||0} <span style="font-size:14px;color:#6e7681">/ ${s.memory_total_gb||0} GB</span></div>${pct_bar(s.memory_percent||0)}</div>`;
  html += `<div class="card"><div class="card-title">disk</div><div class="metric">${s.disk_used_gb||0} <span style="font-size:14px;color:#6e7681">/ ${s.disk_total_gb||0} GB</span></div>${pct_bar(s.disk_percent||0)}</div>`;

  // Row 2: mindX stats
  html += `<div class="card"><div class="card-title">uptime</div><div class="metric">${d.uptime||'?'}</div><div class="metric-sm">service started ${new Date(Date.now()-d.uptime_seconds*1000).toLocaleString()}</div></div>`;
  html += `<div class="card"><div class="card-title">beliefs persisted</div><div class="metric">${d.beliefs?.count||0}</div><div class="metric-sm">identity mappings + learned knowledge</div></div>`;
  html += `<div class="card"><div class="card-title">memory records</div><div class="metric">${(d.memory?.stm_records||0).toLocaleString()}</div><div class="metric-sm">${d.memory?.agent_workspaces||0} agent workspaces</div></div>`;

  // Vault
  html += `<div class="card"><div class="card-title">bankon vault</div><div class="metric">${v.entries||0} <span style="font-size:14px;color:#6e7681">entries</span></div><div class="metric-sm">${v.cipher||'?'} &middot; ${v.kdf||'?'}</div></div>`;

  // Inference sources
  let src_html = '';
  for (const [name, info] of Object.entries(inf.sources||{})) {
    const dot = info.status==='available'?'dot-green':info.status==='degraded'?'dot-yellow':info.status==='unknown'?'dot-gray':'dot-red';
    const models = (info.models||[]).join(', ')||'';
    src_html += `<div class="source-row"><span><span class="dot ${dot}"></span>${name}</span><span style="color:#6e7681">${info.type} ${models?'('+models+')':''}</span></div>`;
  }
  html += `<div class="card"><div class="card-title">inference sources &mdash; ${inf.available||0}/${inf.total||0} available</div>${src_html||'<div style="color:#484f58">no sources</div>'}</div>`;

  // Agents
  let agent_html = '';
  for (const a of (d.agents||[])) {
    agent_html += `<div class="agent-row"><div><div class="agent-name">${a.entity_id}</div><div class="agent-role">${a.role}</div></div><div class="agent-addr">${short_addr(a.address)}</div></div>`;
  }
  html += `<div class="card"><div class="card-title">sovereign agents &mdash; ${(d.agents||[]).length} identities</div>${agent_html||'<div style="color:#484f58">no agents</div>'}</div>`;

  // Beliefs sample
  let belief_html = '';
  for (const b of (d.beliefs?.sample||[])) {
    belief_html += `<div class="belief-row"><span class="belief-key">${b.key}</span> &rarr; ${b.value}</div>`;
  }
  html += `<div class="card"><div class="card-title">belief system sample</div>${belief_html||'<div style="color:#484f58">empty</div>'}</div>`;

  // Godel choices
  let godel_html = '';
  for (const g of (d.godel_choices||[])) {
    godel_html += `<div class="godel-entry"><span class="godel-agent">${g.agent}</span> <span class="godel-type">${g.type}</span> <span style="color:#484f58">${g.timestamp?.slice(11,19)||''}</span><div class="godel-choice">${g.chosen}</div></div>`;
  }
  html += `<div class="card"><div class="card-title">recent g&ouml;del decisions</div>${godel_html||'<div style="color:#484f58">no decisions recorded yet</div>'}</div>`;

  // Logs
  let log_html = '';
  for (const l of (d.recent_logs||[])) { log_html += `<div class="log-line">${l.replace(/</g,'&lt;')}</div>`; }
  html += `<div class="card wide"><div class="card-title">recent activity log</div>${log_html||'<div style="color:#484f58">no logs</div>'}</div>`;

  document.getElementById('grid').innerHTML = html;
  document.getElementById('uptime').textContent = 'uptime ' + d.uptime + ' | ' + (d.agents||[]).length + ' agents | ' + (inf.available||0) + ' inference sources';
  document.getElementById('status-badge').textContent = d.system?.cpu_percent !== undefined ? 'LIVE' : 'DEGRADED';
  document.getElementById('status-badge').className = 'status-badge' + (d.system?.cpu_percent !== undefined ? '' : ' warn');
  document.getElementById('ts').textContent = d.timestamp || '';
}

async function refresh() {
  try {
    const r = await fetch(API);
    if (r.ok) { lastData = await r.json(); render(lastData); }
  } catch(e) {
    document.getElementById('status-badge').textContent = 'OFFLINE';
    document.getElementById('status-badge').className = 'status-badge warn';
  }
}

refresh();
setInterval(refresh, 8000);

// ── Insight sections — each loads independently, hides itself on fail ──

const ROOMS = {thinking:'room-thinking', improvement:'room-improvement', godel:'room-godel', boardroom:'room-boardroom'};
const thinkMax = 3;
let thinkBuf = [];

function escapeHtml(s){ return (s==null?'':String(s)).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function tshort(ts){ const d = new Date(ts*1000); return d.toTimeString().slice(0,8); }

function renderThink() {
  const el = document.getElementById('think-list');
  if (!thinkBuf.length) { el.innerHTML = '<div class="insight-empty">no thinking events yet</div>'; return; }
  el.innerHTML = thinkBuf.slice(-thinkMax).reverse().map(ev => {
    const roomCls = ROOMS[ev.room] || 'room-thinking';
    return `<div class="think-row">
      <div class="think-room ${roomCls}">${escapeHtml(ev.room||'')}</div>
      <div class="think-body"><span class="agent">${escapeHtml(ev.agent||'')}</span>${escapeHtml(ev.content||'')}</div>
      <div class="think-time">${tshort(ev.timestamp||(Date.now()/1000))}</div>
    </div>`;
  }).join('');
}

function connectThinkStream() {
  const state = document.getElementById('think-stream-state');
  const sec = document.getElementById('sec-think');
  try {
    const src = new EventSource('/insight/thinking/live');
    src.addEventListener('activity', e => {
      try {
        const ev = JSON.parse(e.data);
        thinkBuf.push(ev);
        if (thinkBuf.length > 20) thinkBuf = thinkBuf.slice(-20);
        sec.hidden = false;
        state.textContent = 'live';
        state.className = 'sub sse-state live';
        renderThink();
      } catch(_) {}
    });
    src.addEventListener('heartbeat', () => {
      state.textContent = 'live';
      state.className = 'sub sse-state live';
    });
    src.onerror = () => {
      state.textContent = 'reconnecting...';
      state.className = 'sub sse-state';
      // Fallback: try the polled endpoint once.
      fetch('/insight/dialogue/recent?room=thinking&limit=5').then(r => r.ok ? r.json() : null).then(d => {
        if (d && Array.isArray(d.events) && d.events.length) {
          thinkBuf = d.events.slice().reverse();
          sec.hidden = false;
          renderThink();
        }
      }).catch(() => {});
    };
  } catch(_) {
    sec.hidden = true;
  }
}

async function loadLedger() {
  const sec = document.getElementById('sec-ledger');
  try {
    const r = await fetch('/insight/improvement/summary?window=24h');
    if (!r.ok) throw new Error('http ' + r.status);
    const d = await r.json();
    if (d.fallback || d.status === 'warming_up') { sec.hidden = true; return; }
    const c24 = d.campaigns_24h || {total:0,succeeded:0,failed:0,running:0};
    const tl = await (await fetch('/insight/improvement/timeline?limit=50')).json().catch(()=>({campaigns:[]}));
    const campaigns = (tl.campaigns || []).slice(0, 40);
    if (!campaigns.length && !c24.total) { sec.hidden = true; return; }
    sec.hidden = false;
    const pills = campaigns.map(c => {
      const status = (c.overall_campaign_status||'').toUpperCase();
      const cls = status === 'SUCCESS' ? 'ok' : (status === 'IN_PROGRESS' || status === 'RUNNING') ? 'running' : 'failed';
      const title = `${escapeHtml(c.directive||'')} — ${escapeHtml(status)} :: ${escapeHtml(c.final_bdi_message||'')}`;
      return `<span class="ledger-pill ${cls}" title="${title}"></span>`;
    }).join('');
    const totals = `<span class="ledger-totals">24h: <span class="num" style="color:#3fb950">${c24.succeeded}</span> ok &middot; <span class="num" style="color:#d29922">${c24.running}</span> running &middot; <span class="num" style="color:#f85149">${c24.failed}</span> fail &middot; <span class="num">${c24.total}</span> total</span>`;
    document.getElementById('ledger-row').innerHTML = pills + totals;
  } catch(_) {
    sec.hidden = true;
  }
}

function heatColor(v) {
  if (v >= 80) return '#3fb950';
  if (v >= 60) return '#7ee787';
  if (v >= 45) return '#d2a8ff';
  if (v >= 30) return '#d29922';
  return '#f85149';
}
function barColor(v){ return v>=70?'#3fb950':v>=50?'#58a6ff':v>=30?'#d29922':'#f85149'; }

async function loadFitness() {
  const sec = document.getElementById('sec-fitness');
  try {
    const r = await fetch('/insight/fitness');
    if (!r.ok) throw new Error('http ' + r.status);
    const d = await r.json();
    if (d.fallback) { sec.hidden = true; return; }
    const agents = (d.agents || []).slice(0, 8);
    if (!agents.length) { sec.hidden = true; return; }
    sec.hidden = false;
    const axisOrder = ['campaign_success','trace_reliability','latency_score','consensus_alignment','reputation_momentum','learning_velocity','godel_selection_rate'];
    const rows = agents.map((a,i) => {
      const bar = `<div class="fit-bar-wrap"><div class="fit-bar" style="width:${a.fitness}%;background:${barColor(a.fitness)}"></div></div>`;
      const dots = axisOrder.map(k => {
        const v = (a.axes||{})[k] ?? 50;
        return `<div class="axis-dot" title="${k}: ${v.toFixed(0)}" style="background:${heatColor(v)}"></div>`;
      }).join('');
      const td = a.trend_7d || 0;
      const tcls = td > 1 ? 'up' : td < -1 ? 'dn' : 'flat';
      const ts = td > 0 ? `+${td.toFixed(1)}` : td.toFixed(1);
      return `<tr>
        <td class="fit-rank">${i+1}</td>
        <td class="fit-agent">${escapeHtml(a.agent_id||'')}</td>
        <td class="fit-score">${a.fitness.toFixed(1)}</td>
        <td>${bar}</td>
        <td><div class="axes-heat">${dots}</div></td>
        <td class="fit-trend ${tcls}">${ts}</td>
      </tr>`;
    }).join('');
    document.getElementById('fit-body').innerHTML = `<table class="fit-table">
      <thead><tr><th></th><th>agent</th><th style="text-align:right">fit</th><th></th><th>axes</th><th>&Delta;7d</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  } catch(_) {
    sec.hidden = true;
  }
}

async function loadSelection() {
  const sec = document.getElementById('sec-selection');
  try {
    const r = await fetch('/insight/selection/events?limit=5');
    if (!r.ok) throw new Error('http ' + r.status);
    const d = await r.json();
    if (d.fallback) { sec.hidden = true; return; }
    document.getElementById('sel-mode').textContent = 'mode: ' + (d.mode || 'shadow');
    const evs = d.events || [];
    if (!evs.length) {
      sec.hidden = false;
      document.getElementById('sel-body').innerHTML = '<div class="insight-empty">no selection proposals yet — aggregator still warming up or no agents above/below thresholds</div>';
      return;
    }
    sec.hidden = false;
    const rows = evs.map(e => {
      const m = (e.mode||'shadow').toLowerCase();
      const ev = (e.event||'').toLowerCase();
      const evClass = ev.indexOf('retire') >= 0 ? 'retire' : ev.indexOf('spawn') >= 0 ? 'spawn' : '';
      const t = e.timestamp_utc ? e.timestamp_utc.slice(11,19) : '';
      const extra = e.mutation ? ` &middot; mutation: ${escapeHtml(e.mutation)}` : (e.parent_agent_id ? ` &middot; parent: ${escapeHtml(e.parent_agent_id)}` : '');
      return `<div class="sel-row">
        <div class="sel-badge ${m}">${m.toUpperCase()}</div>
        <div><span class="sel-event ${evClass}">${escapeHtml(e.event||'')}</span> &middot; ${escapeHtml(e.agent_id||'')} &middot; fit ${(e.fitness_before||0).toFixed?(e.fitness_before||0).toFixed(1):e.fitness_before}${extra}</div>
        <div class="sel-time">${t}</div>
      </div>`;
    }).join('');
    document.getElementById('sel-body').innerHTML = rows;
  } catch(_) {
    sec.hidden = true;
  }
}

// Kick off insight sections. SSE reconnects itself; polled sections refresh on cadence.
connectThinkStream();
loadLedger();   setInterval(loadLedger,   60000);
loadFitness();  setInterval(loadFitness,  30000);
loadSelection();setInterval(loadSelection,60000);

</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def dashboard_root():
    """Public diagnostics dashboard — non-interactive, read-only."""
    return HTMLResponse(content=DASHBOARD_HTML)
