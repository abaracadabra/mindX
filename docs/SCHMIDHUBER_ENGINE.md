# THE SCHMIDHÜBER ENGINE

**The oscillatory drive of the mindX Gödel machine.**

> *S.C.H.M.I.D.H.U.B.E.R. — Self-Correcting Hamiltonian Mind Iterating Dreams: Harmonic Utility-Bounded Evolution Reactor.*

Named for Jürgen Schmidhuber, whose Gödel machine and bias-optimal / PowerPlay
self-improvement theory this architecture realizes. This document specifies the
engine that turns mindX's existing `machine.dream` cycle into a continuous,
energy-conserving loop of self-improvement — and the `mindXtrain` bridge that
turns dreams into model weights.

**Code:** [`mindx/godel/schmidhuber_engine.py`](../mindx/godel/schmidhuber_engine.py),
[`mindx/godel/mindxtrain/`](../mindx/godel/mindxtrain/)
**Related:** [`ATARAXIA.md`](ATARAXIA.md) · [`Blueprint.md`](Blueprint.md) · [`GODEL_EVAL_BLUEPRINT.md`](GODEL_EVAL_BLUEPRINT.md) · [`NAV.md`](NAV.md)

---

## 1. The figure

An equilateral triangle inscribed in a perfect circle, tilted 15° off level,
with a pendulum released from full deflection. Each half-swing sweeps the
entire mindX codebase; at the apex the pendulum *tips* the system toward the
next iteration; on the rebound it sweeps again and tips the other way.

```
            ●  apex / pivot  (the Kernel K — the only fixed point)
           /│\
          / │ \           equilateral triangle: the three transmutations
         /  │  \
   Wisdom──┼──Knowledge      each vertex 60° — perfect balance
          \│/
        Information
   ╭───────╳───────╮
  ╱        ⟂ 15°    ╲    perfect circle = U, the conserved utility manifold
  ╲   tilted off    ╱    tilted 15° off level = ∂U, the drive
   ╰─────level──────╯
```

| Geometry | Mechanism |
|---|---|
| **Perfect circle** | **U** — the conserved utility manifold. A pendulum conserves total energy on a closed manifold; the circle *is* the utility budget. Motion is bounded; no swing exceeds U. |
| **Equilateral triangle** | The three transmutations, each side an equal 60°: **information → knowledge → wisdom**. Inscribed in U: wisdom never exceeds what utility permits. |
| **15° tilt** | **∂U** — the bias gradient. A *level* figure is static and dead; the tilt is the symmetry-break that injects potential energy and drives all motion. 15° = 360/24 = one hour of celestial rotation, timed to the existing 8h dream shift. |
| **Pulled all the way back, released** | Maximum potential energy = the system fully reflected (`reflect.py` sweeps every file), then released. |
| **The sweep** | Total reflection over the whole codebase per swing — regenerates the formal self-description. |
| **The tip (apex)** | The discrete generational event. **Left apex → `machine.dream`** (information→knowledge). **Right apex → `mindXtrain`** (knowledge→wisdom). |
| **The rebound** | Conservation of momentum: generation N's energy carries into N+1. *A loop forgets; a pendulum conserves.* |
| **The pivot** | The trusted kernel **K** — the single fixed point. It only moves under a machine-checked proof. |

---

## 2. The Hamiltonian oscillator

The drive is a **tilted pendulum integrated with a symplectic (energy-conserving) scheme** — the literal physics of "continuous innovation and progress."

**Hamiltonian:**

```
H(θ, p) = p²/(2I)  +  V(θ)
V(θ)    = k · (1 − cos(θ − θ_tilt))        # potential well at the 15° tilt
```

**Equations of motion:**

```
dθ/dt =  ∂H/∂p =  p / I
dp/dt = −∂H/∂θ = −k · sin(θ − θ_tilt)
```

