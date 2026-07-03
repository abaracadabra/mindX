# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""ephermaleth.chain — a hash-linked, multi-signer attestation chain.

A protocol-enhancement primitive: an ordered chain of custody where each link is
signed by a *different* identity's wallet, and the whole chain is tamper-evident
so a stranger can verify the lineage with nothing but public keys. Think a tiny
blockchain of EIP-191 signatures — a "speech from the throne" carried through a
chain of command, a multi-party approval, a provenance trail.

Each link carries:
  • role / agent_id / act   — who, in what capacity, doing what
  • payload_sha256          — the artifact this link attests
  • prev                    — the previous link's ``link_hash`` (chains them)
  • challenge               — the exact, namespaced EIP-191 message that was signed
  • signature / address     — the signer's wallet signature + recovered address
  • link_hash               — sha256(challenge + signature), the ``prev`` of the next

Design (from the BANKON Vault):
  • the chain never holds a private key — it calls a pluggable ``Signer`` oracle;
  • the challenge string is namespaced + versioned (domain separation, like an
    HKDF ``info``), so a signature for one chain can't be replayed into another;
  • an identity without a key yields an *attested-but-unsigned* link (signed=False)
    rather than failing the chain — operationally transparent about which seats
    have lit up their keys.

Agnostic: no application imports. Bring your own ``Signer`` (see ``signer.py``)
and an optional ``registry`` of ``{agent_id: address}`` for identity checks.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, fields as _dc_fields
from typing import Any, Dict, List, Optional

from .signer import NullSigner, Signer

CHALLENGE_NS = "ephermaleth/v1"

# Characters that structure the challenge string. Encoding them out of every
# interpolated field value makes ``build_challenge`` INJECTIVE in its inputs —
# i.e. two different field-sets can never collapse to the same signed message,
# so a signature is bound to exactly one (chain, seq, role, agent, act, payload,
# prev) tuple. Without this, an identity like ``"a | agent=b"`` could smuggle a
# second field past the separators and reuse a signature. (Security: the signer
# always signs an unambiguous statement of what it is attesting.)
_UNSAFE = re.compile(r"[%|=\s]")


def _enc(v: Any) -> str:
    """Percent-encode the challenge's structural characters out of a field value.
    Readable for ordinary values (no special chars survive untouched)."""
    return _UNSAFE.sub(lambda m: f"%{ord(m.group(0)):02X}", str(v))


def sha256_hex(s: str) -> str:
    return "0x" + hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass
class ChainLink:
    seq: int
    role: str
    agent_id: str
    act: str
    payload_sha256: str
    prev: str
    challenge: str
    signature: Optional[str]
    address: Optional[str]
    signed: bool
    link_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_challenge(chain_id: str, seq: int, role: str, agent_id: str,
                    act: str, payload_sha256: str, prev: str) -> str:
    """The canonical, namespaced, INJECTIVE message a link's signer signs.

    Every variable field is percent-encoded (:func:`_enc`) so the structural
    separators can't be forged into a value — guaranteeing a one-to-one mapping
    from field-tuple to signed string. Must be reconstructable byte-for-byte at
    verification time (verify_chain rebuilds it the same way)."""
    return (f"{CHALLENGE_NS} | chain={_enc(chain_id)} | seq={int(seq)} | "
            f"role={_enc(role)} | agent={_enc(agent_id)} | act={_enc(act)} | "
            f"payload={_enc(payload_sha256)} | prev={_enc(prev)}")


class AttestationChain:
    """A hash-linked, multi-signer attestation chain. Bring a ``Signer``."""

    def __init__(self, chain_id: str, *, signer: Optional[Signer] = None,
                 registry: Optional[Dict[str, str]] = None) -> None:
        self.chain_id = chain_id
        self.links: List[ChainLink] = []
        self._signer: Signer = signer or NullSigner()
        self._registry = dict(registry or {})

    @classmethod
    def anchored(cls, anchor: str, *, ts: int, signer: Optional[Signer] = None,
                 registry: Optional[Dict[str, str]] = None,
                 kind: str = "attestation") -> "AttestationChain":
        """Open a chain whose id is derived from an anchor string + a
        caller-supplied stamp (deterministic — no wall-clock inside)."""
        cid = sha256_hex(f"{kind}|{ts}|{sha256_hex(anchor)}")
        return cls(cid, signer=signer, registry=registry)

    def add_link(self, role: str, agent_id: str, act: str,
                 payload_sha256: str) -> ChainLink:
        """Append a link: build its challenge, ask the signer to sign as
        ``agent_id``, and hash-link it to the previous link. Unsigned when the
        signer has no key for that identity (the link still records the
        registered address when known, for later attestation)."""
        seq = len(self.links)
        prev = self.links[-1].link_hash if self.links else "0x0"
        challenge = build_challenge(self.chain_id, seq, role, agent_id, act,
                                    payload_sha256, prev)
        sig = addr = None
        signed = False
        res = self._signer(agent_id, challenge)
        if res:
            sig, addr = res
            signed = True
        if addr is None:
            addr = self._registry.get(agent_id)
        link_hash = sha256_hex(challenge + "|" + (sig or "UNSIGNED"))
        link = ChainLink(seq=seq, role=role, agent_id=agent_id, act=act,
                         payload_sha256=payload_sha256, prev=prev, challenge=challenge,
                         signature=sig, address=addr, signed=signed, link_hash=link_hash)
        self.links.append(link)
        return link

    def head(self) -> str:
        """The current head hash — the next link's ``prev`` (and a stable id for
        the chain's current state)."""
        return self.links[-1].link_hash if self.links else "0x0"

    def to_dict(self) -> Dict[str, Any]:
        return {"ns": CHALLENGE_NS, "chain_id": self.chain_id, "version": 1,
                "links": [l.to_dict() for l in self.links]}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AttestationChain":
        c = cls(d.get("chain_id", ""))
        allowed = {f.name for f in _dc_fields(ChainLink)}
        c.links = [ChainLink(**{k: v for k, v in l.items() if k in allowed})
                   for l in d.get("links", [])]
        return c


__all__ = ["AttestationChain", "ChainLink", "build_challenge", "sha256_hex",
           "CHALLENGE_NS"]
