"""The mindX OVERLORD hierarchy — the canonical tier ladder.

ONE coherent ladder across BOTH sovereignty chains. Privilege ascends with rank; each tier names HOW it
is earned. Modeled on the DeltaVerse membership ladder (engine/membership.js) and unified with mindX's
two-chain reality:

    overlord  = bankon.eth      (EVM signature  → shadow_overlord)   — the PUBLIC OVERLORD, creates OVERSEERs
    overseer  = mindx.algo      (Algorand sig   → overseer_auth)     — governs the deployment domain
    member    = a *.bankon.eth subname                               — your name IS your membership
    model     = a mindXtrain-imprinted model                          — earned within the hierarchy
    agent     = a sovereign mindX agent identity (BANKON Vault)       — agentic DAIO voting
    participant = any connected wallet                                — recognized at the floor
    public    = the open surface                                      — read-only

RECIPROCITY: just as the modular DeltaVerse was inspired BY mindX, the DeltaVerse recognition layer now
PROTECTS mindX: this ladder IS the boundary. Each tier names not only HOW it is earned but the mindX
surface it GATES — recognition is the protection. The web gates are the real boundaries (the repo stays
private pending audit); an unrecognized caller reaches only the open, read-only surface.

This is the single source of truth; `deltaverse/config.py` defers to it.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

# Floor → apex. Privilege ascends with the index (rank). `how` = how a participant earns the tier;
# `gate` = the mindX surface that tier protects/unlocks (recognition-as-protection).
LADDER: List[Dict[str, str]] = [
    {"tier": "public",      "how": "the open surface — no wallet, read-only",
     "gate": "public diagnostics, docs, feedback — read-only, redacted"},
    {"tier": "participant", "how": "connect a wallet — recognized at the floor",
     "gate": "a recognized identity; the floor of the hierarchy"},
    {"tier": "agent",       "how": "a sovereign mindX agent identity (BANKON Vault wallet) — agentic DAIO voting",
     "gate": "agentic DAIO voting + A2A; an agent acts under its own key"},
    {"tier": "member",      "how": "own a subname.bankon.eth — your name IS your membership",
     "gate": "member surfaces; your name is your credential"},
    {"tier": "model",       "how": "a model promoted by a mindXtrain imprint — earned within the hierarchy",
     "gate": "served-model tier — earned by a positive imprint"},
    {"tier": "overseer",    "how": "sign in as mindx.algo (Algorand · Parsec/Pera) — governs the deployment domain, created by the OVERLORD",
     "gate": "the Algorand deployment suites (/overseer) — deploy under the OVERLORD"},
    {"tier": "overlord",    "how": "sign in as bankon.eth (EVM signature) — the PUBLIC OVERLORD, creates OVERSEERs",
     "gate": "sovereign control — registries, terms, mindX internals; creates OVERSEERs"},
]
ORDER: List[str] = [r["tier"] for r in LADDER]
_HOW: Dict[str, str] = {r["tier"]: r["how"] for r in LADDER}

# The two sovereign apex identities, by chain.
OVERLORD_CHAIN = "evm"        # bankon.eth — SHADOW_OVERLORD_ADDRESS
OVERSEER_CHAIN = "algorand"   # mindx.algo — MINDX_ALGO_ADDRESS / MINDX_OVERSEER_ADDRESSES


def rank(tier: str) -> int:
    try:
        return ORDER.index((tier or "public").lower())
    except ValueError:
        return 0


def next_tier(tier: str) -> Optional[str]:
    i = rank(tier)
    return ORDER[i + 1] if i + 1 < len(ORDER) else None


def can_grant(have: str, needed: str) -> bool:
    """Privilege gate. Offer an upgrade path rather than a dead end when this is False."""
    return rank(have) >= rank(needed or "public")


def _overlord_addr() -> str:
    return (os.environ.get("SHADOW_OVERLORD_ADDRESS") or "").strip().lower()


def _overseer_algo_addrs() -> set:
    out: set = set()
    one = (os.environ.get("MINDX_ALGO_ADDRESS") or "").strip().upper()
    if len(one) == 58:
        out.add(one)
    for a in (os.environ.get("MINDX_OVERSEER_ADDRESSES") or "").split(","):
        a = a.strip().upper()
        if len(a) == 58:
            out.add(a)
    return out


def recognize(*, evm_address: Optional[str] = None, algo_address: Optional[str] = None,
              role: Optional[str] = None, is_member: bool = False) -> Dict[str, Any]:
    """Resolve an identity to its tier across BOTH sovereignty chains.

    overlord   ⟸ evm_address == bankon.eth (SHADOW_OVERLORD_ADDRESS)
    overseer   ⟸ algo_address ∈ {mindx.algo} (MINDX_ALGO_ADDRESS / MINDX_OVERSEER_ADDRESSES)
    model/agent⟸ explicit role
    member     ⟸ owns a *.bankon.eth subname (is_member)
    participant⟸ any connected address; public otherwise.
    """
    evm = (evm_address or "").strip().lower()
    algo = (algo_address or "").strip().upper()
    tier = "public"
    if evm and _overlord_addr() and evm == _overlord_addr():
        tier = "overlord"
    elif algo and algo in _overseer_algo_addrs():
        tier = "overseer"
    elif (role or "").lower() in ("agent", "model"):
        tier = role.lower()
    elif is_member:
        tier = "member"
    elif evm or algo:
        tier = "participant"
    return {
        "tier": tier,
        "rank": rank(tier),
        "how": _HOW.get(tier, ""),
        "is_overlord": tier == "overlord",
        "is_overseer": tier == "overseer",
        "is_member": rank(tier) >= rank("member"),
        "chain": OVERLORD_CHAIN if tier == "overlord" else OVERSEER_CHAIN if tier == "overseer" else None,
        "next": next_tier(tier),
        "ladder": LADDER,
    }


def summary() -> Dict[str, Any]:
    """The hierarchy at a glance — for the public /insight/hierarchy surface."""
    return {
        "ladder": LADDER,
        "apex": {
            "overlord": {"identity": "bankon.eth", "chain": OVERLORD_CHAIN,
                         "configured": bool(_overlord_addr())},
            "overseer": {"identity": "mindx.algo", "chain": OVERSEER_CHAIN,
                         "configured": bool(_overseer_algo_addrs())},
        },
        "note": "Two sovereignty chains, one ladder: the OVERLORD (bankon.eth, EVM) creates OVERSEERs "
                "(mindx.algo, Algorand); members hold *.bankon.eth subnames.",
    }
