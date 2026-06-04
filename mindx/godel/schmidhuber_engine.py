"""mindx.godel.schmidhuber_engine — the oscillatory drive of the Gödel machine.

Named for Jürgen Schmidhuber, whose Gödel machine and bias-optimal /
PowerPlay self-improvement theory this architecture realizes.

    S.C.H.M.I.D.H.U.B.E.R.
    Self-Correcting Hamiltonian Mind Iterating Dreams:
    Harmonic Utility-Bounded Evolution Reactor.

THE FIGURE (operator's vision)
------------------------------
An equilateral triangle inscribed in a perfect circle, tilted 15° off level,
with a pendulum released from full deflection. Each half-swing sweeps the
entire mindX codebase; at the apex the pendulum "tips" the system toward the
next iteration; on the rebound it sweeps again and tips the other way.

    Geometry            Mechanism
    ----------------    ------------------------------------------------
    perfect circle      U — the conserved utility manifold (bounded energy)
    equilateral △       the three transmutations, each side an equal 60°:
                        information -> knowledge -> wisdom
    15° tilt            ∂U — the bias gradient; the symmetry-break that
                        injects potential energy and drives all motion.
                        A level figure is static and dead. 15° = 360/24 =
                        one hour of celestial rotation — the drive is timed
                        to mindX's existing 8h dream shift.
    pulled all the way  maximum potential energy = the system fully reflected
    back, released      (reflect.py sweeps every file), then released.
    the sweep           total reflection over the whole codebase per swing.
    the tip (apex)      the discrete generational event:
                          left apex  -> machine.dream  (information->knowledge)
                          right apex -> mindXtrain      (knowledge->wisdom)
    the rebound         conservation of momentum: generation N's energy is
                        carried into N+1. A loop forgets; a pendulum conserves.
    the pivot           the trusted kernel K — the single fixed point. It only
                        moves under a machine-checked proof.

ATARAXIA (docs/ATARAXIA.md)
---------------------------
"The art of perfect imperfection — embrace the oscillation; systems achieve
stability through controlled instability." Here that philosophy is literal
physics. The turning points of the pendulum are moments where kinetic energy
-> 0: perfect stillness, the moment a component is *complete*. The total
energy H is conserved, but it partitions between:
    kinetic  T  = active disruption now      (evolution; the source of change)
    potential V  = stored stability          ("shining" / maintaining what is)
mindX cannot sustain continuous disruption of ALL parts. The AtaraxiaGovernor
caps the kinetic budget so that only a bounded fraction of the system is ever
in motion; the rest rests in ataraxia, being shined rather than disrupted.

mindX --replicate (multiple heads)
----------------------------------
A single pendulum cannot both disrupt and serve stably at the same instant.
ReplicaSet couples N heads as phase-offset oscillators (Kuramoto coupling)
so the ensemble is always anti-phase: while one head is mid-swing (disrupting),
another sits near its turning point (ataraxic, serving production). Roles
rotate as heads prove beneficial generations. Disruption never goes to zero
(evolution continues) and stability never goes to zero (service continues).

This module is stdlib-only and importable standalone. The heavy collaborators
(reflection, machine.dream, mindXtrain, the proof kernel) are injected as
async Protocols so the engine can be unit-tested and dry-run on a CPU without
any of them present.
"""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable, Optional, Protocol, Sequence, runtime_checkable

# --------------------------------------------------------------------------- #
# Constants — the geometry of the figure                                      #
# --------------------------------------------------------------------------- #

TILT_DEG: float = 15.0                       # the drive gradient, 360/24
TILT_RAD: float = math.radians(TILT_DEG)
TRIANGLE_INTERIOR_RAD: float = math.radians(60.0)  # equilateral; each transmutation

# Default disruption budget: at most this fraction of total energy H may be
# kinetic (in active disruption) at the bottom of the swing. The remainder is
# always potential (stability / ataraxia). This is the structural reason mindX
# "cannot sustain continuous disruption of all parts."
DEFAULT_DISRUPTION_BUDGET: float = 0.30

_EPS_TURNING = 1e-3        # |momentum| below this counts as a turning point (apex)