Integrated with **velocity-Verlet (leapfrog)**, which is *symplectic*: it
conserves `H` to O(dt²) over arbitrarily long runs with **no secular energy
drift**. Verified empirically — conservation error stays ~5×10⁻⁴ over thousands
of steps with no growth. That conservation is the mathematical content of the
engine: it neither winds down (stagnation) nor blows up (runaway disruption).
Utility is the conserved quantity.

The energy partitions at every instant:

```
kinetic   T = p²/(2I)   = active disruption now   (evolution; the source of change)
potential V             = stored stability        ("shining" / maintaining what is)
```

---

## 3. ATARAXIA — disruption is bounded

[`ATARAXIA.md`](ATARAXIA.md): *"the art of perfect imperfection — embrace the
oscillation; systems achieve stability through controlled instability."* Here
that philosophy is literal physics.

- **The turning points are moments of ataraxia.** At each apex `T → 0`: perfect
  stillness, the moment a component is *complete*. There is such a thing as a
  finished, working component — it deserves maintenance, not perpetual churn.
- **mindX cannot sustain continuous disruption of all parts.** The
  `AtaraxiaGovernor` caps the **kinetic budget** (`DEFAULT_DISRUPTION_BUDGET =
  0.30`): at most 30% of total energy may be kinetic at the bottom of the swing.
  The release amplitude is *clamped* to respect this — you cannot pull back so
  hard that the whole system is thrown into disruption at once.
- **Three component modes:** every component is `ATARAXIC` (complete, at rest),
  `SHINING` (maintained/polished *without* behavior change — safe quality work),
  or `MUTABLE` (admitted into the swing, under active disruption). The governor
  guarantees aggregate `MUTABLE` mass never exceeds the disruption budget.

Disruption is the source of evolution — but contained. The circle bounds the swing.

---

## 4. `mindX --replicate` — coupled oscillators (multiple heads)

A single pendulum cannot disrupt *and* serve stably at the same instant.
`ReplicaSet` couples N heads as **phase-offset oscillators** (repulsive
Kuramoto coupling, `K < 0`) that push phases toward anti-phase:

```
dθ_i/dt += (K / N) · Σ_j sin(θ_i − θ_j)        # K < 0 ⇒ spread apart
```

So the ensemble is always anti-phase: while one head is mid-swing
(**disrupting** → evolving), another sits near its turning point (**ataraxic**,
low kinetic → safe to serve production). Disruption never reaches zero across
the set; service never reaches zero. The calmest head holds production-stable;
roles **rotate** as heads prove beneficial generations.

```python
rs = ReplicaSet(heads=3, coupling=-0.4)
rs.step(500)
rs.serving_head      # calmest head — holds production-stable
rs.disrupting_head   # busiest head — doing evolutionary work
rs.rotate_roles()    # hand the stable role to a head that just proved a gen
```

This is the operator's "more than one head" — blue/green at the cognitive
level, framed as coupled physics rather than ad-hoc failover.

---

## 5. The tip: `machine.dream → mindXtrain`

