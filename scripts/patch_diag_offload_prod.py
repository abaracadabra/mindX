#!/usr/bin/env python
"""Offload all synchronous diagnostics file I/O onto a worker thread so the FastAPI
event loop never blocks mid-refresh (the cause of the diagnostics 'flapping' under
CPU load). Adds _diag_read_sync + _diag_stm_fallback_sync helpers and rewires
_diag_compute to call them via asyncio.to_thread. Idempotent-guarded; asserts each
anchor appears exactly once. Operates on the prod file path below."""
P = "/home/mindx/mindX/mindx_backend_service/main_service.py"
s = open(P).read()

if "_diag_read_sync" in s:
    print("already patched (found _diag_read_sync) — aborting")
    raise SystemExit(0)

# R1 — add the Gödel last-good global next to the actions one.
R1_OLD = '_diag_last_actions: list = []  # Last non-empty recent-actions (survives DB stalls)'
R1_NEW = R1_OLD + '\n_diag_last_godel: list = []    # Last non-empty Gödel choices (survives read stalls)'

# R2 — insert the two sync-read helpers before _diag_compute + widen its globals.
R2_OLD = '''async def _diag_compute():
    """Heavy diagnostics gather - run from the endpoint (cold cache only) or a
    background refresher, so the endpoint never blocks on it under CPU load."""
    global _diag_last_probe, _diag_cache, _diag_cache_ts'''
R2_NEW = '''def _diag_read_sync():
    """All synchronous diagnostics file I/O (beliefs, Gödel JSONL, agent registry,
    vault, runtime log, workspace count) gathered in ONE function so the caller can
    run it in a worker thread via asyncio.to_thread — keeping the FastAPI event loop
    free to serve while disk reads + JSON parsing happen off-loop."""
    out = {"beliefs_count": 0, "beliefs_sample": [], "godel": [], "agents": [],
           "vault": {}, "logs": [], "workspaces": 0}
    try:
        bp = PROJECT_ROOT / "data" / "memory" / "beliefs.json"
        if bp.exists():
            bd = json.loads(bp.read_text())
            out["beliefs_count"] = len(bd)
            for k, v in list(bd.items())[:8]:
                val = v.get("value", "")
                if isinstance(val, str) and len(val) > 50: val = val[:50] + "..."
                out["beliefs_sample"].append({"key": k, "value": val})
    except Exception as e: logger.debug(f"Diagnostics: beliefs read failed: {e}")
    try:
        wd = PROJECT_ROOT / "data" / "memory" / "agent_workspaces"
        out["workspaces"] = sum(1 for d_ in wd.iterdir() if d_.is_dir()) if wd.exists() else 0
    except Exception: pass
    try:
        gp = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
        if gp.exists():
            lines = [l for l in gp.read_text().strip().split("\\n") if l.strip()]
            for l in lines[-10:]:
                try:
                    g = json.loads(l)
                    out["godel"].append({"timestamp": g.get("timestamp_utc", g.get("timestamp","")), "agent": g.get("source_agent","?"), "type": g.get("choice_type",""), "chosen": str(g.get("chosen_option", g.get("chosen","")))[:100], "rationale": str(g.get("rationale",""))[:80], "outcome": str(g.get("outcome",""))[:40]})
                except Exception: pass
            out["godel"].reverse()
    except Exception as e: logger.debug(f"Diagnostics: godel choices read failed: {e}")
    try:
        rp = PROJECT_ROOT / "data" / "identity" / "production_registry.json"
        amp = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
        agent_tiers = {}
        if amp.exists():
            for aid, ad in json.loads(amp.read_text()).get("agents", {}).items():
                agent_tiers[aid] = ad.get("verification_tier", 0)
        if rp.exists():
            for a in json.loads(rp.read_text()).get("agents", []):
                eid = a["entity_id"]
                out["agents"].append({"entity_id": eid, "address": a["address"], "role": a.get("role",""), "verification_tier": agent_tiers.get(eid, 1)})
    except Exception as e: logger.debug(f"Diagnostics: agent registry read failed: {e}")
    try:
        from mindx_backend_service.bankon_vault.vault import BankonVault
        vi = BankonVault().info(); vi.pop("vault_dir", None); out["vault"] = vi
    except Exception as e: logger.debug(f"Diagnostics: vault info failed: {e}")
    try:
        lp = PROJECT_ROOT / "data" / "logs" / "mindx_runtime.log"
        if lp.exists():
            for l in lp.read_text().strip().split("\\n")[-20:]:
                if "API_KEY" in l or "private_key" in l.lower() or "WALLET_PK" in l: continue
                out["logs"].append(l[:250])
            out["logs"].reverse()
    except Exception as e: logger.debug(f"Diagnostics: log read failed: {e}")
    return out


def _diag_stm_fallback_sync():
    """Filesystem STM count — only when pgvector is down. rglob over the (huge) STM
    tree MUST run in a worker thread, never on the event loop."""
    stm = 0; stm_by_agent = {}
    try:
        stm_path = PROJECT_ROOT / "data" / "memory" / "stm"
        if stm_path.exists():
            from collections import defaultdict as _ddict
            _counts = _ddict(int)
            for f in stm_path.rglob("*.memory.json"):
                parts = f.relative_to(stm_path).parts
                if parts:
                    _counts[parts[0]] += 1
                    stm += 1
            stm_by_agent = dict(sorted(_counts.items(), key=lambda x: -x[1]))
    except Exception:
        pass
    return stm, stm_by_agent


async def _diag_compute():
    """Heavy diagnostics gather - run from the endpoint (cold cache only) or a
    background refresher, so the endpoint never blocks on it under CPU load.
    All synchronous file I/O is offloaded to a worker thread (_diag_read_sync) so the
    event loop stays free to serve cached responses even mid-refresh."""
    global _diag_last_probe, _diag_cache, _diag_cache_ts, _diag_last_godel'''