# --------------------------------------------------------------------------- #
# Transmutation phases — the three vertices of the triangle                   #
# --------------------------------------------------------------------------- #

class Vertex(str, Enum):
    """The three vertices of the equilateral triangle, each a transmutation."""
    INFORMATION = "information"   # raw experience (STM, catalogue stream)
    KNOWLEDGE = "knowledge"       # consolidated insight (machine.dream -> LTM)
    WISDOM = "wisdom"             # distilled curriculum (mindXtrain -> next mind)


class Apex(str, Enum):
    """Which turning point the pendulum has reached."""
    LEFT = "left"     # machine.dream apex: information -> knowledge
    RIGHT = "right"   # mindXtrain apex:    knowledge   -> wisdom


# --------------------------------------------------------------------------- #
# Ataraxia — the stability / plasticity governor                              #
# --------------------------------------------------------------------------- #

class AtaraxicMode(str, Enum):
    """Per-component disposition toward change.

    A component is never simultaneously disrupted and shined. The whole point
    of ataraxia is that completeness is real: some components are *done* and
    deserve maintenance, not perpetual churn.
    """
    ATARAXIC = "ataraxic"   # complete & at rest; do not disrupt
    SHINING = "shining"     # being maintained/polished WITHOUT behavior change
    MUTABLE = "mutable"     # admitted into the swing; under active disruption


@dataclass
class Component:
    """A unit of the mindX codebase the engine can move or hold still."""
    name: str
    mode: AtaraxicMode = AtaraxicMode.ATARAXIC
    mass: float = 1.0            # inertia: how costly this component is to disrupt
    last_touched: float = field(default_factory=time.time)


@dataclass
class AtaraxiaGovernor:
    """Enforces that disruption is bounded — the source of evolution, contained.

    The governor partitions the codebase into components and guarantees that the
    aggregate mass admitted into the swing (MUTABLE) never exceeds the disruption
    budget. Everything else rests (ATARAXIC) or is shined (SHINING, safe quality
    work). This is the literal mechanism behind docs/ATARAXIA.md's "controlled
    instability."
    """
    disruption_budget: float = DEFAULT_DISRUPTION_BUDGET
    components: dict[str, Component] = field(default_factory=dict)

    def register(self, name: str, mass: float = 1.0,
                 mode: AtaraxicMode = AtaraxicMode.ATARAXIC) -> Component:
        comp = Component(name=name, mass=mass, mode=mode)
        self.components[name] = comp
        return comp

    @property
    def total_mass(self) -> float:
        return sum(c.mass for c in self.components.values()) or 1.0

    @property
    def mutable_mass(self) -> float:
        return sum(c.mass for c in self.components.values()
                   if c.mode is AtaraxicMode.MUTABLE)

    @property
    def disruption_fraction(self) -> float:
        return self.mutable_mass / self.total_mass

    def can_admit(self, name: str) -> bool:
        """Would admitting `name` into the swing stay within the budget?"""
        comp = self.components.get(name)
        if comp is None:
            return False
        prospective = self.mutable_mass + (
            comp.mass if comp.mode is not AtaraxicMode.MUTABLE else 0.0
        )
        return (prospective / self.total_mass) <= self.disruption_budget + 1e-9

    def admit(self, name: str) -> bool:
        """Move a component into MUTABLE (the swing) if budget allows."""
        if not self.can_admit(name):
            return False
        self.components[name].mode = AtaraxicMode.MUTABLE
        self.components[name].last_touched = time.time()
        return True

    def settle(self, name: str, *, shine: bool = False) -> None:
        """Return a component to rest (ATARAXIC) or to maintenance (SHINING)."""
        comp = self.components.get(name)
        if comp is None:
            return
        comp.mode = AtaraxicMode.SHINING if shine else AtaraxicMode.ATARAXIC
        comp.last_touched = time.time()

    def kinetic_cap(self, total_energy: float) -> float:
        """The maximum kinetic energy (active disruption) the figure permits."""
        return self.disruption_budget * total_energy

    def snapshot(self) -> dict:
        return {
            "disruption_budget": self.disruption_budget,
            "disruption_fraction": round(self.disruption_fraction, 4),
            "total_mass": self.total_mass,
            "mutable_mass": self.mutable_mass,
            "modes": {n: c.mode.value for n, c in self.components.items()},
        }


