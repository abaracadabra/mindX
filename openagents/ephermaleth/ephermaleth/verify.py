# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""ephermaleth.verify — verify an attestation chain with public keys only.

No trust required, only recovery: for every signed link, recover the EIP-191
signer and confirm it equals the link's address (and the *registered* identity
when a registry is supplied); confirm the hash linkage (prev / link_hash) is
intact and each challenge reconstructs byte-for-byte. Unsigned links are
reported (not fatal) so the verdict is honest about which seats signed.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .chain import build_challenge, sha256_hex
from .signer import recover_signer


def verify_chain(chain: Dict[str, Any],
                 registry: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Verify a serialized attestation chain end to end. Returns a structured
    report: per-link verdicts + overall ``valid`` (intact AND every signed link
    recovers to its address AND every registered identity matches)."""
    registry = registry or {}
    links: List[Dict[str, Any]] = chain.get("links", []) if isinstance(chain, dict) else []
    chain_id = chain.get("chain_id", "")
    results: List[Dict[str, Any]] = []
    intact = True
    signed_ok = True
    registry_ok = True
    signed_count = 0
    prev = "0x0"

    for l in links:
        seq = l.get("seq"); role = l.get("role", ""); agent_id = l.get("agent_id", "")
        act = l.get("act", ""); payload = l.get("payload_sha256", "")
        link_prev = l.get("prev", ""); challenge = l.get("challenge", "")
        signature = l.get("signature"); address = l.get("address")
        claimed_signed = bool(l.get("signed"))

        challenge_ok = (challenge == build_challenge(
            chain_id, seq, role, agent_id, act, payload, link_prev))
        linkage_ok = (link_prev == prev)
        lh_ok = (sha256_hex(challenge + "|" + (signature or "UNSIGNED")) == l.get("link_hash"))

        recovered = sig_ok = reg_ok = None
        if claimed_signed and signature:
            recovered = recover_signer(challenge, signature)
            sig_ok = (recovered is not None and address is not None
                      and recovered.lower() == str(address).lower())
            signed_count += 1
            if not sig_ok:
                signed_ok = False
            reg_addr = registry.get(agent_id)
            if reg_addr:
                reg_ok = (str(address).lower() == reg_addr.lower())
                if not reg_ok:
                    registry_ok = False

        if not (challenge_ok and linkage_ok and lh_ok):
            intact = False
        results.append({
            "seq": seq, "role": role, "agent_id": agent_id, "act": act,
            "signed": claimed_signed, "challenge_ok": challenge_ok,
            "linkage_ok": linkage_ok, "link_hash_ok": lh_ok, "recovered": recovered,
            "signature_ok": sig_ok, "registered_match": reg_ok, "address": address,
            "valid": challenge_ok and linkage_ok and lh_ok and (sig_ok in (None, True)),
        })
        prev = l.get("link_hash", "")

    return {
        "chain_id": chain_id, "links": len(links), "signed_links": signed_count,
        "unsigned_links": len(links) - signed_count, "chain_intact": intact,
        "signatures_valid": signed_ok, "registry_match": registry_ok,
        "valid": intact and signed_ok and registry_ok, "results": results,
    }


def extract_chain_from_html(html: str) -> Optional[Dict[str, Any]]:
    """Pull an embedded chain JSON back out of rendered HTML (a
    ``<script class="ephermaleth-chain">`` or ``mindx-provenance-chain`` block)."""
    import json
    m = re.search(
        r"<script[^>]*class=\"(?:ephermaleth-chain|mindx-provenance-chain)\"[^>]*>(.*?)</script>",
        html or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


__all__ = ["verify_chain", "extract_chain_from_html"]