# R3 — replace the inline beliefs block with the threaded read + unpacking.
R3_OLD = '''    # beliefs
    bp = PROJECT_ROOT / "data" / "memory" / "beliefs.json"
    bc, bs = 0, []
    try:
        if bp.exists():
            bd = json.loads(bp.read_text())
            bc = len(bd)
            for k, v in list(bd.items())[:8]:
                val = v.get("value", "")
                if isinstance(val, str) and len(val) > 50: val = val[:50] + "..."
                bs.append({"key": k, "value": val})
    except Exception as e: logger.debug(f"Diagnostics: beliefs read failed: {e}")
    # stm count'''
R3_NEW = '''    # ── All synchronous file I/O offloaded to a worker thread (never blocks the
    #    event loop, which is what kept serving responsive mid-refresh) ──
    _sync = await asyncio.to_thread(_diag_read_sync)
    bc, bs = _sync["beliefs_count"], _sync["beliefs_sample"]
    wsp = _sync["workspaces"]
    godel = _sync["godel"]
    agents = _sync["agents"]
    vault = _sync["vault"]
    logs = _sync["logs"]
    if godel:
        _diag_last_godel = godel
    elif _diag_last_godel:
        godel = _diag_last_godel
    # stm count'''

# R4 — replace fallback + workspaces + godel + registry inline blocks with threaded fallback.
R4_OLD = '''    # Filesystem fallback if DB returned nothing
    if stm == 0:
        try:
            stm_path = PROJECT_ROOT / "data" / "memory" / "stm"
            if stm_path.exists():
                from collections import defaultdict as _ddict
                _counts = _ddict(int)
                for f in stm_path.rglob("*.memory.json"):
                    parts = f.relative_to(stm_path).parts
                    if parts:
                        _counts[parts[0]] += 1
                        stm += 1
                stm_by_agent = dict(sorted(_counts.items(), key=lambda x: -x[1]))
        except Exception:
            pass
    wsp = sum(1 for d_ in (PROJECT_ROOT / "data" / "memory" / "agent_workspaces").iterdir() if d_.is_dir()) if (PROJECT_ROOT / "data" / "memory" / "agent_workspaces").exists() else 0
    # godel
    gp = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
    godel = []
    try:
        if gp.exists():
            lines = [l for l in gp.read_text().strip().split("\\n") if l.strip()]
            for l in lines[-10:]:
                try:
                    g = json.loads(l)
                    godel.append({"timestamp": g.get("timestamp_utc", g.get("timestamp","")), "agent": g.get("source_agent","?"), "type": g.get("choice_type",""), "chosen": str(g.get("chosen_option", g.get("chosen","")))[:100], "rationale": str(g.get("rationale",""))[:80], "outcome": str(g.get("outcome",""))[:40]})
                except Exception: pass
            godel.reverse()
    except Exception as e: logger.debug(f"Diagnostics: godel choices read failed: {e}")
    # registry
    rp = PROJECT_ROOT / "data" / "identity" / "production_registry.json"
    amp = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
    agents = []
    agent_tiers = {}
    try:
        if amp.exists():
            am = json.loads(amp.read_text())
            for aid, ad in am.get("agents", {}).items():
                agent_tiers[aid] = ad.get("verification_tier", 0)
    except Exception as e: logger.debug(f"Diagnostics: agent map read failed: {e}")
    try:
        if rp.exists():
            for a in json.loads(rp.read_text()).get("agents", []):
                eid = a["entity_id"]
                agents.append({"entity_id": eid, "address": a["address"], "role": a.get("role",""), "verification_tier": agent_tiers.get(eid, 1)})
    except Exception as e: logger.debug(f"Diagnostics: agent registry read failed: {e}")
    # inference (use cached summary'''
