"""
inference_ledger.py — append-only, hash-linked record of every LLM inference (tokens + price PER MODEL),
in a format suitable for periodic publication to the blockchain (immutable cost provenance).

Per the thesis/manifesto: mindX maximizes daily inference at the lowest cost, and keeps an immutable
ledger of what each model cost it. Each entry is HASH-LINKED to the previous (sha256 over the canonical
fields + prev_hash) — so the ledger is tamper-evident, a mini-chain. `anchor_digest()` rolls the whole
ledger up to a single deterministic sha256 + per-model totals for on-chain anchoring (same pattern as the
storage/anchor offload). This is memory-from-logs: rebuildable, and the head hash is what gets anchored.

Disable with MINDX_INFERENCE_LEDGER_DISABLE=1. Best-effort + lock-guarded: a ledger failure NEVER breaks
the inference it is recording.
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
except Exception:  # pragma: no cover - import-order safety
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

LEDGER_PATH = PROJECT_ROOT / "data" / "monitoring" / "inference_ledger.jsonl"
_GENESIS = "0" * 64
_HASHED_FIELDS = ("seq", "ts", "agent", "provider", "model", "prompt_tokens",
                  "completion_tokens", "cost_usd", "purpose", "prev_hash")
_lock = threading.Lock()


def _disabled() -> bool:
    return os.getenv("MINDX_INFERENCE_LEDGER_DISABLE") == "1"


def _entry_hash(entry: dict) -> str:
    canonical = json.dumps({k: entry[k] for k in _HASHED_FIELDS}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _last_entry() -> Optional[dict]:
    """Read the tail line (the chain head) without loading the whole file."""
    if not LEDGER_PATH.exists():
        return None
    try:
        with open(LEDGER_PATH, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 8192))
            lines = f.read().decode("utf-8", "replace").splitlines()
        for ln in reversed(lines):
            ln = ln.strip()
            if ln:
                return json.loads(ln)
    except Exception:
        return None
    return None


def record(*, agent: str, provider: str, model: str, prompt_tokens: int = 0,
           completion_tokens: int = 0, cost_usd: float = 0.0, purpose: str = "",
           ts: Optional[float] = None) -> Optional[dict]:
    """Append one hash-linked inference entry. Returns the entry (or None if disabled/failed)."""
    if _disabled():
        return None
    try:
        with _lock:
            prev = _last_entry()
            entry = {
                "seq": (prev["seq"] + 1) if prev else 0,
                "ts": round(ts if ts is not None else time.time(), 3),
                "agent": str(agent or "?")[:80],
                "provider": str(provider or "?")[:40],
                "model": str(model or "?")[:80],
                "prompt_tokens": int(prompt_tokens or 0),
                "completion_tokens": int(completion_tokens or 0),
                "total_tokens": int(prompt_tokens or 0) + int(completion_tokens or 0),
                "cost_usd": round(float(cost_usd or 0.0), 8),
                "purpose": str(purpose or "")[:48],
                "prev_hash": prev["hash"] if prev else _GENESIS,
            }
            entry["hash"] = _entry_hash(entry)
            LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(LEDGER_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, separators=(",", ":")) + "\n")
            return entry
    except Exception:
        return None


def _iter_entries():
    if not LEDGER_PATH.exists():
        return
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                yield json.loads(ln)
            except Exception:
                continue


def summary(limit_tail: int = 20, since_ts: Optional[float] = None) -> dict:
    """Per-model token/cost rollup + recent tail + the anchorable head hash."""
    by_model: dict = {}
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost_usd": 0.0, "count": 0}
    tail: list = []
    head_hash = _GENESIS
    for e in _iter_entries():
        head_hash = e.get("hash", head_hash)
        if since_ts is not None and e.get("ts", 0) < since_ts:
            continue
        m = e.get("model", "?")
        d = by_model.setdefault(m, {"provider": e.get("provider", "?"), "count": 0,
                                     "prompt_tokens": 0, "completion_tokens": 0,
                                     "total_tokens": 0, "cost_usd": 0.0})
        d["count"] += 1
        for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
            d[k] += e.get(k, 0)
            totals[k] += e.get(k, 0)
        d["cost_usd"] = round(d["cost_usd"] + e.get("cost_usd", 0.0), 8)
        totals["cost_usd"] = round(totals["cost_usd"] + e.get("cost_usd", 0.0), 8)
        totals["count"] += 1
        tail.append(e)
    return {
        "entries": totals["count"],
        "by_model": by_model,
        "totals": totals,
        "tail": tail[-limit_tail:][::-1] if limit_tail else [],
        "head_hash": head_hash,
        "ledger_path": str(LEDGER_PATH),
    }


def anchor_digest() -> dict:
    """A compact, deterministic digest for periodic on-chain anchoring of the whole ledger to date."""
    s = summary(limit_tail=0)
    payload = {
        "entries": s["entries"],
        "head_hash": s["head_hash"],
        "totals": s["totals"],
        "by_model": {m: {"count": d["count"], "total_tokens": d["total_tokens"], "cost_usd": d["cost_usd"]}
                     for m, d in s["by_model"].items()},
    }
    payload["digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return payload


def verify_chain() -> dict:
    """Walk the chain and confirm every link (prev_hash + recomputed hash). Tamper-evidence proof."""
    prev_hash = _GENESIS
    ok = 0
    broken_at = None
    for e in _iter_entries():
        if e.get("prev_hash") != prev_hash or _entry_hash(e) != e.get("hash"):
            broken_at = e.get("seq")
            break
        prev_hash = e["hash"]
        ok += 1
    return {"valid": broken_at is None, "verified_entries": ok, "broken_at_seq": broken_at, "head_hash": prev_hash}
