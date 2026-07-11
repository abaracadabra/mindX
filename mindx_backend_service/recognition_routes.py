"""
mindX RECOGNITION — the offering to a recognized participant.

Kin to the DeltaVerse OVERLORD/login333 ladder (the two systems have been developing from each
other), but mindX recognizes a *different* thing. DeltaVerse recognizes holdings and names.
**mindX recognizes contribution to cognition** — you are recognized here by what you gave the
mind, not by what you own.

The flow (identical in spirit to the DeltaVerse sovereign offering, and deliberately so):

    GET  /recognition/offer            → the ladder, the covenant, the configured airdrop (public)
    POST /recognition/recognize        → { address, signature } over the covenant → mint a rung
    POST /recognition/airdrop          → queue the configured grant for a recognized address
    GET  /recognition/status/{address} → rung, earned, airdrop position
    GET  /recognized                   → THE RECOGNITION FIELD (mindX's own substrate)

SOVEREIGNTY: a new wallet is created **in the participant's browser**, shown once, and forgotten.
mindX persists the ADDRESS only — never key material. The handoff protects the participant and
protects mindX. BANKON — all rights preserved · cypherpunk2048 (CP2048-OVL-1).

Nothing here moves funds. The airdrop is a QUEUE; delivery is an operator/OVERSEER act against a
real on-chain asset. An unconfigured grant (asset_id null) queues and says so — it never pretends.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException
from starlette.responses import FileResponse

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["recognition"])

CONFIG_PATH = PROJECT_ROOT / "data" / "config" / "recognition.json"
STATE_DIR = PROJECT_ROOT / "data" / "recognition"
QUEUE_PATH = STATE_DIR / "airdrop-queue.jsonl"
ROLL_PATH = STATE_DIR / "recognized.jsonl"
FIELD_HTML = Path(__file__).parent / "recognition_field.html"


def _config() -> Dict[str, Any]:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception as e:
        logger.error("recognition: config unreadable (%s) — the offering is closed", e)
        return {"ladder": [], "airdrop": {"enabled": False}, "covenant": {}}


def covenant_message(address: str) -> str:
    """The canonical signing text — single source for browser AND verifier, so the two can
    never drift (the lesson DeltaVerse's sovereign covenant learned first)."""
    c = _config().get("covenant", {})
    return "\n".join([
        "mindX recognition covenant",
        "v: 1",
        f"standard: {c.get('standard', 'CP2048-OVL-1 (cypherpunk2048)')}",
        f"rights: {c.get('rights', 'BANKON — all rights preserved')}",
        f"wallet: {address}",
        f"affirmation: {c.get('affirmation', 'I am SOVEREIGN.')}",
    ])


def _rung_for(earned: int, ladder) -> Dict[str, Any]:
    best = ladder[0] if ladder else {"rung": "visitor", "rank": 0}
    for r in ladder:
        e = r.get("earned")
        if e is not None and earned >= e:
            best = r
    return best


def _read_roll() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    try:
        for line in ROLL_PATH.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            out[rec["address"].lower()] = rec          # last write wins — the roll is append-only
    except Exception:
        pass
    return out


def _append(path: Path, rec: Dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")


def _verify_evm(address: str, signature: str, message: str) -> bool:
    """ecrecover(message, sig) == address. The signature IS the identity claim."""
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
        rec = Account.recover_message(encode_defunct(text=message), signature=signature)
        return rec.lower() == address.lower()
    except Exception as e:
        logger.warning("recognition: EVM verify unavailable/failed: %s", e)
        return False


def _verify_algorand(address: str, signature: str, message: str) -> bool:
    """Ed25519 over the covenant — the mindx.algo / Pera / PARSEC path."""
    try:
        import base64
        from algosdk import encoding as algo_encoding
        from algosdk.util import verify_bytes
        return bool(verify_bytes(message.encode("utf-8"), base64.b64decode(signature), address)) \
            and algo_encoding.is_valid_address(address)
    except Exception as e:
        logger.warning("recognition: Algorand verify unavailable/failed: %s", e)
        return False


# ── the offering (public) ───────────────────────────────────────────────────
@router.get("/recognition/offer")
async def recognition_offer() -> Dict[str, Any]:
    cfg = _config()
    ad = cfg.get("airdrop", {})
    return {
        "ok": True,
        "note": cfg.get("note"),
        "covenant": cfg.get("covenant", {}),
        "covenant_message_template": covenant_message("<your-address>"),
        "ladder": cfg.get("ladder", []),
        "airdrop": {
            "enabled": bool(ad.get("enabled")),
            "requireCovenantSignature": bool(ad.get("requireCovenantSignature", True)),
            "oncePerAddress": bool(ad.get("oncePerAddress", True)),
            "grants": [
                {**g, "configured": bool(g.get("asset_id") or g.get("contract"))}
                for g in ad.get("grants", [])
            ],
        },
        "substrate": cfg.get("substrate", {}),
        "recognized_count": len(_read_roll()),
    }


# ── recognition: the signature IS the recognition ───────────────────────────
@router.post("/recognition/recognize")
async def recognize(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    address = str(payload.get("address", "")).strip()
    signature = str(payload.get("signature", "")).strip()
    chain = str(payload.get("chain", "evm")).lower()
    if not address or not signature:
        raise HTTPException(400, "address and signature required")

    msg = covenant_message(address)
    ok = _verify_algorand(address, signature, msg) if chain == "algorand" \
        else _verify_evm(address, signature, msg)
    if not ok:
        raise HTTPException(401, "signature does not prove control of this address "
                                 "(the covenant text must match exactly)")

    roll = _read_roll()
    prior = roll.get(address.lower())
    earned = int(prior.get("earned", 0)) if prior else 0
    earned = max(earned, 1)                       # recognition itself is the first earning
    ladder = _config().get("ladder", [])
    rung = _rung_for(earned, ladder)

    rec = {"address": address, "chain": chain, "earned": earned, "rung": rung.get("rung"),
           "rank": rung.get("rank"), "iat": int(time.time()), "covenant_v": 1}
    _append(ROLL_PATH, rec)
    logger.info("recognition: %s recognized as %s (earned=%d)", address, rung.get("rung"), earned)
    return {"ok": True, **rec, "opens": rung.get("opens"),
            "substrate": _config().get("substrate", {}).get("path", "/recognized"),
            "sovereignty": "acknowledged — keys are yours alone; mindX holds only your address"}


# ── the configurable airdrop ────────────────────────────────────────────────
@router.post("/recognition/airdrop")
async def airdrop(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    cfg = _config()
    ad = cfg.get("airdrop", {})
    if not ad.get("enabled"):
        raise HTTPException(403, "the airdrop is not enabled")

    address = str(payload.get("address", "")).strip()
    signature = str(payload.get("signature", "")).strip()
    chain = str(payload.get("chain", "evm")).lower()
    if not address:
        raise HTTPException(400, "address required")

    if ad.get("requireCovenantSignature", True):
        msg = covenant_message(address)
        ok = _verify_algorand(address, signature, msg) if chain == "algorand" \
            else _verify_evm(address, signature, msg)
        if not ok:
            raise HTTPException(401, "covenant signature required — sign to affirm you are SOVEREIGN")

    roll = _read_roll()
    rec = roll.get(address.lower())
    if not rec:
        raise HTTPException(403, "not recognized — POST /recognition/recognize first")

    rung = rec.get("rung")
    grant = next((g for g in ad.get("grants", []) if g.get("rung") == rung), None)
    if not grant:
        return {"ok": True, "queued": False, "reason": f"no grant configured for rung '{rung}'",
                "rung": rung}

    if ad.get("oncePerAddress", True):
        try:
            for line in QUEUE_PATH.read_text().splitlines():
                if line.strip() and json.loads(line).get("address", "").lower() == address.lower():
                    return {"ok": True, "queued": False, "reason": "already queued", "rung": rung}
        except Exception:
            pass

    configured = bool(grant.get("asset_id") or grant.get("contract"))
    entry = {"address": address, "chain": grant.get("chain"), "asset": grant.get("asset"),
             "asset_id": grant.get("asset_id"), "contract": grant.get("contract"),
             "amount": grant.get("amount"), "rung": rung, "configured": configured,
             "iat": int(time.time())}
    _append(QUEUE_PATH, entry)
    logger.info("recognition: airdrop QUEUED %s → %s %s (configured=%s)",
                address, grant.get("amount"), grant.get("asset"), configured)
    return {
        "ok": True, "queued": True, "grant": entry,
        "delivery": "an OVERSEER settles the queue on-chain; mindX moves no funds from this endpoint",
        "warning": None if configured else
                   f"the '{grant.get('asset')}' grant has no asset_id/contract configured yet — "
                   f"your place is held, delivery waits on the operator deploying the asset",
        "rights": cfg.get("covenant", {}).get("rights"),
    }


@router.get("/recognition/status/{address}")
async def status(address: str) -> Dict[str, Any]:
    rec = _read_roll().get(address.lower())
    queued = 0
    try:
        for line in QUEUE_PATH.read_text().splitlines():
            if line.strip() and json.loads(line).get("address", "").lower() == address.lower():
                queued += 1
    except Exception:
        pass
    if not rec:
        return {"ok": True, "recognized": False, "rung": "visitor", "earned": 0, "airdrop_queued": bool(queued)}
    return {"ok": True, "recognized": True, **rec, "airdrop_queued": bool(queued)}


# ── mindX's OWN substrate ───────────────────────────────────────────────────
@router.get("/recognized")
async def recognition_field():
    """THE RECOGNITION FIELD — mindX's own substrate. Not a DeltaVerse expression: where the
    DeltaVerse renders light + action over a fabric, mindX renders COGNITION + MEMORY."""
    if not FIELD_HTML.exists():
        raise HTTPException(404, "the field is not installed")
    return FileResponse(str(FIELD_HTML), media_type="text/html")
