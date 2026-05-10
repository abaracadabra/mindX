"""
marketing_routes — FastAPI surface for the marketing Counsellor cabinet.

Routes:
  GET /marketing/status       — orchestrator + 5 sub-agent health
  GET /marketing/campaigns    — recent campaign decisions (from catalogue)
  GET /marketing/brand_code   — current loaded brand-code (read-only)
  GET /marketing/geo          — last GEO probe rollup
  GET /marketing/identity     — on-chain identity binding status

All routes accept `?h=true` (or `Accept: text/plain`) and return a fixed-width
plain-text rendering via `text_render` primitives. JSON is the default when
the parameter is absent.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from starlette.responses import PlainTextResponse


router = APIRouter(prefix="/marketing", tags=["marketing"])


# ── helpers ────────────────────────────────────────────────────────────────


def _data_root() -> Path:
    try:
        from utils.config import PROJECT_ROOT  # type: ignore
        return Path(PROJECT_ROOT) / "data"
    except Exception:
        return Path(__file__).resolve().parents[1] / "data"


def _wants_text(request: Request) -> bool:
    try:
        from mindx_backend_service import text_render  # type: ignore
        return text_render.wants_text(request)
    except Exception:
        h = (request.query_params.get("h") or "").lower()
        return h in {"1", "true", "yes", "y", "on"}


def _kv(d: Dict[str, Any], label_width: int = 22) -> str:
    try:
        from mindx_backend_service.text_render import render_kv  # type: ignore
        return render_kv(d, label_width=label_width)
    except Exception:
        return "\n".join(f"{k.ljust(label_width)}  {v}" for k, v in d.items()) + "\n"


def _table(rows: List[Dict[str, Any]], columns: List[tuple]) -> str:
    try:
        from mindx_backend_service.text_render import render_table  # type: ignore
        return render_table(rows, columns)
    except Exception:
        if not rows:
            return "(none)\n"
        header = "  ".join(c[0] for c in columns) + "\n"
        body = "\n".join(
            "  ".join(str(r.get(c[1], "")) for c in columns) for r in rows
        )
        return header + body + "\n"


def _read_recent_marketing_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Tail data/logs/catalogue_events.jsonl for marketing.* events."""
    path = _data_root() / "logs" / "catalogue_events.jsonl"
    if not path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with path.open("rb") as fh:
            try:
                fh.seek(0, 2)
                size = fh.tell()
                read_chunk = min(size, 1024 * 1024)
                fh.seek(size - read_chunk)
                tail = fh.read().decode("utf-8", errors="ignore")
            except Exception:
                tail = path.read_text(encoding="utf-8", errors="ignore")
        for line in tail.splitlines()[::-1]:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except Exception:
                continue
            kind = evt.get("kind") or ""
            if isinstance(kind, str) and kind.startswith("marketing."):
                out.append(evt)
                if len(out) >= limit:
                    break
    except Exception:
        return []
    return out


def _orchestrator_status() -> Optional[Dict[str, Any]]:
    """Return MarketingaAgent status if instantiated; None otherwise.

    We deliberately do NOT instantiate the orchestrator from the route —
    that would require LLM caller wiring, etc. The orchestrator is created
    by the application's bootstrap path; here we only inspect.
    """
    try:
        from agents.marketing.marketinga_agent import MarketingaAgent  # type: ignore
        inst = MarketingaAgent._instance  # accessing the singleton handle
        if inst is None:
            return None
        return inst.status()
    except Exception:
        return None


def _read_recent_boardroom_sessions(limit: int = 50) -> Dict[str, Any]:
    """Tail data/governance/boardroom_sessions.jsonl. Returns {id: session}."""
    path = _data_root() / "governance" / "boardroom_sessions.jsonl"
    out: Dict[str, Any] = {}
    if not path.is_file():
        return out
    try:
        with path.open("rb") as fh:
            try:
                fh.seek(0, 2)
                size = fh.tell()
                read_chunk = min(size, 1024 * 1024)
                fh.seek(size - read_chunk)
                tail = fh.read().decode("utf-8", errors="ignore")
            except Exception:
                tail = path.read_text(encoding="utf-8", errors="ignore")
        for line in tail.splitlines()[-limit * 2:]:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            sid = rec.get("session_id")
            if sid:
                out[sid] = rec
    except Exception:
        return {}
    return out


