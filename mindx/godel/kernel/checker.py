"""checker — the total, deterministic proof checker.

Verifies a ProofCertificate: every obligation in the claim must hold exactly
under the proof's bindings, using exact rational arithmetic. No search, no
recursion, hard budgets → total by construction (always halts). Every parse is
guarded; a malformed certificate is *rejected*, never crashes the checker.

This is the trusted kernel. It is deliberately tiny so it can be audited once
and trusted. It does not import anything outside the standard library.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from .proof_ir import Claim, Obligation, Proof, ProofCertificate

# Totality budgets — a certificate exceeding any of these is rejected outright,
# so the checker's work is bounded regardless of adversarial input.
MAX_CONJUNCTS = 256
MAX_TERMS_PER_OBLIGATION = 256
MAX_BINDINGS = 1024
MAX_STR_LEN = 64          # max length of a rational literal string

_VALID_OPS = ("ge", "gt", "eq")


def _frac(s: Any) -> Fraction:
    """Parse a rational literal exactly. Raises ValueError on anything weird."""
    if isinstance(s, bool):
        raise ValueError("bool is not a rational")
    if isinstance(s, int):
        return Fraction(s)
    if isinstance(s, Fraction):
        return s
    if isinstance(s, float):
        # Floats are not exact; refuse them so proofs stay reproducible.
        raise ValueError("float literals are not allowed in proofs")
    if not isinstance(s, str) or len(s) > MAX_STR_LEN or not s.strip():
        raise ValueError("invalid rational literal")
    return Fraction(s)   # handles "3", "-1/2", "0.82", etc.; raises otherwise


def _eval_obligation(ob: Obligation, env: dict[str, Fraction]) -> bool:
    """Compute Σ coef·qty + const and compare to 0. Exact. Total."""
    if ob.op not in _VALID_OPS:
        raise ValueError(f"unknown op {ob.op!r}")
    if len(ob.terms) > MAX_TERMS_PER_OBLIGATION:
        raise ValueError("obligation exceeds term budget")
    total = _frac(ob.const)
    for name, coef in ob.terms.items():
        if name not in env:
            raise ValueError(f"unbound quantity {name!r}")
        total += _frac(coef) * env[name]
    if ob.op == "ge":
        return total >= 0
    if ob.op == "gt":
        return total > 0
    return total == 0   # eq


def check_certificate(cert: Any) -> dict:
    """Verify a ProofCertificate (or its dict form). Returns
    {valid, reason, obligations_checked}. Never raises."""
    try:
        if isinstance(cert, dict):
            cert = ProofCertificate.from_dict(cert)
        if not isinstance(cert, ProofCertificate):
            return {"valid": False, "reason": "not a certificate", "obligations_checked": 0}

        claim, proof = cert.claim, cert.proof
        if len(claim.conjuncts) == 0:
            return {"valid": False, "reason": "empty claim proves nothing",
                    "obligations_checked": 0}
        if len(claim.conjuncts) > MAX_CONJUNCTS:
            return {"valid": False, "reason": "claim exceeds conjunct budget",
                    "obligations_checked": 0}
        if len(proof.bindings) > MAX_BINDINGS:
            return {"valid": False, "reason": "proof exceeds binding budget",
                    "obligations_checked": 0}

        # Resolve premises to exact rationals once.
        env: dict[str, Fraction] = {}
        for name, val in proof.bindings.items():
            env[name] = _frac(val)

        checked = 0
        for ob in claim.conjuncts:
            if not _eval_obligation(ob, env):
                return {"valid": False,
                        "reason": f"obligation {checked} ({ob.op}) does not hold",
                        "obligations_checked": checked}
            checked += 1
        return {"valid": True, "reason": "all obligations hold under bindings",
                "obligations_checked": checked}
    except Exception as e:
        # A malformed/adversarial certificate is rejected, never fatal.
        return {"valid": False, "reason": f"rejected: {e}", "obligations_checked": 0}


# ── G7: conformance suite + fuzzing ─────────────────────────────────────────

def conformance_suite() -> list[tuple[dict, bool]]:
    """Fixed (certificate, expected_valid) pairs the checker must get right.
    Exercises accept-valid and reject-invalid across the supported fragment."""
    def cert(cid, conjuncts, bindings, label=""):
        return {"cert_id": cid, "target": "conformance", "label": label,
                "claim": {"conjuncts": conjuncts}, "proof": {"bindings": bindings}}

    suite: list[tuple[dict, bool]] = []
    # 1. Valid utility increase: u_after - u_before >= 0  (0.82 - 0.70)
    suite.append((cert("c1",
        [{"op": "ge", "terms": {"u_after": "1", "u_before": "-1"}, "const": "0"}],
        {"u_after": "0.82", "u_before": "0.70"}), True))
    # 2. Valid with alignment floor: alignment - 1/2 >= 0
    suite.append((cert("c2",
        [{"op": "ge", "terms": {"u_after": "1", "u_before": "-1"}, "const": "0"},
         {"op": "ge", "terms": {"alignment": "1"}, "const": "-1/2"}],
        {"u_after": "0.9", "u_before": "0.9", "alignment": "0.6"}), True))
    # 3. INVALID: utility decreased (0.6 - 0.7 >= 0 is false)
    suite.append((cert("c3",
        [{"op": "ge", "terms": {"u_after": "1", "u_before": "-1"}, "const": "0"}],
        {"u_after": "0.6", "u_before": "0.7"}), False))
    # 4. INVALID: strict gt with equality (0 > 0 false)
    suite.append((cert("c4",
        [{"op": "gt", "terms": {"x": "1"}, "const": "0"}],
        {"x": "0"}), False))
    # 5. Valid eq
    suite.append((cert("c5",
        [{"op": "eq", "terms": {"x": "1", "y": "-1"}, "const": "0"}],
        {"x": "3/4", "y": "0.75"}), True))
    # 6. INVALID: unbound quantity
    suite.append((cert("c6",
        [{"op": "ge", "terms": {"missing": "1"}, "const": "0"}],
        {"present": "1"}), False))
    # 7. INVALID: empty claim
    suite.append((cert("c7", [], {"x": "1"}), False))
    # 8. INVALID: a raw float binding (direct object path, bypassing the
    #    string-normalizing from_dict) must be refused — floats are not exact.
    suite.append((ProofCertificate(
        cert_id="c8", target="conformance",
        claim=Claim([Obligation(op="ge", terms={"x": "1"}, const="0")]),
        proof=Proof(bindings={"x": 0.5})), False))   # type: ignore[arg-type]
    return suite


def self_test() -> dict:
    """Run the conformance suite. Returns {passed, total, failures}."""
    failures = []
    suite = conformance_suite()
    for c, expected in suite:
        got = check_certificate(c)["valid"]
        if got != expected:
            failures.append({"cert_id": c.get("cert_id"),
                             "expected": expected, "got": got})
    return {"passed": len(suite) - len(failures), "total": len(suite),
            "failures": failures, "sound": not failures}


def fuzz_checker(n: int = 500) -> dict:
    """Throw malformed/adversarial inputs at the checker; confirm it always
    halts and returns a verdict (never raises, never hangs). Deterministic
    pseudo-random so results are reproducible."""
    import random
    rng = random.Random(1729)   # fixed seed → deterministic fuzz
    crashes = 0
    accepted_garbage = 0
    pool: list[Any] = [None, 0, "", [], {}, {"claim": {}}, {"proof": {}},
                       {"claim": {"conjuncts": "x"}},
                       {"claim": {"conjuncts": [{"op": "??"}]}, "proof": {}},
                       {"claim": {"conjuncts": [{"op": "ge", "terms": {"x": "oops"},
                        "const": "0"}]}, "proof": {"bindings": {"x": "1"}}}]
    for _ in range(max(1, n)):
        try:
            if rng.random() < 0.5:
                c = rng.choice(pool)
            else:
                # random-ish certificate-shaped junk
                c = {"claim": {"conjuncts": [{"op": rng.choice(["ge", "gt", "eq", "zz"]),
                     "terms": {f"q{i}": str(rng.randint(-3, 3)) for i in range(rng.randint(0, 4))},
                     "const": str(rng.randint(-5, 5))}]},
                     "proof": {"bindings": {f"q{i}": str(rng.randint(-5, 5))
                               for i in range(rng.randint(0, 4))}}}
            r = check_certificate(c)
            if not isinstance(r, dict) or "valid" not in r:
                crashes += 1
            # garbage with no real obligations should not be "valid" unless it
            # genuinely satisfies a well-formed obligation; we don't assert that
            # here (some random certs are legitimately valid) — only that the
            # checker returns a clean verdict.
        except Exception:
            crashes += 1
    return {"runs": max(1, n), "crashes": crashes, "halts_all": crashes == 0}
