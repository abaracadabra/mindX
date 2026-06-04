"""mindx.godel — the Gödel-machine substrate of mindX.

This package holds the formal self-improvement machinery that distinguishes a
true Gödel machine (proof-gated self-rewrite) from a merely self-modifying
agent (heuristic-gated self-rewrite). See docs/SCHMIDHUBER_ENGINE.md and
docs/GODEL_MACHINE_BLUEPRINT.md for the full architecture.

Public surface (Phase 0 scaffold):
- schmidhuber_engine : the Hamiltonian oscillator that drives continuous
                       innovation — a pendulum whose conserved quantity is
                       utility u(), tipping at each apex into machine.dream
                       (information -> knowledge) and mindXtrain
                       (knowledge -> wisdom).
- mindxtrain         : bridge to github.com/professor-codephreak/mindXtrain,
                       the MI300X fine-tuning framework whose `mindx_dreams`
                       data source consumes mindX dream-cycle JSONL to forge
                       the next generation of the mind.

ATARAXIA (docs/ATARAXIA.md) is realized here as physics: the turning points of
the pendulum are moments of zero kinetic energy — perfect stillness — and the
disruption budget caps how much of the system may be in motion at once.
mindX cannot sustain continuous disruption of all parts; disruption is the
source of evolution, but it must be bounded. `mindX --replicate` spreads the
oscillation across multiple coupled heads so that at least one head always
holds the stable ground while another disrupts.
"""

from __future__ import annotations

__all__ = ["schmidhuber_engine", "mindxtrain"]