def _read_brand_code() -> Dict[str, Any]:
    root = _data_root() / "brand_code"
    out: Dict[str, Any] = {"root": str(root), "files": {}}
    if not root.is_dir():
        out["error"] = "brand_code root missing"
        return out
    try:
        forbidden = json.loads((root / "forbidden_terms.json").read_text(encoding="utf-8"))
        out["files"]["forbidden_terms.json"] = {
            "version": forbidden.get("version"),
            "deny_pattern_count": len(forbidden.get("deny_patterns") or []),
            "soft_warn_pattern_count": len(forbidden.get("soft_warn_patterns") or []),
        }
    except Exception as exc:
        out["files"]["forbidden_terms.json"] = {"error": repr(exc)}
    try:
        comp = json.loads((root / "competitor_map.json").read_text(encoding="utf-8"))
        out["files"]["competitor_map.json"] = {
            "version": comp.get("version"),
            "competitors": list((comp.get("competitors") or {}).keys()),
        }
    except Exception as exc:
        out["files"]["competitor_map.json"] = {"error": repr(exc)}
    for name in ("voice.md", "regulatory_constraints.md"):
        p = root / name
        out["files"][name] = {"exists": p.is_file(), "bytes": p.stat().st_size if p.is_file() else 0}
    pos = root / "positioning"
    out["files"]["positioning"] = {
        "pillars.md": (pos / "pillars.md").is_file(),
        "icp_segments.md": (pos / "icp_segments.md").is_file(),
    }
    onboarding = root / "onboarding"
    out["files"]["onboarding"] = sorted(p.name for p in onboarding.glob("*.md")) if onboarding.is_dir() else []
    return out


def _identity_status() -> Dict[str, Any]:
    import os
    addrs = {
        "tessera": os.environ.get("MARKETING_TESSERA_ADDR"),
        "censura": os.environ.get("MARKETING_CENSURA_ADDR"),
        "agent_registry": os.environ.get("MARKETING_AGENT_REGISTRY_ADDR"),
        "bankon_subname_registrar": os.environ.get("MARKETING_BANKON_REGISTRAR_ADDR"),
        "inft_7857": os.environ.get("MARKETING_INFT_7857_ADDR"),
        "marketing_attribution_receipt": os.environ.get("MARKETING_ATTRIBUTION_RECEIPT_ADDR"),
        "marketing_treasury": os.environ.get("MARKETING_TREASURY_ADDR"),
    }
    bound = {k: bool(v and v != "0x0000000000000000000000000000000000000000") for k, v in addrs.items()}
    pending = [k for k, v in bound.items() if not v]
    return {
        "addresses": addrs,
        "bound": bound,
        "pending": pending,
        "operator_command_to_bind": "python -m agents.marketing.onchain.bind_identity --execute",
        "computed_at": time.time(),
    }


# ── routes ─────────────────────────────────────────────────────────────────


_DEFAULT_SOLDIER_MAPPING = [
    {"soldier_id": "ceo",            "skill_name": "brief_composition_and_signing", "weight": 0.0, "hbr_layer": -1},
    {"soldier_id": "cpo_product",    "skill_name": "content_drafting",              "weight": 1.0, "hbr_layer": 1},
    {"soldier_id": "cto_technology", "skill_name": "experimentation",               "weight": 1.0, "hbr_layer": 2},
    {"soldier_id": "coo_operations", "skill_name": "distribution",                  "weight": 1.0, "hbr_layer": 3},
    {"soldier_id": "cfo_finance",    "skill_name": "reporting_and_treasury",        "weight": 1.0, "hbr_layer": 4},
    {"soldier_id": "ciso_security",  "skill_name": "identity_and_voice_gate",       "weight": 1.2, "hbr_layer": 0},
    {"soldier_id": "clo_legal",      "skill_name": "regulatory_and_competitor",     "weight": 0.8, "hbr_layer": 0},
    {"soldier_id": "cro_risk",       "skill_name": "spend_risk_and_hard_stop",      "weight": 1.2, "hbr_layer": 0},
]


@router.get("/status", summary="Marketing Counsellor cabinet health (8-soldier map)")
async def marketing_status(request: Request):
    orch = _orchestrator_status()
    soldier_skills = (orch or {}).get("soldier_skills") or _DEFAULT_SOLDIER_MAPPING
    payload = {
        "orchestrator": orch or {"agent_id": "marketinga", "state": "NOT_INSTANTIATED"},
        "soldier_skills": soldier_skills,
        "computed_at": time.time(),
    }
    if not _wants_text(request):
        return payload
    head = _kv({
        "orchestrator": payload["orchestrator"].get("agent_id", "marketinga"),
        "did": payload["orchestrator"].get("did", "did:pythai:marketinga"),
        "ens": payload["orchestrator"].get("ens", "marketinga.bankon.eth"),
        "state": payload["orchestrator"].get("state") or "ACTIVE",
        "cycles": payload["orchestrator"].get("cycle_count", 0),
        "voice_register": payload["orchestrator"].get("voice_register", "cypherpunk"),
    })
    rows = [
        {
            "soldier": s["soldier_id"],
            "weight": f"{s.get('weight', 1.0):.1f}",
            "skill": s.get("skill_name", ""),
            "hbr": str(s.get("hbr_layer", "")),
        }
        for s in soldier_skills
    ]
    body = _table(
        rows,
        [
            ("soldier", "soldier", None),
            ("weight", "weight", None),
            ("skill", "skill", None),
            ("hbr", "hbr", None),
        ],
    )
    return PlainTextResponse(head + "\n" + body, media_type="text/plain; charset=utf-8")


