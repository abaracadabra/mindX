"""DeltaVerse configuration — nothing hardcoded.

Identity → role mapping reuses the overlord config (the canonical
SHADOW_OVERLORD_ADDRESS and MINDX_OVERSEER_ADDRESSES). The DeltaVerse adds the
non-human participant roles (model, agent) on top of the overlord axis.
"""
from __future__ import annotations

import os
from typing import Dict, List, Tuple

# The cypherpunk2048 hierarchy. Privilege ascends with the index.
# `member` = a paid-in *.bankon.eth subname holder (collection-from-payment by
# the bankon.eth overlord). `overlord` = the owner of bankon.eth itself.
REALM_ROLES: Tuple[str, ...] = ("public", "member", "model", "agent", "overseer", "overlord")


def is_enabled() -> bool:
    """The fabric mounts only when explicitly enabled (agnostic, opt-in)."""
    return os.environ.get("MINDX_DELTAVERSE_ENABLED", "0") == "1"


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name, default) or "").strip()


def rank(role: str) -> int:
    try:
        return REALM_ROLES.index((role or "public").lower())
    except ValueError:
        return 0


def can_grant(role: str, needed: str) -> bool:
    """Privilege gate. Payment/tenure can lift a participant toward `needed`;
    callers offer an upgrade path rather than a dead end when this is False."""
    return rank(role) >= rank(needed or "public")


def known_addresses() -> Dict[str, str]:
    """Authoritative address → role map from the overlord config. Used ONLY for
    an *unverified* visual hint; real privilege requires the signed overlord
    token (see overlord/resolver.py). Never grants access on its own."""
    out: Dict[str, str] = {}
    overlord = _env("SHADOW_OVERLORD_ADDRESS").lower()
    if overlord:
        out[overlord] = "overlord"
    overseers: List[str] = [a.strip().lower() for a in _env("MINDX_OVERSEER_ADDRESSES").split(",") if a.strip()]
    for a in overseers:
        out.setdefault(a, "overseer")
    # mindx.algo — the Algorand OVERSEER address (case-preserved; Algorand addresses are
    # case-sensitive base32). Real privilege is the signed OVERSEER JWT (overseer_auth.py);
    # this entry is only the unverified visual hint, like the others above.
    algo = _env("MINDX_ALGO_ADDRESS").strip()
    if algo:
        out.setdefault(algo, "overseer")
    return out


def bankon_eth_suffix() -> str:
    return _env("MINDX_DELTAVERSE_ENS_SUFFIX", ".bankon.eth") or ".bankon.eth"


# ── ENS resolution (subdomain.bankon.eth → owner → role) ────────────────────
# Reuses the agnostic openagents/bankoneth tiers module, which reads bankon.eth
# ownership LIVE (admin = owns bankon.eth = overlord; member = holds a subname).
# Everything here is best-effort: any RPC/import failure degrades to `public`
# and never raises. The result is an *unverified* hint (on-chain name ownership
# proves who owns the name, not who is asking) — privileged action stays behind
# the signed overlord token.

import time
from typing import Any, Optional

_TIERS_MOD: Any = None
_TIERS_TRIED = False
_RESOLVE_CACHE: Dict[str, tuple] = {}   # key -> (expiry_ts, result_dict)
_RESOLVE_TTL_S = 60.0


def ens_rpc() -> str:
    """ENS RPC: explicit override, else the same fallback chain tiers.py uses."""
    return (
        _env("MINDX_DELTAVERSE_ENS_RPC")
        or _env("BANKON_GATE_RPC")
        or _env("MAINNET_RPC")
        or "https://ethereum-rpc.publicnode.com"
    )


def _load_tiers() -> Any:
    """Lazy, defensive import of openagents/bankoneth/backend/tiers.py — by
    package first, then by file path. Cached; returns None if unavailable."""
    global _TIERS_MOD, _TIERS_TRIED
    if _TIERS_TRIED:
        return _TIERS_MOD
    _TIERS_TRIED = True
    try:
        from openagents.bankoneth.backend import tiers as _t  # type: ignore
        _TIERS_MOD = _t
        return _TIERS_MOD
    except Exception:
        pass
    try:
        import importlib.util
        from pathlib import Path
        try:
            from utils.config import PROJECT_ROOT
        except Exception:
            PROJECT_ROOT = Path(__file__).resolve().parents[2]
        path = PROJECT_ROOT / "openagents" / "bankoneth" / "backend" / "tiers.py"
        if path.exists():
            spec = importlib.util.spec_from_file_location("bankon_tiers", str(path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _TIERS_MOD = mod
    except Exception:
        _TIERS_MOD = None
    return _TIERS_MOD


def resolve_realm_identity(address: Optional[str], ens_name: Optional[str]) -> Dict[str, Any]:
    """Resolve a wallet address and/or *.bankon.eth name to {address, role, names,
    source}. bankon.eth root owner → overlord; *.bankon.eth subname holder →
    member; env overlord/overseer set wins as authoritative override. Never raises."""
    key = f"{(address or '').lower()}|{(ens_name or '').lower()}"
    now = time.time()
    hit = _RESOLVE_CACHE.get(key)
    if hit and hit[0] > now:
        return hit[1]

    result: Dict[str, Any] = {"address": address, "role": "public", "names": [], "source": "none"}
    tiers = _load_tiers()
    try:
        if tiers is not None:
            from web3 import Web3  # installed (7.x)
            w3 = Web3(Web3.HTTPProvider(ens_rpc(), request_kwargs={"timeout": 8}))
            suffix = bankon_eth_suffix()
            # Name path: resolve the name to its on-chain owner.
            if ens_name:
                nm = ens_name.lower().strip()
                if nm == suffix.lstrip("."):  # the bare root "bankon.eth"
                    owner = tiers.owner_of(w3, tiers.BANKON_ETH_NODE)
                    if owner:
                        result.update(address=owner, role="overlord", names=[nm], source="ens-root")
                else:
                    label = nm.replace(suffix, "")
                    owner = tiers.owner_of(w3, tiers.subname_node(label))
                    if owner:
                        # Subname holder == bankon.eth owner? then overlord, else member.
                        role = "overlord" if tiers.owns_root(w3, owner) else "member"
                        result.update(address=owner, role=role, names=[nm], source="ens-subname")
            # Address path: live tier (admin/member/visitor) for the raw address.
            elif address:
                tier = tiers.resolve_tier(address)
                t = (tier or {}).get("tier")
                role = {"admin": "overlord", "member": "member", "visitor": "public"}.get(t, "public")
                result.update(address=address, role=role,
                              names=tier.get("names", []), source="ens-tier")
    except Exception:
        # Any RPC/web3/module failure → leave as public.
        result["source"] = "error"

    # Authoritative env override (overlord/overseer addresses) always wins.
    if result.get("address"):
        forced = known_addresses().get(result["address"].lower())
        if forced and rank(forced) > rank(result["role"]):
            result["role"] = forced
            result["source"] = "env-override"

    _RESOLVE_CACHE[key] = (now + _RESOLVE_TTL_S, result)
    return result
