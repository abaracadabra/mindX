"""proof_ir — the serialized proof terms the kernel checks.

A Claim is a conjunction of Obligations. Each Obligation is a linear-rational
comparison against zero:

    sum(coef_i * quantity_i) + const   OP   0          OP ∈ {ge, gt, eq}

A Proof binds each named quantity to an exact rational value (the premises). A
ProofCertificate ties a target (what changed) to a Claim and its Proof, plus a
precise English `label` of exactly what is (and isn't) being asserted.

Everything serializes to/from plain JSON dicts so the (huge, evolving) producer
and the (tiny, frozen) checker stay decoupled. Rationals travel as strings
("p/q" or decimal) and are parsed with fractions.Fraction by the checker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Obligation:
    """A linear-rational comparison: Σ coef·qty + const  OP  0."""
    op: str                          # "ge" | "gt" | "eq"
    terms: dict[str, str]            # quantity name -> rational coefficient (str)
    const: str = "0"                 # rational constant (str)

    def to_dict(self) -> dict:
        return {"op": self.op, "terms": dict(self.terms), "const": self.const}

    @staticmethod
    def from_dict(d: dict) -> "Obligation":
        return Obligation(op=str(d.get("op", "")),
                          terms={str(k): str(v) for k, v in (d.get("terms") or {}).items()},
                          const=str(d.get("const", "0")))


@dataclass
class Claim:
    """A conjunction of obligations (all must hold)."""
    conjuncts: list[Obligation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"conjuncts": [o.to_dict() for o in self.conjuncts]}

    @staticmethod
    def from_dict(d: dict) -> "Claim":
        return Claim(conjuncts=[Obligation.from_dict(o)
                                for o in (d.get("conjuncts") or [])])


@dataclass
class Proof:
    """Premises: each named quantity bound to an exact rational (as a string)."""
    bindings: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"bindings": dict(self.bindings)}

    @staticmethod
    def from_dict(d: dict) -> "Proof":
        return Proof(bindings={str(k): str(v)
                               for k, v in (d.get("bindings") or {}).items()})


@dataclass
class ProofCertificate:
    """A change + the claim it carries + the proof of that claim."""
    cert_id: str
    target: str
    claim: Claim
    proof: Proof
    label: str = ""                  # precise English: exactly what is asserted
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "cert_id": self.cert_id, "target": self.target,
            "claim": self.claim.to_dict(), "proof": self.proof.to_dict(),
            "label": self.label, "meta": self.meta,
        }

    @staticmethod
    def from_dict(d: dict) -> "ProofCertificate":
        return ProofCertificate(
            cert_id=str(d.get("cert_id", "")),
            target=str(d.get("target", "")),
            claim=Claim.from_dict(d.get("claim") or {}),
            proof=Proof.from_dict(d.get("proof") or {}),
            label=str(d.get("label", "")),
            meta=d.get("meta") or {},
        )
