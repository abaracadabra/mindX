"""prover — builds checkable certificates and records the ones that verify.

This is the (untrusted) producer side. It constructs a ProofCertificate for a
modest, precisely-labeled claim, hands it to the trusted checker, and records
it to the certificate ledger ONLY if the checker accepts. The kernel — not the
prover — is the authority; the prover can be wrong without compromising
soundness, because nothing reaches the ledger as "valid" unless the checker
said so.

Phase 2 emits one obligation class: *recorded-utility non-regression* — a
genuinely checkable arithmetic claim over measured rationals. The label states
exactly what that does and does not mean (it is not a claim about a formal
utility function — that is Phase 3).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from .checker import check_certificate
from .proof_ir import Claim, Obligation, Proof, ProofCertificate

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CERT_LEDGER = PROJECT_ROOT / "data" / "godel" / "certificates.jsonl"


def build_utility_certificate(
    *,
    target: str,
    u_before: str,
    u_after: str,
    alignment: Optional[str] = None,
    alignment_floor: str = "1/2",
    cert_id: Optional[str] = None,
) -> ProofCertificate:
    """Construct a certificate asserting recorded utility did not regress
    (and, if given, that alignment clears its floor). Values are exact rational
    strings ("0.82", "3/4", …) — never floats."""
    conjuncts = [
        Obligation(op="ge", terms={"u_after": "1", "u_before": "-1"}, const="0"),
    ]
    bindings = {"u_after": str(u_after), "u_before": str(u_before)}
    if alignment is not None:
        conjuncts.append(
            Obligation(op="ge", terms={"alignment": "1"},
                       const="-" + str(alignment_floor)))
        bindings["alignment"] = str(alignment)
    label = ("Proof that the RECORDED utility proxy did not regress across this "
             "change (u_after - u_before >= 0)"
             + (", and recorded alignment clears its floor" if alignment is not None else "")
             + ". This is a checked arithmetic derivation over measured rationals "
               "— not a claim about a formal utility function (Phase 3).")
    return ProofCertificate(
        cert_id=cert_id or f"cert_{int(time.time()*1000)}",
        target=target, claim=Claim(conjuncts=conjuncts),
        proof=Proof(bindings=bindings), label=label,
        meta={"created_at": time.time(), "obligation_class": "utility_nonregression"},
    )


def build_acceptance_certificate(
    *,
    target: str,
    critique_score: str,
    threshold: str,
    syntax_ok: bool,
    selftests_ok: Optional[bool] = None,
    cert_id: Optional[str] = None,
) -> ProofCertificate:
    """Certificate that a self-improvement met its acceptance criteria:
    critique_score - threshold >= 0, syntax passed, and (for self-edits) self
    tests passed. This is exactly the gate condition in
    self_improve_agent.run_self_improvement_cycle, re-expressed as a
    kernel-checkable proof over exact rationals (booleans encoded as 1/0)."""
    conjuncts = [
        Obligation(op="ge", terms={"critique": "1"}, const="-" + str(threshold)),
        Obligation(op="ge", terms={"syntax_ok": "1"}, const="-1"),
    ]
    bindings = {"critique": str(critique_score),
                "syntax_ok": "1" if syntax_ok else "0"}
    if selftests_ok is not None:
        conjuncts.append(Obligation(op="ge", terms={"selftests_ok": "1"}, const="-1"))
        bindings["selftests_ok"] = "1" if selftests_ok else "0"
    label = ("Proof that this accepted self-modification met its recorded "
             "acceptance criteria (critique >= threshold, syntax check passed"
             + (", self-tests passed" if selftests_ok is not None else "")
             + "). A checked derivation over the gate's own measured values — "
               "not a claim that the change is globally optimal (Phase 3).")
    return ProofCertificate(
        cert_id=cert_id or f"accept_{int(time.time()*1000)}",
        target=target, claim=Claim(conjuncts=conjuncts),
        proof=Proof(bindings=bindings), label=label,
        meta={"created_at": time.time(), "obligation_class": "acceptance_criteria"},
    )


def record_proof_gated_change(cert: ProofCertificate) -> dict:
    """Check the certificate; append to the ledger ONLY if it verifies.
    Returns the checker verdict augmented with {recorded}."""
    verdict = check_certificate(cert)
    recorded = False
    if verdict.get("valid"):
        try:
            CERT_LEDGER.parent.mkdir(parents=True, exist_ok=True)
            row = cert.to_dict()
            row["_verdict"] = verdict
            row["_recorded_at"] = time.time()
            with CERT_LEDGER.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            recorded = True
        except Exception:
            recorded = False
    out = dict(verdict)
    out["recorded"] = recorded
    return out


def load_certificates(limit: int = 1000) -> list[dict]:
    """Load recorded certificates (newest last). Defensive."""
    if not CERT_LEDGER.exists():
        return []
    try:
        rows = []
        for ln in CERT_LEDGER.read_text(encoding="utf-8").splitlines()[-limit:]:
            ln = ln.strip()
            if ln:
                try:
                    rows.append(json.loads(ln))
                except Exception:
                    continue
        return rows
    except Exception:
        return []