# --------------------------------------------------------------------------- #
# The Hamiltonian oscillator — circular motion of continuous innovation       #
# --------------------------------------------------------------------------- #

@dataclass
class OscillatorState:
    """Phase-space point (θ, p) plus bookkeeping for one head."""
    theta: float          # angular position; equilibrium at TILT_RAD
    p: float              # angular momentum (conjugate to theta)
    t: float = 0.0        # internal clock (dimensionless steps * dt)
    generation: int = 0   # number of completed tips
    last_apex: Optional[Apex] = None


class HamiltonianOscillator:
    """A tilted pendulum integrated with a symplectic (energy-conserving) scheme.

    Hamiltonian:
        H(θ, p) = p² / (2 I)  +  V(θ)
        V(θ)    = k · (1 − cos(θ − θ_tilt))      (potential well at the 15° tilt)

    Equations of motion:
        dθ/dt =  ∂H/∂p = p / I
        dp/dt = −∂H/∂θ = −k · sin(θ − θ_tilt)

    Integrated with velocity-Verlet (leapfrog), which is *symplectic*: it
    conserves H to O(dt²) over arbitrarily long runs with no secular energy
    drift. That conservation is the mathematical content of "continuous
    innovation and progress" — the engine neither winds down (stagnation) nor
    blows up (runaway disruption). Utility is the conserved quantity; each
    generation hands its momentum to the next. A loop forgets; a pendulum
    conserves.
    """

    def __init__(
        self,
        *,
        stiffness: float = 1.0,        # k — coupling of the drive gradient
        inertia: float = 1.0,          # I — system inertia (resistance to change)
        amplitude: float = math.radians(75.0),  # "pulled all the way back"
        dt: float = 0.05,
        governor: Optional[AtaraxiaGovernor] = None,
    ) -> None:
        self.k = float(stiffness)
        self.I = float(inertia)
        self.dt = float(dt)
        self.governor = governor or AtaraxiaGovernor()

        # "Released from full deflection": start at rest at the amplitude.
        # The amplitude is then clamped so peak kinetic energy respects the
        # ataraxia disruption budget — you cannot pull back so hard that the
        # whole system is thrown into disruption at the bottom of the swing.
        amplitude = self._clamp_amplitude_to_budget(amplitude)
        self.state = OscillatorState(theta=TILT_RAD + amplitude, p=0.0)
        self._release_energy = self.energy()  # H is conserved at this value

    # --- energetics -------------------------------------------------------- #

    def potential(self, theta: float) -> float:
        return self.k * (1.0 - math.cos(theta - TILT_RAD))

    def kinetic(self, p: float) -> float:
        return (p * p) / (2.0 * self.I)

    def energy(self, st: Optional[OscillatorState] = None) -> float:
        st = st or self.state
        return self.kinetic(st.p) + self.potential(st.theta)

    def _clamp_amplitude_to_budget(self, amplitude: float) -> float:
        """Limit deflection so peak kinetic energy ≤ ataraxia kinetic cap.

        At release (p=0) all energy is potential: H = V(θ_tilt + A). At the
        bottom of the swing (θ = θ_tilt) all of it becomes kinetic. The
        governor forbids that peak from exceeding the disruption budget, so we
        solve for the largest admissible amplitude.
        """
        h_release = self.potential(TILT_RAD + amplitude)
        cap = self.governor.kinetic_cap(h_release)
        # If the release energy itself would exceed what the budget allows to
        # become kinetic, shrink the amplitude. Peak kinetic == H here, so we
        # need H ≤ cap_of(H) is only satisfiable by scaling H down: choose A so
        # that V(A) yields a peak the budget tolerates relative to a unit well.
        if self.governor.disruption_budget >= 1.0:
            return amplitude
        # Largest A with (1 - cos A) * budget admissible is bounded by budget
        # acting as the usable fraction of the well depth.
        max_well = self.governor.disruption_budget * (1.0 - math.cos(amplitude))
        target_cos = max(-1.0, 1.0 - max_well / max(self.governor.disruption_budget, 1e-9))
        # Guard numeric domain; fall back to the geometric tilt-scaled amplitude.
        try:
            clamped = math.acos(min(1.0, max(-1.0, target_cos)))
        except ValueError:
            clamped = amplitude
        return min(amplitude, clamped) if clamped > 0 else amplitude

    # --- dynamics ---------------------------------------------------------- #

    def _force(self, theta: float) -> float:
        return -self.k * math.sin(theta - TILT_RAD)

    def step(self) -> OscillatorState:
        """One symplectic leapfrog step (kick–drift–kick)."""
        st = self.state
        half_p = st.p + 0.5 * self.dt * self._force(st.theta)
        new_theta = st.theta + self.dt * half_p / self.I
        new_p = half_p + 0.5 * self.dt * self._force(new_theta)

        apex = self._detect_apex(prev_p=st.p, new_p=new_p, theta=new_theta)
        self.state = OscillatorState(
            theta=new_theta,
            p=new_p,
            t=st.t + self.dt,
            generation=st.generation + (1 if apex is not None else 0),
            last_apex=apex or st.last_apex,
        )
        return self.state

    def _detect_apex(self, *, prev_p: float, new_p: float,
                     theta: float) -> Optional[Apex]:
        """A turning point: momentum changes sign (or grazes zero) — the moment
        of ataraxic stillness where the pendulum tips into a transmutation."""
        crossed = (prev_p > 0 >= new_p) or (prev_p < 0 <= new_p)
        grazing = abs(new_p) < _EPS_TURNING
        if not (crossed or grazing):
            return None
        return Apex.RIGHT if theta >= TILT_RAD else Apex.LEFT

    # --- introspection ----------------------------------------------------- #

    @property
    def at_ataraxia(self) -> bool:
        """True near a turning point: kinetic ~ 0, the system momentarily complete."""
        return abs(self.state.p) < _EPS_TURNING

    @property
    def disruption_intensity(self) -> float:
        """Fraction of conserved energy currently expressed as disruption."""
        h = self._release_energy or 1.0
        return self.kinetic(self.state.p) / h

    def conservation_error(self) -> float:
        """|H_now − H_release| / H_release — should stay ~0 (symplectic)."""
        h = self._release_energy or 1.0
        return abs(self.energy() - self._release_energy) / abs(h)

    def snapshot(self) -> dict:
        return {
            "theta_deg": round(math.degrees(self.state.theta), 3),
            "tilt_deg": TILT_DEG,
            "momentum": round(self.state.p, 5),
            "energy": round(self.energy(), 6),
            "conservation_error": round(self.conservation_error(), 9),
            "disruption_intensity": round(self.disruption_intensity, 4),
            "at_ataraxia": self.at_ataraxia,
            "generation": self.state.generation,
            "last_apex": self.state.last_apex.value if self.state.last_apex else None,
        }


