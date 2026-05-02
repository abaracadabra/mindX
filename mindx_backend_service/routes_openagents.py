"""
routes_openagents — insight endpoints for the Open Agents 8-module dashboard.

Reads the catalogue stream (data/logs/catalogue_events.jsonl), the
deployed-contracts files (openagents/deployments/{galileo,sepolia}.json),
and a few module-specific log files. Surfaces the eight panels:

  GET /insight/openagents/inft         iNFT_7857 (Module 1)
  GET /insight/openagents/compute      0G Compute calls + attestations (Module 2)
  GET /insight/openagents/storage      0G Storage uploads (Module 2)
  GET /insight/openagents/conclave     Conclave sessions + bond events (Module 3)
  GET /insight/openagents/ens          BANKON v1 subname issuances (Module 4)
  GET /insight/openagents/keeperhub    KH bridge settlements (Module 5)
  GET /insight/openagents/uniswap      Uniswap trader cycles (Module 6)
  GET /insight/openagents/thot         THOT.commit() memory events (Module 7)
  GET /insight/openagents/agentregistry ERC-8004 registrations (Module 8)
  GET /insight/openagents/summary      one-shot rollup for the dashboard hero

All endpoints respect ?h=true / Accept: text/plain so terminals can curl them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["openagents"])

CATALOGUE_LOG = PROJECT_ROOT / "data" / "logs" / "catalogue_events.jsonl"
GALILEO_DEPLOYMENTS = PROJECT_ROOT / "openagents" / "deployments" / "galileo.json"
ARISTOTLE_DEPLOYMENTS = PROJECT_ROOT / "openagents" / "deployments" / "aristotle.json"   # 0G mainnet
SEPOLIA_DEPLOYMENTS = PROJECT_ROOT / "openagents" / "deployments" / "sepolia.json"
CONCLAVE_DEPLOYMENTS = PROJECT_ROOT / "openagents" / "conclave" / "deployments" / "default.json"
UNISWAP_LOG = PROJECT_ROOT / "data" / "logs" / "uniswap_decisions.jsonl"


def _tail_catalogue(predicate, limit: int = 50, max_bytes: int = 4 * 1024 * 1024) -> List[Dict[str, Any]]:
    """Tail the catalogue jsonl, return up to `limit` events matching `predicate`."""
    if not CATALOGUE_LOG.exists():
        return []
    try:
        sz = CATALOGUE_LOG.stat().st_size
        with CATALOGUE_LOG.open("rb") as fh:
            if sz > max_bytes:
                fh.seek(sz - max_bytes)
                fh.readline()  # discard partial leading line
            raw = fh.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"catalogue tail failed: {e}")
        return []

    out: List[Dict[str, Any]] = []
    # Walk from newest to oldest
    for line in reversed(raw.splitlines()):
        if not line.strip():
            continue
        try:
            evt = json.loads(line)
        except Exception:
            continue
        if predicate(evt):
            out.append(evt)
            if len(out) >= limit:
                break
    return out


def _maybe_text(request: Request, payload: Dict[str, Any], route_path: str) -> Any:
    """Tiny shim — defer to the project's text_render if available, else JSON."""
    try:
        from mindx_backend_service.text_render import _maybe_h_text  # type: ignore
        return _maybe_h_text(request, payload, route_path=route_path)
    except Exception:
        return payload


