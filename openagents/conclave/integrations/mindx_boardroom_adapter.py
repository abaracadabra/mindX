"""mindX boardroom → CONCLAVE adapter (illustrative composition).

mindX has two deliberation surfaces:

  1. Fast LLM boardroom — `daio/governance/boardroom.py`. Cloud-routable
     CEO + 7 soldiers; weighted-consensus across LLM providers. Optimized
     for routine throughput; sub-second per-soldier vote.

  2. CONCLAVE — this protocol. End-to-end-encrypted mesh deliberation;
     cryptographically-bounded membership; on-chain anchoring. Optimized
     for high-stakes / trade-secret / cross-org sessions where the
     non-repudiation and privacy properties matter more than latency.

This adapter shows how mindX routes a *high-stakes* directive through
CONCLAVE instead of the fast boardroom path. **The adapter is optional**:
- mindX runs fine without CONCLAVE (the fast boardroom is the default)
- CONCLAVE runs fine without mindX (any agent framework can compose it)

The adapter is the **composition demonstration**: it shows that the two
modules are wired by interface only.

Public surface:
- `is_high_stakes(directive: str) -> bool`
   Caller-policy heuristic; default flags directives mentioning trade
   secrets, M&A, incident-response, or marked `[STAKES:HIGH]`.
- `convene_via_conclave(directive: str, agenda_md: str | None = None,
                        cabinet: list[Member] | None = None) -> str`
   Spawns a Conclave session with the local agent as Convener (CEO).
   Returns the session_id. Async-safe.
- `route(directive: str, mindx_boardroom_runner=None) -> str`
   The single integration entry-point. mindX `daio/governance/boardroom.py`
   imports this and calls it before invoking the fast path. If
   `is_high_stakes()` returns True, we route to CONCLAVE; else we hand
   back to `mindx_boardroom_runner(directive)` (mindX's existing path).

Other frameworks compose the same way: their boardroom dispatcher imports
`route()` and supplies its own `mindx_boardroom_runner` analogue.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass
from typing import Awaitable, Callable, Iterable, Optional

# Local-only imports — adapter explicitly does NOT import mindX.
from conclave.protocol import Conclave
from conclave.roles import Member, QuorumPolicy, Role
from conclave.session import Session


log = logging.getLogger("conclave.integrations.mindx")


# Heuristic patterns that flag a directive as "high-stakes" — caller can
# replace this with a richer policy (BONAFIDE Censura threshold, explicit
# board flag, NDA tag, etc.). Keep as a module-level constant so callers
# can override before import-time freezing.
HIGH_STAKES_PATTERNS = (
    re.compile(r"\bM&?A\b", re.IGNORECASE),
    re.compile(r"\btrade[\s\-]*secret", re.IGNORECASE),
    re.compile(r"\bincident\s*response\b", re.IGNORECASE),
    re.compile(r"\bcompliance\s*disclosure\b", re.IGNORECASE),
    re.compile(r"\bvulnerab[il]\w+\s*disclosure\b", re.IGNORECASE),
    re.compile(r"\[\s*STAKES\s*:\s*HIGH\s*\]", re.IGNORECASE),
)


def is_high_stakes(directive: str) -> bool:
    """Return True if the directive should route through CONCLAVE.

    Replaceable by setting `MindxBoardroomAdapter.is_high_stakes_fn`
    on the adapter instance, OR by appending to `HIGH_STAKES_PATTERNS`
    at import time, OR by tagging the directive `[STAKES:HIGH]`.
    """
    if not directive:
        return False
    return any(p.search(directive) for p in HIGH_STAKES_PATTERNS)


def agenda_hash(agenda_md: str) -> str:
    """Deterministic agenda hash for the Conclave manifest."""
    return "0x" + hashlib.sha256(agenda_md.encode("utf-8")).hexdigest()


@dataclass
class MindxBoardroomAdapter:
    """One-shot composition adapter; instantiate with the local Conclave runtime.

    Example wiring (mindX side):

        from conclave.protocol import Conclave
        from conclave.integrations.mindx_boardroom_adapter import (
            MindxBoardroomAdapter, is_high_stakes,
        )

        local_conclave = Conclave(keypair=ceo_keypair, role=Role.CEO, axl=axl_client)
        adapter = MindxBoardroomAdapter(conclave=local_conclave, cabinet=cabinet_members)

        async def boardroom_dispatch(directive: str):
            return await adapter.route(directive, mindx_boardroom_runner=mindx.fast_boardroom)
    """

    conclave: Conclave
    cabinet: list[Member]
    is_high_stakes_fn: Callable[[str], bool] = is_high_stakes
    default_quorum: Optional[QuorumPolicy] = None

    def convene_via_conclave(
        self,
        directive: str,
        agenda_md: Optional[str] = None,
        conclave_id: Optional[str] = None,
    ) -> Session:
        """Open a Conclave session with this directive as the agenda.

        Returns the local Session in PROPOSED state. Caller is responsible
        for waiting on acclaims (the Conclave runtime's dispatch loop fills
        them in via `/recv`) and then calling
        `local_conclave.open_session_if_quorum(session.session_id)` to flip
        to ACTIVE and broadcast the SessionOpen envelope.
        """
        if not self.cabinet:
            raise ValueError("cabinet member list is empty — adapter mis-wired")
        title = f"mindX directive · {directive[:80]}"
        agenda_md_full = agenda_md or _default_agenda(directive)
        conclave_id_full = conclave_id or _generate_conclave_id(directive)
        sess = self.conclave.convene(
            conclave_id=conclave_id_full,
            title=title,
            agenda_hash=agenda_hash(agenda_md_full),
            members=list(self.cabinet),
            quorum=self.default_quorum,
        )
        log.info(
            "mindX-boardroom-adapter routed directive %r through CONCLAVE (session %s)",
            directive[:60], sess.session_id,
        )
        return sess

    async def route(
        self,
        directive: str,
        mindx_boardroom_runner: Optional[Callable[[str], Awaitable[object]]] = None,
    ) -> object:
        """Single entry-point. Routes high-stakes → CONCLAVE; else fast path.

        The `mindx_boardroom_runner` callable is mindX's own
        `daio.governance.boardroom.convene_session(directive)` (or any
        equivalent in another framework). When the directive is not
        high-stakes, we delegate without ever touching CONCLAVE — the
        fast path returns whatever the runner returns. mindX is one
        consumer; this adapter never imports mindX itself.
        """
        if self.is_high_stakes_fn(directive):
            sess = self.convene_via_conclave(directive)
            return {
                "router":      "conclave",
                "session_id":  sess.session_id,
                "title":       sess.title,
                "members":     [m.pubkey for m in self.cabinet],
                "state":       sess.state.value if hasattr(sess.state, "value") else str(sess.state),
                "note":        "high-stakes routing — see /openagents/conclave for resolution anchoring",
            }
        # Fast path: hand off to the consumer's boardroom (mindX, OpenClaw, …)
        if mindx_boardroom_runner is None:
            log.warning(
                "no fast-path runner supplied — directive %r dropped",
                directive[:60],
            )
            return {"router": "none", "note": "no fast-path runner configured"}
        return {"router": "fast", "result": await mindx_boardroom_runner(directive)}


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #

def _generate_conclave_id(seed: str) -> str:
    """A short, deterministic-ish id derived from the directive + env."""
    src = seed + "|" + os.environ.get("CONCLAVE_NAMESPACE", "mindx")
    return "0x" + hashlib.sha256(src.encode("utf-8")).hexdigest()[:32]


def _default_agenda(directive: str) -> str:
    """Build a minimal agenda Markdown blob."""
    return (
        "# Agenda\n\n"
        "1. Discuss directive\n"
        f"   > {directive}\n\n"
        "2. Identify trade-secret considerations\n"
        "3. Vote on motion to proceed\n"
        "4. Resolve and anchor\n"
    )


def cabinet_from_local_keys(keys: Iterable[tuple[str, Role, Optional[str]]]) -> list[Member]:
    """Convenience builder from `(pubkey_hex, role, evm_address)` triples.

    Useful for tests and the example 8-node bring-up. Other frameworks can
    build cabinets from their own identity managers (mindX uses
    `agents/core/id_manager_agent.py`, but that's a mindX detail).
    """
    return [
        Member(pubkey=pk, role=role, evm_address=evm)
        for (pk, role, evm) in keys
    ]