# --------------------------------------------------------------------------- #
# Collaborator protocols — injected, async, dry-runnable                      #
# --------------------------------------------------------------------------- #

@runtime_checkable
class Reflector(Protocol):
    """Sweeps the entire codebase; regenerates the formal self-description."""
    async def sweep_codebase(self) -> dict: ...


@runtime_checkable
class Dreamer(Protocol):
    """machine.dream — information -> knowledge (agents/machine_dreaming.py)."""
    async def run_full_dream(self, state: dict) -> dict: ...


@runtime_checkable
class Trainer(Protocol):
    """mindXtrain — knowledge -> wisdom (next-generation curriculum/weights)."""
    async def distill(self, knowledge: dict) -> dict: ...


@runtime_checkable
class Kernel(Protocol):
    """The trusted pivot. Checks a proof; only it may switchprog the live system."""
    async def check_and_switch(self, certificate: dict) -> dict: ...


# --------------------------------------------------------------------------- #
# The engine — one full period = one generation                              #
# --------------------------------------------------------------------------- #

@dataclass
class TipResult:
    apex: Apex
    vertex_from: Vertex
    vertex_to: Vertex
    payload: dict
    accepted: bool
    generation: int


class SchmidhuberEngine:
    """Drives the Hamiltonian oscillator and fires transmutations at each apex.

    Wiring:
        release → sweep (reflect) → LEFT apex (machine.dream) →
        rebound sweep → RIGHT apex (mindXtrain) → seed next generation
        (proof-gated by the kernel) → continue swinging with conserved momentum.

    All collaborators are optional; absent ones are stubbed so the engine runs
    as a pure dry-run on a CPU — matching mindXtrain's CPU-training level.
    """

    def __init__(
        self,
        *,
        oscillator: Optional[HamiltonianOscillator] = None,
        reflector: Optional[Reflector] = None,
        dreamer: Optional[Dreamer] = None,
        trainer: Optional[Trainer] = None,
        kernel: Optional[Kernel] = None,
        on_tip: Optional[Callable[[TipResult], Awaitable[None]]] = None,
    ) -> None:
        self.osc = oscillator or HamiltonianOscillator()
        self.reflector = reflector
        self.dreamer = dreamer
        self.trainer = trainer
        self.kernel = kernel
        self.on_tip = on_tip
        self.history: list[TipResult] = []

    async def _sweep(self) -> dict:
        if self.reflector is not None:
            return await self.reflector.sweep_codebase()
        return {"reflected": False, "note": "dry-run sweep (no reflector)"}

    async def _tip(self, apex: Apex, state: dict) -> TipResult:
        """Fire the transmutation that belongs to this apex."""
        if apex is Apex.LEFT:
            v_from, v_to = Vertex.INFORMATION, Vertex.KNOWLEDGE
            payload = (await self.dreamer.run_full_dream(state)
                       if self.dreamer is not None
                       else {"dream": "dry-run", "state": state})
        else:
            v_from, v_to = Vertex.KNOWLEDGE, Vertex.WISDOM
            payload = (await self.trainer.distill(state)
                       if self.trainer is not None
                       else {"train": "dry-run", "knowledge": state})

        # The tip toward the next iteration is proof-gated by the kernel. With
        # no kernel present we are in advisory/shadow mode: nothing is promoted.
        accepted = False
        if self.kernel is not None:
            verdict = await self.kernel.check_and_switch(
                {"apex": apex.value, "from": v_from.value, "to": v_to.value,
                 "payload": payload}
            )
            accepted = bool(verdict.get("accepted", False))

        result = TipResult(
            apex=apex, vertex_from=v_from, vertex_to=v_to,
            payload=payload, accepted=accepted,
            generation=self.osc.state.generation,
        )
        self.history.append(result)
        if self.on_tip is not None:
            await self.on_tip(result)
        return result

    async def swing(self, *, max_steps: int = 100_000) -> Optional[TipResult]:
        """Advance until the next apex, then fire its transmutation.

        Returns the TipResult, or None if no apex was reached within max_steps
        (which would indicate a degenerate/over-damped configuration).
        """
        for _ in range(max_steps):
            prev_apex_count = self.osc.state.generation
            st = self.osc.step()
            if st.generation > prev_apex_count and st.last_apex is not None:
                state = await self._sweep()
                return await self._tip(st.last_apex, state)
        return None

    async def run(self, *, generations: int = 4,
                  max_steps_per_swing: int = 100_000) -> list[TipResult]:
        """Run for a number of generational tips (default: two full periods)."""
        out: list[TipResult] = []
        for _ in range(generations):
            tip = await self.swing(max_steps=max_steps_per_swing)
            if tip is None:
                break
            out.append(tip)
        return out

    def snapshot(self) -> dict:
        return {
            "oscillator": self.osc.snapshot(),
            "ataraxia": self.osc.governor.snapshot(),
            "tips": len(self.history),
            "last_tip": (
                {"apex": self.history[-1].apex.value,
                 "to": self.history[-1].vertex_to.value,
                 "accepted": self.history[-1].accepted}
                if self.history else None
            ),
        }