def _load_deployments(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


# --------------------------------------------------------------------- #
# 0G Compute
# --------------------------------------------------------------------- #

@router.get("/insight/openagents/compute", summary="Recent 0G Compute calls + attestations")
async def insight_compute(request: Request, limit: int = 25):
    def pred(e):
        if e.get("kind") not in ("tool.invoke", "tool.result"):
            return False
        p = e.get("payload") or {}
        actor = e.get("actor", "")
        return (
            actor in ("zerog_handler", "keeperhub_bridge", "demo_agent")
            and (p.get("attestation") or p.get("model", "").startswith("zerog/"))
        )
    events = _tail_catalogue(pred, limit=limit)
    out = []
    for e in events:
        p = e.get("payload") or {}
        out.append({
            "ts": e.get("ts"),
            "actor": e.get("actor"),
            "model": p.get("model"),
            "attestation": p.get("attestation"),
            "backend": p.get("backend") or p.get("serving_backend"),
            "amount_usdc": p.get("amount_usdc"),
            "endpoint": p.get("endpoint"),
        })
    return _maybe_text(
        request,
        {"calls": out, "count": len(out)},
        route_path="/insight/openagents/compute",
    )


# --------------------------------------------------------------------- #
# 0G Storage
# --------------------------------------------------------------------- #

@router.get("/insight/openagents/storage", summary="Recent 0G Storage uploads")
async def insight_storage(request: Request, limit: int = 25):
    def pred(e):
        if e.get("kind") not in ("memory.offload", "tool.invoke"):
            return False
        p = e.get("payload") or {}
        # Either explicit zerog provider, or a memory.offload that recorded a 0g uri
        return (
            p.get("provider") == "zerog"
            or "0g://" in str(p.get("uri", ""))
            or p.get("storage_uri", "").startswith("0g://")
        )
    events = _tail_catalogue(pred, limit=limit)
    out = []
    for e in events:
        p = e.get("payload") or {}
        out.append({
            "ts": e.get("ts"),
            "root": p.get("root") or p.get("content_root"),
            "uri": p.get("uri") or p.get("storage_uri"),
            "tx_hash": p.get("tx_hash"),
            "size_bytes": p.get("size_bytes"),
            "actor": e.get("actor"),
        })
    return _maybe_text(
        request,
        {"uploads": out, "count": len(out)},
        route_path="/insight/openagents/storage",
    )


# --------------------------------------------------------------------- #
# iNFT (deployed contract + recent mints)
# --------------------------------------------------------------------- #

@router.get("/insight/openagents/inft", summary="Deployed iNFT_7857 + recent mints")
async def insight_inft(request: Request, limit: int = 10):
    deploy = _load_deployments(GALILEO_DEPLOYMENTS)
    inft = deploy.get("contracts", {}).get("iNFT_7857", {}) if deploy else {}
    dsreg = deploy.get("contracts", {}).get("DatasetRegistry", {}) if deploy else {}

    def pred(e):
        p = e.get("payload") or {}
        return e.get("actor") == "demo_agent" and (
            p.get("token_id") is not None or p.get("contract") == inft.get("address")
        )
    mints = _tail_catalogue(pred, limit=limit)
    return _maybe_text(
        request,
        {
            "network":           deploy.get("network"),
            "chain_id":          deploy.get("chainId"),
            "explorer":          deploy.get("explorer"),
            "iNFT_7857":         inft,
            "DatasetRegistry":   dsreg,
            "deployed_at":       deploy.get("deployed_at"),
            "recent_mints":      mints,
            "recent_mint_count": len(mints),
        },
        route_path="/insight/openagents/inft",
    )


# --------------------------------------------------------------------- #
# KeeperHub bridge
# --------------------------------------------------------------------- #

@router.get("/insight/openagents/keeperhub", summary="Recent KeeperHub × AgenticPlace settlements")
async def insight_keeperhub(request: Request, limit: int = 25):
    def pred(e):
        return e.get("actor") == "keeperhub_bridge"
    events = _tail_catalogue(pred, limit=limit)
    out = []
    revenue = 0.0
    for e in events:
        p = e.get("payload") or {}
        amt = p.get("amount_usdc") or 0
        try:
            revenue += float(amt)
        except Exception:
            pass
        out.append({
            "ts": e.get("ts"),
            "direction": p.get("direction"),
            "endpoint": p.get("endpoint") or p.get("workflow_id"),
            "amount_usdc": amt,
            "tx_hash": p.get("tx_hash"),
        })
    return _maybe_text(
        request,
        {
            "settlements": out,
            "count": len(out),
            "total_usdc": round(revenue, 6),
        },
        route_path="/insight/openagents/keeperhub",
    )


# --------------------------------------------------------------------- #
# ENS subnames
# --------------------------------------------------------------------- #

@router.get("/insight/openagents/ens", summary="bankon.eth subname issuances")
async def insight_ens(request: Request, limit: int = 25):
    deploy = _load_deployments(SEPOLIA_DEPLOYMENTS)
    registrar = deploy.get("contracts", {}).get("BankonAgentRegistrar", {}) if deploy else {}

    def pred(e):
        return e.get("actor") in ("subdomain_issuer", "id_manager_agent") and e.get("kind") == "agent.interact"
    events = _tail_catalogue(pred, limit=limit)
    out = []
    for e in events:
        p = e.get("payload") or {}
        if p.get("subname") or p.get("agent_id"):
            out.append({
                "ts": e.get("ts"),
                "agent_id": p.get("agent_id"),
                "subname": p.get("subname"),
                "wallet": p.get("wallet"),
                "tx_hash": p.get("tx_hash"),
                "explorer": p.get("explorer"),
            })

    # Live count from chain (best-effort, optional)
    total_registered: Optional[int] = None
    try:
        from openagents.ens.subdomain_issuer import get_default_issuer
        issuer = await get_default_issuer()
        if issuer is not None:
            total_registered = issuer.total_registered()
    except Exception as e:
        logger.debug(f"ENS live count unavailable: {e}")

    return _maybe_text(
        request,
        {
            "network":          deploy.get("network"),
            "explorer":         deploy.get("explorer"),
            "parent_name":      deploy.get("parent_name"),
            "registrar":        registrar,
            "recent_issuances": out,
            "total_registered_onchain": total_registered,
        },
        route_path="/insight/openagents/ens",
    )


# --------------------------------------------------------------------- #
# Conclave (Gensyn track)
# --------------------------------------------------------------------- #

@router.get("/insight/openagents/conclave", summary="Conclave sessions + bond events")
async def insight_conclave(request: Request, limit: int = 20):
    deploy = _load_deployments(CONCLAVE_DEPLOYMENTS)
    contracts = deploy.get("contracts", {}) if deploy else {}

    def pred(e):
        return e.get("actor") in ("conclave", "conclave_runtime", "mindx_boardroom_adapter")
    events = _tail_catalogue(pred, limit=limit)
    out = []
    for e in events:
        p = e.get("payload") or {}
        out.append({
            "ts": e.get("ts"),
            "kind": e.get("kind"),
            "session_id": p.get("session_id") or p.get("sessionId"),
            "title": p.get("title"),
            "members": p.get("members") or p.get("member_count"),
            "router": p.get("router"),
        })
    return _maybe_text(
        request,
        {
            "network":      deploy.get("network"),
            "explorer":     deploy.get("explorer"),
            "Conclave":     contracts.get("Conclave", {}),
            "ConclaveBond": contracts.get("ConclaveBond", {}),
            "recent_sessions": out,
        },
        route_path="/insight/openagents/conclave",
    )


# --------------------------------------------------------------------- #
# Uniswap V4 trader
# --------------------------------------------------------------------- #

@router.get("/insight/openagents/uniswap", summary="Uniswap V4 trader cycles + decisions")
async def insight_uniswap(request: Request, limit: int = 20):
    rows: List[Dict[str, Any]] = []
    if UNISWAP_LOG.exists():
        try:
            sz = UNISWAP_LOG.stat().st_size
            with UNISWAP_LOG.open("rb") as fh:
                if sz > 1_000_000:
                    fh.seek(sz - 1_000_000)
                    fh.readline()
                raw = fh.read().decode("utf-8", errors="ignore")
            for line in reversed(raw.splitlines()):
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
                if len(rows) >= limit:
                    break
        except Exception as e:
            logger.warning(f"uniswap log tail failed: {e}")

    quote = sum(1 for r in rows if r.get("action") == "quote")
    swap  = sum(1 for r in rows if r.get("action") == "swap")
    hold  = sum(1 for r in rows if r.get("action") == "hold")
    executed = sum(1 for r in rows if r.get("executed"))
    return _maybe_text(
        request,
        {
            "log": str(UNISWAP_LOG),
            "cycles_logged": len(rows),
            "quote_count":   quote,
            "swap_count":    swap,
            "hold_count":    hold,
            "executed":      executed,
            "recent": [{
                "ts":         r.get("ts"),
                "cycle":      r.get("cycle"),
                "action":     r.get("action"),
                "executed":   r.get("executed"),
                "confidence": r.get("confidence"),
                "rationale":  (r.get("rationale") or "")[:120],
            } for r in rows],
        },
        route_path="/insight/openagents/uniswap",
    )


# --------------------------------------------------------------------- #
# THOT.commit() — memory anchoring (Module 7)
# --------------------------------------------------------------------- #

@router.get("/insight/openagents/thot", summary="THOT.commit() memory anchor events")
async def insight_thot(request: Request, limit: int = 20):
    galileo = _load_deployments(GALILEO_DEPLOYMENTS)
    aristotle = _load_deployments(ARISTOTLE_DEPLOYMENTS)
    thot_g = galileo.get("contracts", {}).get("THOT_v1", {}) if galileo else {}
    thot_a = aristotle.get("contracts", {}).get("THOT_v1", {}) if aristotle else {}

    def pred(e):
        return e.get("kind") == "memory.anchor" or (
            e.get("actor") in ("thot_v1", "demo_agent")
            and (e.get("payload") or {}).get("rootHash") is not None
        )
    events = _tail_catalogue(pred, limit=limit)
    out = []
    for e in events:
        p = e.get("payload") or {}
        out.append({
            "ts": e.get("ts"),
            "tokenId": p.get("tokenId") or p.get("token_id"),
            "rootHash": p.get("rootHash") or p.get("root_hash") or p.get("root"),
            "chatID": p.get("chatID") or p.get("chat_id") or p.get("attestation"),
            "pillar": p.get("pillar") or e.get("actor"),
            "parentRootHash": p.get("parentRootHash") or p.get("parent_root_hash"),
        })
    return _maybe_text(
        request,
        {
            "THOT_v1_galileo":   thot_g,
            "THOT_v1_aristotle": thot_a,
            "recent_anchors":    out,
        },
        route_path="/insight/openagents/thot",
    )


# --------------------------------------------------------------------- #
# AgentRegistry (ERC-8004) — Module 8
# --------------------------------------------------------------------- #

@router.get("/insight/openagents/agentregistry", summary="ERC-8004 AgentRegistry registrations")
async def insight_agentregistry(request: Request, limit: int = 20):
    galileo = _load_deployments(GALILEO_DEPLOYMENTS)
    sepolia = _load_deployments(SEPOLIA_DEPLOYMENTS)
    aristotle = _load_deployments(ARISTOTLE_DEPLOYMENTS)
    reg_g = galileo.get("contracts", {}).get("AgentRegistry", {}) if galileo else {}
    reg_s = sepolia.get("contracts", {}).get("AgentRegistry", {}) if sepolia else {}
    reg_a = aristotle.get("contracts", {}).get("AgentRegistry", {}) if aristotle else {}

    def pred(e):
        return e.get("actor") in ("agent_registry", "agentregistry", "demo_agent") and (
            (e.get("payload") or {}).get("agentId") is not None
            or (e.get("payload") or {}).get("agent_token_id") is not None
        )
    events = _tail_catalogue(pred, limit=limit)
    out = []
    for e in events:
        p = e.get("payload") or {}
        out.append({
            "ts": e.get("ts"),
            "agentTokenId": p.get("agent_token_id") or p.get("agentTokenId"),
            "agentId": p.get("agentId") or p.get("agent_id"),
            "owner": p.get("owner") or p.get("wallet"),
            "linkedINFT_7857": p.get("linkedINFT_7857") or p.get("inft"),
            "attestorCount": p.get("attestorCount") or 0,
        })
    return _maybe_text(
        request,
        {
            "AgentRegistry_galileo":   reg_g,
            "AgentRegistry_sepolia":   reg_s,
            "AgentRegistry_aristotle": reg_a,
            "recent_registrations":    out,
        },
        route_path="/insight/openagents/agentregistry",
    )


# --------------------------------------------------------------------- #
# Summary (dashboard hero)
# --------------------------------------------------------------------- #

@router.get("/insight/openagents/summary", summary="One-shot rollup for /openagents.html hero")
async def insight_summary(request: Request):
    galileo = _load_deployments(GALILEO_DEPLOYMENTS)
    aristotle = _load_deployments(ARISTOTLE_DEPLOYMENTS)
    sepolia = _load_deployments(SEPOLIA_DEPLOYMENTS)
    conclave = _load_deployments(CONCLAVE_DEPLOYMENTS)

    def count(pred):
        return len(_tail_catalogue(pred, limit=10000))

    uniswap_cycles = 0
    if UNISWAP_LOG.exists():
        try:
            with UNISWAP_LOG.open("rb") as fh:
                uniswap_cycles = sum(1 for _ in fh)
        except Exception:
            pass

    inft_deployed = bool(galileo.get("contracts", {}).get("iNFT_7857") or
                         aristotle.get("contracts", {}).get("iNFT_7857"))
    thot_deployed = bool(galileo.get("contracts", {}).get("THOT_v1") or
                         aristotle.get("contracts", {}).get("THOT_v1"))
    bankon_deployed = bool(sepolia.get("contracts", {}).get("BankonSubnameRegistrar"))
    conclave_deployed = bool(conclave.get("contracts", {}).get("Conclave"))
    agentreg_deployed = bool(galileo.get("contracts", {}).get("AgentRegistry") or
                             sepolia.get("contracts", {}).get("AgentRegistry") or
                             aristotle.get("contracts", {}).get("AgentRegistry"))

    return _maybe_text(
        request,
        {
            "framework_agnostic": True,
            "compatible_with": ["openclaw", "nanoclaw", "zeroclaw", "nullclaw", "any"],
            "modules": [
                {"id": "inft7857",      "track": "0G — Best Autonomous Agents / iNFT",        "status": "deployed" if inft_deployed else "tested-not-deployed"},
                {"id": "0g-adapter",    "track": "0G — Best Framework",                        "status": "live"},
                {"id": "conclave",      "track": "Gensyn — AXL",                               "status": "deployed" if conclave_deployed else "tested-not-deployed"},
                {"id": "bankon-v1",     "track": "ENS — Best Integration + Most Creative",     "status": "deployed" if bankon_deployed else "tested-not-deployed"},
                {"id": "keeperhub",     "track": "KeeperHub — Best Use + Builder Bounty",      "status": "live"},
                {"id": "uniswap",       "track": "Uniswap — Best API Integration",             "status": "trader-built"},
                {"id": "thot",          "track": "primitive — boosts iNFT + Framework",        "status": "deployed" if thot_deployed else "tested-not-deployed"},
                {"id": "agentregistry", "track": "primitive — boosts iNFT + ENS",              "status": "deployed" if agentreg_deployed else "tested-not-deployed"},
            ],
            "counts": {
                "compute_calls":      count(lambda e: (e.get("payload") or {}).get("attestation") is not None),
                "storage_uploads":    count(lambda e: "0g://" in str((e.get("payload") or {}).get("uri", ""))),
                "kh_settlements":     count(lambda e: e.get("actor") == "keeperhub_bridge"),
                "ens_issuances":      count(lambda e: e.get("actor") in ("subdomain_issuer", "id_manager_agent")),
                "thot_anchors":       count(lambda e: e.get("kind") == "memory.anchor"),
                "uniswap_cycles":     uniswap_cycles,
            },
            "test_totals": {
                "iNFT_7857":             56,
                "BankonSubnameRegistrar": 29,
                "THOT_v1":               14,
                "AgentRegistry":         20,
                "Conclave_python":        9,
                "Conclave_solidity":     10,
                "total":                138,
            },
            "deployments": {
                "galileo":   galileo,
                "aristotle": aristotle,
                "sepolia":   sepolia,
                "conclave":  conclave,
            },
        },
        route_path="/insight/openagents/summary",
    )
