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
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def dashboard_root():
    """Public diagnostics dashboard — non-interactive, read-only."""
    return HTMLResponse(content=DASHBOARD_HTML)
