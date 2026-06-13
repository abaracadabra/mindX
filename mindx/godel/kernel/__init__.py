"""mindx.godel.kernel — the trusted proof checker (Phase 2).

The Gödel-machine pivot: a tiny, total, deterministic checker that is the ONLY
thing allowed to certify a self-modification. It does not search for proofs
(intractable, offloaded) — it only *verifies* a finished proof term. That
asymmetry is why it can be small and trustworthy.

Phase 2 scope (docs/GODEL_EVAL_BLUEPRINT.md §6): the checker verifies claims in
quantifier-free linear-rational arithmetic with conjunction (a decidable
fragment of QF_LRA). A utility-increase certificate reduces to exactly this —
`u_after - u_before >= 0  ∧  alignment - floor >= 0  ∧  …` — once the measured
quantities are pinned as exact rationals.

HONESTY BOUNDARY: the checker proves the claim follows *from its premises*
(the bound quantities). It does not yet prove the premises faithfully reflect
reality — sensor integrity / a formal utility function U is Phase 3 (G5). So a
verified certificate today means "given these measured rationals, the stated
arithmetic obligation holds, exactly" — a real, sound derivation over a modest
claim, not a guarantee about the world.

Pure stdlib, exact arithmetic (fractions.Fraction), no dependencies.
"""

from __future__ import annotations

from .checker import (
    check_certificate,
    conformance_suite,
    fuzz_checker,
    self_test,
)
from .proof_ir import Claim, Obligation, Proof, ProofCertificate

__all__ = [
    "Obligation", "Claim", "Proof", "ProofCertificate",
    "check_certificate", "self_test", "fuzz_checker", "conformance_suite",
]