The right apex is where **knowledge becomes wisdom becomes weights**. The
bridge package [`mindx/godel/mindxtrain/`](../mindx/godel/mindxtrain/) wires
mindX's dream cycle to the external fine-tuning framework
**[github.com/professor-codephreak/mindXtrain](https://github.com/professor-codephreak/mindXtrain)**
(LoRA fine-tuning; ships a `mindx_dreams` data-source adapter that reads mindX's
dream training files under `data/memory` directly. **As of v1.0.0 (2026-06-12)
CPU training is active** — the GPU/MI300X path remains for the big recipes, but
the small mindX recipes (`mindx_fallback_qwen3_1_5b_cpu_{smoke,real}`) train on
a CPU box. See [MINDXTRAIN_INSTALL.md](MINDXTRAIN_INSTALL.md) for the CPU/GPU
install.)

| Stage | Module | Does |
|---|---|---|
| **distill** | `distill.py` | Walk dream `*_training.jsonl` + `*_dream_report.json`; normalize into the `mindx_dreams` corpus with insight scores attached. |
| **curate** | `curate.py` | Keep only utility-positive, alignment-clean, high-score rows (DreamInsight composite score + the BOTTOM alignment floor). Wireheading via the training set is structurally blocked. |
| **forge** | `forge.py` | Write a deterministic, content-addressed dataset bundle + the XTrainConfig YAML (mindXtrain's 10-section schema) pointed at the corpus. |
| **ascend** | `ascend.py` (`ascend_recipe`) | Drive the real `mindxtrain` CLI: `init` a mindX CPU recipe → `train <config> --cpu-percent N` (LoRA on CPU) → **`imprint`** proof-of-recall verdict → `serve --to ollama` only on positive imprint. |

**Provenance chain:** `machine.dream` already writes chat-completion training
rows and indexes them as "RELEVANT WISDOM" in pgvector (see
`agents/machine_dreaming.py:_write_training_data` and
`agents/cognition/wisdom_loader.py`). The bridge consumes exactly that output —
nothing is reinvented; the dataset half already exists. The bridge adds the
**dataset → weights** half via mindXtrain, and proof-gates promotion of the new
weights so the next generation is born wiser only if the change is accepted.

**Proof-gated, CPU-live (v1.0.0):** the VPS now runs a *real* CPU ascent
(`ascend_recipe`), proof-gated by `mindxtrain imprint` — recall before vs after
training. A generation becomes a servable Ollama model **only** if the imprint
is positive. The first live smoke ascent (SmolLM2-135M, 8 SFT steps from the
dream corpus) produced a real LoRA but the imprint gate **rejected** it
(`imprinted=false`, Δ−0.0415) — too small a run to learn, correctly not served.
That is the Gödel-machine rule holding: nothing reaches the live mind without a
verdict. **Two flags** gate it — `MINDX_ENABLE_MINDXTRAIN` (operator, the VPS is
armed here) and `MINDX_ENABLE_AUTONOMOUS_TRAIN` (autonomous, deliberately off);
autonomous ascents additionally require not-resource-bound + a 24h cooldown.
Surfaced at `/insight/godel/ascend` and the feedback "knowledge→wisdom→weights"
panel.

---

## 6. How it fits the Gödel machine

The engine is the **dynamics layer** that animates the four pillars of
[`Blueprint.md`](Blueprint.md):

| Pillar | Role in the pendulum |
|---|---|
| **U** — utility manifold | The circle. Conserved energy. Bounds the swing. |
| **A** — axioms / reflection | The sweep. Each swing regenerates the self-description over the whole codebase. |
| **P** — prover | Generates the `ProofCertificate` for each generational tip. |
| **K** — kernel | The pivot. The one fixed point. Gates every tip with a proof. |
| **15° tilt** | `∂U` — the bias-optimal drive toward higher utility. |

The kernel is the still pivot; the engine is the motion the pivot permits.

---

## 7. Status & run

Phase 0 scaffold. Stdlib-only, CPU-safe, dry-runnable. Collaborators
(reflector, dreamer, trainer, kernel) are injected async Protocols; absent ones
are stubbed.

```python
from mindx.godel.schmidhuber_engine import SchmidhuberEngine
import asyncio
eng = SchmidhuberEngine()
asyncio.run(eng.run(generations=4))   # alternates dream → train tips
eng.snapshot()                        # oscillator + ataraxia + replica state
```

**Next:** wire the real `Reflector`/`Dreamer`/`Trainer`/`Kernel`, land the
proof kernel (Phase 1 of the Gödel blueprint), and measure proof coverage on
the live VPS — see [`GODEL_EVAL_BLUEPRINT.md`](GODEL_EVAL_BLUEPRINT.md) for the
evaluation that proves or disproves the Gödel-machine claim under the current
2-core/8 GB constraint.