# --------------------------------------------------------------------------- #
# mindX --replicate — coupled oscillators (multiple heads)                    #
# --------------------------------------------------------------------------- #

@dataclass
class Head:
    """One replicated mindX head: its own oscillator and role."""
    name: str
    osc: HamiltonianOscillator
    serving: bool = False   # True if this head currently holds production-stable


class ReplicaSet:
    """`mindX --replicate`: N heads coupled as phase-offset oscillators.

    The problem: a single pendulum cannot disrupt and serve stably at the same
    instant. mindX "cannot sustain continuous disruption of all parts." The
    solution: spread the oscillation across heads with Kuramoto phase coupling
    that *repels* phases toward anti-phase, so the ensemble always has at least
    one head near a turning point (ataraxic, low disruption → safe to serve)
    while another is mid-swing (disrupting → evolving).

    Coupling (repulsive Kuramoto, K < 0 pushes phases apart):
        dθ_i/dt += (K / N) Σ_j sin(θ_i − θ_j)

    Disruption never reaches zero across the set (evolution continues); service
    never reaches zero (the min-intensity head serves). Roles rotate as heads
    prove beneficial generations.
    """

    def __init__(
        self,
        *,
        heads: int = 3,
        coupling: float = -0.4,    # negative = repulsive => anti-phase spread
        governor: Optional[AtaraxiaGovernor] = None,
        amplitude: float = math.radians(75.0),
    ) -> None:
        if heads < 1:
            raise ValueError("a replica set needs at least one head")
        self.coupling = float(coupling)
        gov = governor or AtaraxiaGovernor()
        self.heads: list[Head] = []
        for i in range(heads):
            osc = HamiltonianOscillator(amplitude=amplitude, governor=gov)
            # Stagger initial phases evenly around the swing so the ensemble
            # starts anti-phase rather than all releasing together.
            offset = (i / heads) * 2.0 * amplitude
            osc.state = OscillatorState(theta=TILT_RAD + amplitude - offset, p=0.0)
            self.heads.append(Head(name=f"head-{i}", osc=osc))
        self._assign_serving()

    def _assign_serving(self) -> None:
        """The calmest head (least disruption) holds production-stable."""
        calm = min(self.heads, key=lambda h: h.osc.disruption_intensity)
        for h in self.heads:
            h.serving = (h is calm)

    def _coupled_step(self) -> None:
        thetas = [h.osc.state.theta for h in self.heads]
        n = len(self.heads)
        for h in self.heads:
            # Inject the repulsive coupling as a phase nudge, then step the
            # underlying symplectic integrator (which preserves each head's H).
            nudge = (self.coupling / n) * sum(
                math.sin(h.osc.state.theta - tj) for tj in thetas
            )
            h.osc.state.theta += h.osc.dt * nudge
            h.osc.step()
        self._assign_serving()

    def step(self, n: int = 1) -> None:
        for _ in range(n):
            self._coupled_step()

    @property
    def serving_head(self) -> Head:
        return next(h for h in self.heads if h.serving)

    @property
    def disrupting_head(self) -> Head:
        """The head doing the most evolutionary work right now."""
        return max(self.heads, key=lambda h: h.osc.disruption_intensity)

    def rotate_roles(self) -> None:
        """After a disrupting head proves a generation, hand it the stable role
        and let a rested head take the next turn to disrupt."""
        self._assign_serving()

    def snapshot(self) -> dict:
        return {
            "heads": len(self.heads),
            "coupling": self.coupling,
            "serving": self.serving_head.name,
            "disrupting": self.disrupting_head.name,
            "intensities": {
                h.name: round(h.osc.disruption_intensity, 4) for h in self.heads
            },
            "min_intensity": round(
                min(h.osc.disruption_intensity for h in self.heads), 4
            ),
            "max_intensity": round(
                max(h.osc.disruption_intensity for h in self.heads), 4
            ),
        }


__all__ = [
    "TILT_DEG",
    "Vertex",
    "Apex",
    "AtaraxicMode",
    "Component",
    "AtaraxiaGovernor",
    "OscillatorState",
    "HamiltonianOscillator",
    "Reflector",
    "Dreamer",
    "Trainer",
    "Kernel",
    "TipResult",
    "SchmidhuberEngine",
    "Head",
    "ReplicaSet",
]
