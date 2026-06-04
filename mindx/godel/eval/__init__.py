"""mindx.godel.eval — the Gödel-machine self-audit.

Phase 0 of docs/GODEL_EVAL_BLUEPRINT.md. Computes the Gödel Machine Index
(GMI): a transparent, falsifiable scorecard of whether mindX is (or is not) a
Gödel machine. Honest by construction — it reports what is actually measured
(rationale coherence) versus what a Gödel machine requires (a machine-checked
proof of utility increase), and never overstates.

Pure stdlib, defensive (never raises), CPU-cheap — it only *reads* logs.
"""

from __future__ import annotations

from .gmi import compute_gmi

__all__ = ["compute_gmi"]