R4_NEW = '''    # Filesystem fallback if DB returned nothing — rglob over the (huge) STM tree
    # runs in a worker thread so it can never block the event loop.
    if stm == 0:
        stm, stm_by_agent = await asyncio.to_thread(_diag_stm_fallback_sync)
    # inference (use cached summary'''

# R5 — drop the inline vault + logs blocks (now in _diag_read_sync).
R5_OLD = '''    # vault
    vault = {}
    try:
        from mindx_backend_service.bankon_vault.vault import BankonVault
        v = BankonVault(); vault = v.info(); vault.pop("vault_dir", None)
    except Exception as e: logger.debug(f"Diagnostics: vault info failed: {e}")
    # logs
    lp = PROJECT_ROOT / "data" / "logs" / "mindx_runtime.log"
    logs = []
    try:
        if lp.exists():
            all_lines = lp.read_text().strip().split("\\n")
            for l in all_lines[-20:]:
                if "API_KEY" in l or "private_key" in l.lower() or "WALLET_PK" in l: continue
                logs.append(l[:250])
            logs.reverse()
    except Exception as e: logger.debug(f"Diagnostics: log read failed: {e}")
    # Load dojo and boardroom data'''
R5_NEW = '''    # (vault + recent logs now come from _diag_read_sync, off the event loop)
    # Load dojo and boardroom data'''

pairs = [("R1", R1_OLD, R1_NEW), ("R2", R2_OLD, R2_NEW), ("R3", R3_OLD, R3_NEW),
         ("R4", R4_OLD, R4_NEW), ("R5", R5_OLD, R5_NEW)]
for name, old, _new in pairs:
    n = s.count(old)
    assert n == 1, f"anchor {name} count={n} (expected 1) — aborting, no changes written"
for name, old, new in pairs:
    s = s.replace(old, new, 1)
open(P, "w").write(s)
print("patched: diagnostics file I/O offloaded to worker thread (_diag_read_sync + fallback)")
