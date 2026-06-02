"""
I am the x402 paywall.

When a caller hits a cost-bearing endpoint without a valid payment header,
I construct a triple-rail 402 envelope (Base USDC, Tempo USDC.e, Algorand
USDC ASA) and return it. When a caller presents a valid X-PAYMENT header,
I verify the settlement with the configured facilitator (or accept a
syntactically-valid stub in dev mode) and let the request through.

Logged-in callers get a free-quota allowance (10 calls per 24h rolling
window) before x402 kicks in. Anonymous callers get 0 free calls.

For the protocol contract see ``docs/services/x402_as_a_service.md``.

The middleware is a FastAPI ``Depends`` factory:

    @app.post("/coordinator/query", dependencies=[Depends(x402_required("/coordinator/query"))])
    async def coordinator_query(...): ...

The dependency:
  1. Reads the request's wallet address from the session (X-Session-Token).
  2. Looks up the per-endpoint price from data/config/x402_pricing.json.
  3. If the caller has free quota remaining → records the call + lets it through.
  4. Else if the caller presented a valid X-PAYMENT header → verifies + records.
  5. Else → raises HTTPException(402, detail=<triple-rail envelope>).

Records every settlement to ``data/governance/free_quota_ledger.json`` and
mirrors a ``payment.x402.settled`` catalogue event (best-effort).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


# ─── Config loader (hot-reloadable) ──────────────────────────────────────


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PRICING_PATH = _PROJECT_ROOT / "data" / "config" / "x402_pricing.json"
_QUOTA_LEDGER_PATH = _PROJECT_ROOT / "data" / "governance" / "free_quota_ledger.json"

_pricing_cache: Dict[str, Any] = {}
_pricing_loaded_at: float = 0.0


def _load_pricing(force: bool = False) -> Dict[str, Any]:
    """Read pricing config; reload if the file is newer than what we have.

    Reads the JSON on first call and whenever the file's mtime is newer than
    the cached load timestamp. Hot-reload contract documented in
    ``docs/services/x402_as_a_service.md`` §6.
    """
    global _pricing_cache, _pricing_loaded_at
    try:
        mtime = _PRICING_PATH.stat().st_mtime
    except OSError:
        return _pricing_cache
    if not force and _pricing_cache and mtime <= _pricing_loaded_at:
        return _pricing_cache
    try:
        with _PRICING_PATH.open("r", encoding="utf-8") as fh:
            _pricing_cache = json.load(fh)
        _pricing_loaded_at = mtime
    except Exception as exc:
        logger.warning(f"x402: failed to load pricing config: {exc}")
    return _pricing_cache


# ─── Free-quota ledger (per-wallet 24h rolling window) ───────────────────


def _load_quota_ledger() -> Dict[str, List[float]]:
    """Load the per-wallet quota ledger.

    Shape: ``{ "<wallet_lower>": [<unix_ts>, ...] }`` — a list of timestamps,
    each representing one free-quota call within the last 24h. Entries older
    than 24h are pruned on every read.
    """
    if not _QUOTA_LEDGER_PATH.exists():
        return {}
    try:
        with _QUOTA_LEDGER_PATH.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    cutoff = time.time() - 24 * 3600
    pruned: Dict[str, List[float]] = {}
    for wallet, ts_list in raw.items():
        if not isinstance(ts_list, list):
            continue
        kept = [float(t) for t in ts_list if isinstance(t, (int, float)) and float(t) >= cutoff]
        if kept:
            pruned[wallet] = kept
    return pruned


def _save_quota_ledger(ledger: Dict[str, List[float]]) -> None:
    try:
        _QUOTA_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _QUOTA_LEDGER_PATH.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(ledger, fh, indent=2)
        tmp.replace(_QUOTA_LEDGER_PATH)
    except Exception as exc:
        logger.warning(f"x402: failed to persist quota ledger: {exc}")


def _quota_status(wallet: str) -> Tuple[int, int]:
    """Return ``(used_in_window, limit)`` for ``wallet`` (lowercased).

    ``limit`` is taken from pricing config. For anonymous callers
    (empty/None wallet), the anonymous limit applies (0 by default).
    """
    cfg = _load_pricing()
    fq = cfg.get("free_quota", {}) if isinstance(cfg, dict) else {}
    if not wallet or wallet == "anonymous":
        limit = int(fq.get("anonymous_calls_per_24h", 0))
    else:
        limit = int(fq.get("calls_per_24h", 10))
    ledger = _load_quota_ledger()
    used = len(ledger.get((wallet or "").lower(), []))
    return used, limit


def _record_quota_use(wallet: str) -> None:
    if not wallet:
        return
    ledger = _load_quota_ledger()
    key = wallet.lower()
    ledger.setdefault(key, []).append(time.time())
    _save_quota_ledger(ledger)


# ─── Settlement verification ─────────────────────────────────────────────


_settlement_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _settlement_cache_ttl() -> int:
    cfg = _load_pricing()
    ido = cfg.get("idempotency", {}) if isinstance(cfg, dict) else {}
    return int(ido.get("settlement_cache_ttl_seconds", 60))


def _verify_x_payment(header_value: str, endpoint_id: str, max_amount: int) -> Dict[str, Any]:
    """Verify a base64-encoded X-PAYMENT envelope.

    The full contract is in ``docs/services/x402_as_a_service.md`` §3. This
    implementation does *syntactic* verification on every request and defers
    *cryptographic* verification to the facilitator at the URL configured in
    pricing config.

    In test / dev mode (``MINDX_X402_TEST_MODE=1``), the function accepts any
    syntactically-valid envelope and returns a stub success — the receipt
    contains ``tx_hash="0xtest"`` to make the test path observable.

    Returns the verified settlement record (with ``tx_hash``, ``rail``,
    ``amount_microusd``) on success. Raises ``HTTPException(402)`` on failure
    so the caller falls back to the standard 402 path.
    """
    try:
        decoded = base64.b64decode(header_value).decode("utf-8")
        env = json.loads(decoded)
    except Exception as exc:
        raise HTTPException(status_code=402, detail={
            "code": "x402_malformed_payment",
            "reason": f"could not decode X-PAYMENT: {exc}",
        })

    if not isinstance(env, dict):
        raise HTTPException(status_code=402, detail={"code": "x402_malformed_payment"})

    scheme = env.get("scheme")
    network = env.get("network")
    payload = env.get("payload") or {}
    if scheme != "exact" or not network or not isinstance(payload, dict):
        raise HTTPException(status_code=402, detail={
            "code": "x402_malformed_payment",
            "reason": "envelope must have scheme='exact', network, payload",
        })

    # Idempotency cache: a verified settlement is honored for ~60s on retry.
    cache_key = f"{network}:{json.dumps(payload, sort_keys=True)[:256]}"
    now = time.time()
    ttl = _settlement_cache_ttl()
    cached = _settlement_cache.get(cache_key)
    if cached and (now - cached[0]) < ttl:
        return cached[1]

    test_mode = os.environ.get("MINDX_X402_TEST_MODE", "0").strip() == "1"
    if test_mode:
        record = {
            "rail": network,
            "tx_hash": "0xtest",
            "amount_microusd": max_amount,
            "verified_at": now,
            "facilitator": "test-stub",
        }
        _settlement_cache[cache_key] = (now, record)
        return record

    # Production path: call the facilitator's /verify endpoint.
    cfg = _load_pricing()
    fac = (cfg.get("facilitator") or {}).get("url") if isinstance(cfg, dict) else None
    if not fac:
        raise HTTPException(status_code=503, detail={
            "code": "x402_facilitator_not_configured",
            "reason": "facilitator URL missing from x402_pricing.json",
        })

    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                fac.rstrip("/") + "/verify",
                json={
                    "scheme": scheme,
                    "network": network,
                    "payload": payload,
                    "endpoint": endpoint_id,
                    "max_amount_microusd": max_amount,
                },
            )
    except Exception as exc:
        raise HTTPException(status_code=503, detail={
            "code": "x402_facilitator_unreachable",
            "reason": str(exc),
        })

    if resp.status_code != 200:
        raise HTTPException(status_code=402, detail={
            "code": "x402_facilitator_rejected",
            "status": resp.status_code,
            "body": resp.text[:512],
        })

    try:
        body = resp.json()
    except Exception:
        raise HTTPException(status_code=402, detail={"code": "x402_facilitator_bad_response"})

    if not body.get("verified"):
        raise HTTPException(status_code=402, detail={
            "code": "x402_settlement_not_verified",
            "reason": body.get("reason", ""),
        })

    record = {
        "rail": network,
        "tx_hash": body.get("txHash", ""),
        "amount_microusd": int(body.get("amount", max_amount)),
        "verified_at": now,
        "facilitator": fac,
    }
    _settlement_cache[cache_key] = (now, record)
    return record


# ─── 402 envelope builder ────────────────────────────────────────────────


def _build_402_envelope(endpoint_id: str, max_amount: int) -> Dict[str, Any]:
    """Construct the triple-rail 402 envelope per the spec.

    The endpoint_id is used to fill in the ``resource`` field; max_amount
    overrides the rail's default amount when present.
    """
    cfg = _load_pricing()
    rails_cfg = cfg.get("rails", {}) if isinstance(cfg, dict) else {}
    requirements: List[Dict[str, Any]] = []
    for name, rail in rails_cfg.items():
        if not isinstance(rail, dict):
            continue
        # Skip rails whose payTo is empty / zero (rail advertised but not settling yet).
        pay_to = str(rail.get("payTo", "")).strip()
        if not pay_to or pay_to == "0x0000000000000000000000000000000000000000":
            continue
        requirements.append({
            "scheme": rail.get("scheme", "exact"),
            "network": rail.get("network", name),
            "asset": rail.get("asset", ""),
            "maxAmountRequired": str(max_amount),
            "payTo": pay_to,
            "resource": endpoint_id,
            "description": rail.get("_comment", ""),
            "mimeType": "application/json",
            "extra": rail.get("extra", {}),
        })

    return {
        "code": "x402_payment_required",
        "message": "This endpoint requires payment. Settle on any of the offered rails and re-submit with X-PAYMENT.",
        "endpoint": endpoint_id,
        "paymentRequirements": requirements,
        "x402Version": 1,
        "_note": "See docs/services/x402_as_a_service.md for the protocol contract.",
    }


# ─── Catalogue mirror ────────────────────────────────────────────────────


async def _emit_settlement_event(wallet: str, endpoint_id: str, record: Dict[str, Any]) -> None:
    try:
        from agents.catalogue.events import emit_catalogue_event
        await emit_catalogue_event(
            kind="payment.x402.settled",
            actor="mindx.gateway",
            payload={
                "endpoint": endpoint_id,
                "wallet": wallet,
                "rail": record.get("rail"),
                "amount_microusd": record.get("amount_microusd"),
                "tx_hash": record.get("tx_hash"),
                "facilitator": record.get("facilitator"),
            },
            source_log="mindx_backend_service.x402_middleware",
        )
    except Exception:
        # Catalogue write failure must NEVER break a paid request.
        pass


async def _emit_free_quota_event(wallet: str, endpoint_id: str, used: int, limit: int) -> None:
    try:
        from agents.catalogue.events import emit_catalogue_event
        await emit_catalogue_event(
            kind="payment.x402.free_quota",
            actor="mindx.gateway",
            payload={
                "endpoint": endpoint_id,
                "wallet": wallet,
                "used_in_window": used + 1,
                "limit": limit,
            },
            source_log="mindx_backend_service.x402_middleware",
        )
    except Exception:
        pass


# ─── Session inspection ──────────────────────────────────────────────────


def _wallet_from_request(request: Request) -> Optional[str]:
    """Return the lowercase wallet address from the session, or None."""
    token = request.headers.get("X-Session-Token")
    if not token:
        return None
    try:
        # Lazy import to avoid a hard dependency on the vault during tests.
        from mindx_backend_service.bankon_vault import get_vault_manager
        vault = get_vault_manager()
        session = vault.get_user_session(token)
        if session and session.get("wallet_address"):
            return str(session["wallet_address"]).lower()
    except Exception:
        return None
    return None


# ─── The decorator-style factory ─────────────────────────────────────────


def x402_required(endpoint_id: str, max_amount_microusd: Optional[int] = None) -> Callable:
    """Return a FastAPI dependency that enforces x402 on the decorated route.

    The dependency:
      1. Looks up the wallet from X-Session-Token.
      2. If wallet has free quota remaining → records and allows.
      3. Else if X-PAYMENT present and verifies → records and allows.
      4. Else → raises HTTPException(402) with the triple-rail envelope.

    The ``endpoint_id`` is the canonical path string used in pricing config
    and catalogue events (e.g. "/coordinator/query"). When the path contains
    a path parameter like ``{agent_id}``, pass the templated form
    (``/agents/{agent_id}/evolve``) — the middleware uses it as a key, not
    a route match.
    """
    async def _dep(request: Request) -> Dict[str, Any]:
        cfg = _load_pricing()
        endpoints = cfg.get("endpoints", {}) if isinstance(cfg, dict) else {}
        rule = endpoints.get(endpoint_id, {})
        amount = int(rule.get("max_amount_microusd", max_amount_microusd or 2000))

        wallet = _wallet_from_request(request) or "anonymous"
        used, limit = _quota_status(wallet)

        if used < limit:
            _record_quota_use(wallet)
            await _emit_free_quota_event(wallet, endpoint_id, used, limit)
            return {"path": "free_quota", "wallet": wallet, "used": used + 1, "limit": limit}

        x_payment = request.headers.get("X-PAYMENT")
        if x_payment:
            record = _verify_x_payment(x_payment, endpoint_id, amount)
            await _emit_settlement_event(wallet, endpoint_id, record)
            return {"path": "x402_settled", "wallet": wallet, **record}

        envelope = _build_402_envelope(endpoint_id, amount)
        if not envelope["paymentRequirements"]:
            # No rails currently settling → upgrade to 503 so the caller knows
            # the operator hasn't finished configuring x402 yet.
            raise HTTPException(status_code=503, detail={
                "code": "x402_no_rails_configured",
                "reason": "No x402 rails have a payTo address yet. Operator must update data/config/x402_pricing.json.",
            })
        raise HTTPException(status_code=402, detail=envelope)

    _dep.__name__ = f"x402_required_for_{endpoint_id.strip('/').replace('/', '_').replace('{', '').replace('}', '')}"
    return _dep