@router.get("/campaigns", summary="Recent marketing campaign decisions from catalogue")
async def marketing_campaigns(request: Request, limit: int = 50):
    events = _read_recent_marketing_events(limit=max(1, min(500, int(limit))))
    payload = {"events": events, "count": len(events), "computed_at": time.time()}
    if not _wants_text(request):
        return payload
    rows = []
    for e in events:
        p = e.get("payload") or {}
        rows.append({
            "ts": e.get("ts"),
            "kind": e.get("kind"),
            "campaign_id": p.get("campaign_id") or "",
            "status": p.get("status") or "",
            "pillar": p.get("pillar") or "",
            "ring": p.get("audience_ring") or "",
        })
    text = _kv({"events": len(rows)}) + "\n" + _table(
        rows,
        [
            ("ts", "ts", None),
            ("kind", "kind", None),
            ("campaign", "campaign_id", None),
            ("status", "status", None),
            ("pillar", "pillar", None),
            ("ring", "ring", None),
        ],
    )
    return PlainTextResponse(text, media_type="text/plain; charset=utf-8")


@router.get("/brand_code", summary="Current loaded brand-code (read-only)")
async def marketing_brand_code(request: Request):
    payload = _read_brand_code()
    payload["computed_at"] = time.time()
    if not _wants_text(request):
        return payload
    flat: Dict[str, Any] = {"root": payload["root"]}
    for fname, meta in (payload.get("files") or {}).items():
        if isinstance(meta, dict):
            flat[fname] = json.dumps(meta, default=str)
        else:
            flat[fname] = meta
    return PlainTextResponse(_kv(flat), media_type="text/plain; charset=utf-8")


@router.get("/geo", summary="Last GEO probe rollup (share-of-voice across LLM engines)")
async def marketing_geo(request: Request):
    events = _read_recent_marketing_events(limit=200)
    geo = next((e for e in events if e.get("kind") == "marketing.geo_probe"), None)
    if geo is None:
        payload = {
            "rollup": None,
            "note": "no marketing.geo_probe events recorded yet",
            "computed_at": time.time(),
        }
    else:
        payload = {"rollup": geo.get("payload"), "ts": geo.get("ts"), "computed_at": time.time()}
    if not _wants_text(request):
        return payload
    if geo is None:
        return PlainTextResponse(
            _kv({"rollup": "(none)", "note": payload["note"]}),
            media_type="text/plain; charset=utf-8",
        )
    sov = (geo.get("payload") or {}).get("share_of_voice") or {}
    rows = [{"term": t, "share": f"{v:.2%}"} for t, v in sov.items()]
    text = _kv({
        "ts": geo.get("ts"),
        "diminished_share": (geo.get("payload") or {}).get("diminished_share"),
        "error_share": (geo.get("payload") or {}).get("error_share"),
    }) + "\n" + _table(rows, [("term", "term", None), ("share", "share", None)])
    return PlainTextResponse(text, media_type="text/plain; charset=utf-8")


@router.get("/session/{boardroom_session_id}", summary="Join a BoardroomSession with the resulting MarketingAttributionReceipt + soldier skill outputs")
async def marketing_session(request: Request, boardroom_session_id: str):
    sessions = _read_recent_boardroom_sessions(limit=200)
    session = sessions.get(boardroom_session_id)
    events = _read_recent_marketing_events(limit=500)
    matched_events = [
        e for e in events
        if (e.get("payload") or {}).get("boardroom_session_id") == boardroom_session_id
    ]
    payload = {
        "boardroom_session_id": boardroom_session_id,
        "boardroom_session": session,
        "marketing_events": matched_events,
        "computed_at": time.time(),
    }
    if not _wants_text(request):
        return payload
    head = _kv({
        "session_id": boardroom_session_id,
        "outcome": (session or {}).get("outcome", "(unknown)"),
        "weighted_score": (session or {}).get("weighted_score", "—"),
        "events": len(matched_events),
    })
    rows = [
        {
            "ts": e.get("ts"),
            "kind": e.get("kind"),
            "actor": e.get("actor"),
            "status": (e.get("payload") or {}).get("status", ""),
        }
        for e in matched_events
    ]
    body = _table(
        rows,
        [
            ("ts", "ts", None),
            ("kind", "kind", None),
            ("actor", "actor", None),
            ("status", "status", None),
        ],
    )
    return PlainTextResponse(head + "\n" + body, media_type="text/plain; charset=utf-8")


@router.get("/identity", summary="On-chain identity binding status (Tessera/ENS/AgentRegistry/iNFT)")
async def marketing_identity(request: Request):
    payload = _identity_status()
    if not _wants_text(request):
        return payload
    flat: Dict[str, Any] = {}
    for k, v in payload["bound"].items():
        flat[k] = "BOUND" if v else "PENDING"
    flat["pending_count"] = len(payload["pending"])
    flat["operator_cmd"] = payload["operator_command_to_bind"]
    return PlainTextResponse(_kv(flat), media_type="text/plain; charset=utf-8")


__all__ = ["router"]
