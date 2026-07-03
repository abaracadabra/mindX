"""
inference_ledger.py — blockchain ANCHOR layer over the EXISTING precision-metrics ledger.

mindX already keeps the source-of-truth inference ledger in `llm/precision_metrics.py`
(`PrecisionMetricsTracker` → `data/metrics/cloud_precision_metrics.json`): ACTUAL per-model tokens
(eval_count / prompt_eval_count, 18-dp) that feed the boardroom value>cost upgrade trigger
(BOARDROOM.md §3.X). This module does NOT duplicate that — it READS it and produces a deterministic,
hash-linked ANCHOR CHAIN suitable for periodic publication to the blockchain (immutable cost provenance
as mindX evolves into permanence).

Each `anchor()` snapshots the ledger's accounting state → a `state_digest` (sha256), and appends a
hash-linked anchor entry (`prev_hash` + state → `anchor_hash`) to `data/monitoring/inference_anchors.jsonl`.
`anchor()` is idempotent on an unchanged ledger. The latest `anchor_hash` is what gets published on-chain.
Disable with `MINDX_INFERENCE_LEDGER_DISABLE=1`.
"""
from __future__ import annotations

import json
import os
import hashlib
import threading
import time
from pathlib import Path
from typing import Optional

try:
    from utils.config import PROJECT_ROOT
except Exception:  # pragma: no cover
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Source-of-truth ledger (the existing precision-metrics tracker persists here).
PRECISION_METRICS_PATH = PROJECT_ROOT / "data" / "metrics" / "cloud_precision_metrics.json"
# The anchor chain — periodic immutable snapshots for on-chain publication.
ANCHOR_PATH = PROJECT_ROOT / "data" / "monitoring" / "inference_anchors.jsonl"
_GENESIS = "0" * 64
_ANCHOR_HASHED = ("seq", "ts", "state_digest", "global_total_requests",
                  "global_total_tokens", "global_total_cost_usd", "prev_hash")
_lock = threading.Lock()


def _disabled() -> bool:
    return os.getenv("MINDX_INFERENCE_LEDGER_DISABLE") == "1"


def _read_ledger() -> dict:
    if not PRECISION_METRICS_PATH.exists():
        return {}
    try:
        return json.loads(PRECISION_METRICS_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _state_digest(ledger: dict) -> str:
    """Deterministic sha256 of the ledger's accounting state (order-independent)."""
    models = ledger.get("models", {}) or {}
    canon = {
        "gr": ledger.get("global_total_requests", 0),
        "ge": ledger.get("global_total_eval_tokens", 0),
        "gp": ledger.get("global_total_prompt_tokens", 0),
        "gc": str(ledger.get("global_total_cost_usd", "0")),
        "m": {m: [d.get("total_requests", 0), d.get("total_eval_count", 0),
                  d.get("total_prompt_eval_count", 0)]
              for m, d in sorted(models.items())},
    }
    return hashlib.sha256(json.dumps(canon, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _anchor_hash(entry: dict) -> str:
    return hashlib.sha256(json.dumps({k: entry[k] for k in _ANCHOR_HASHED},
                          sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _read_anchors(limit: int = 0) -> list:
    """limit=0 → full chain ascending; limit>0 → newest-first, capped."""
    if not ANCHOR_PATH.exists():
        return []
    out = []
    try:
        with open(ANCHOR_PATH, "r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    out.append(json.loads(ln))
                except Exception:
                    continue
    except Exception:
        return []
    return out[-limit:][::-1] if limit else out


def anchor(ts: Optional[float] = None) -> Optional[dict]:
    """Snapshot the precision-metrics ledger into a hash-linked anchor (blockchain-publishable).
    Idempotent: returns the existing head anchor unchanged if the ledger state hasn't moved."""
    if _disabled():
        return None
    try:
        with _lock:
            ledger = _read_ledger()
            digest = _state_digest(ledger)
            head = _read_anchors(1)
            prev = head[0] if head else None
            if prev and prev.get("state_digest") == digest:
                return prev  # nothing changed since last anchor
            entry = {
                "seq": (prev["seq"] + 1) if prev else 0,
                "ts": round(ts if ts is not None else time.time(), 3),
                "state_digest": digest,
                "global_total_requests": ledger.get("global_total_requests", 0),
                "global_total_tokens": ledger.get("global_total_eval_tokens", 0) + ledger.get("global_total_prompt_tokens", 0),
                "global_total_cost_usd": str(ledger.get("global_total_cost_usd", "0")),
                "models": sorted((ledger.get("models", {}) or {}).keys()),
                "prev_hash": prev["anchor_hash"] if prev else _GENESIS,
            }
            entry["anchor_hash"] = _anchor_hash(entry)
            ANCHOR_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(ANCHOR_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, separators=(",", ":")) + "\n")
            return entry
    except Exception:
        return None


def summary(limit_tail: int = 20, do_anchor: bool = True) -> dict:
    """Per-model token rollup from the precision-metrics ledger + the anchor chain.
    By default also writes a fresh anchor when the ledger has changed (idempotent otherwise)."""
    if do_anchor:
        anchor()
    ledger = _read_ledger()
    models = ledger.get("models", {}) or {}
    by_model = {}
    for m, d in models.items():
        ev, pr = d.get("total_eval_count", 0), d.get("total_prompt_eval_count", 0)
        by_model[m] = {
            "requests": d.get("total_requests", 0),
            "eval_tokens": ev, "prompt_tokens": pr, "total_tokens": ev + pr,
            "cost_usd": float(d.get("total_cost_usd", 0) or 0),
        }
    ge, gp = ledger.get("global_total_eval_tokens", 0), ledger.get("global_total_prompt_tokens", 0)
    totals = {"requests": ledger.get("global_total_requests", 0),
              "eval_tokens": ge, "prompt_tokens": gp, "total_tokens": ge + gp,
              "cost_usd": float(ledger.get("global_total_cost_usd", 0) or 0)}
    anchors = _read_anchors(max(0, min(limit_tail, 100)))
    return {
        "source": "precision_metrics",
        "entries": totals["requests"],
        "by_model": by_model,
        "totals": totals,
        "state_digest": _state_digest(ledger),
        "anchors": anchors,
        "head_anchor": anchors[0]["anchor_hash"] if anchors else _GENESIS,
        "anchor_count": len(_read_anchors(0)),
        "ledger_path": str(PRECISION_METRICS_PATH),
    }


def anchor_digest() -> dict:
    """The current publishable digest: live state digest + head anchor hash."""
    ledger = _read_ledger()
    head = _read_anchors(1)
    return {
        "digest_sha256": _state_digest(ledger),
        "head_anchor": head[0]["anchor_hash"] if head else _GENESIS,
        "anchored_seq": head[0]["seq"] if head else -1,
        "global_total_requests": ledger.get("global_total_requests", 0),
    }


def verify_chain() -> dict:
    """Walk the anchor chain and confirm every hash link (tamper-evidence proof)."""
    prev_hash = _GENESIS
    ok = 0
    broken = None
    for e in _read_anchors(0):
        if e.get("prev_hash") != prev_hash or _anchor_hash(e) != e.get("anchor_hash"):
            broken = e.get("seq")
            break
        prev_hash = e["anchor_hash"]
        ok += 1
    return {"valid": broken is None, "verified_anchors": ok, "broken_at_seq": broken, "head_anchor": prev_hash}
