"""DojoArbiter — the Dojo as a blackbox consensus-arbitration service.

The Dojo is mindX's arbitration / escalation tier: Boardroom (t1) → **Dojo (t2)** →
War Council (t3). Where the Boardroom, the War Council, DAIO/JudgeDread, and mindXtrain
each produce *disagreement* in their own vocabulary, the Dojo is the one primitive that
ingests those heterogeneous verdicts, normalizes them into **ballots**, resolves the
disagreement under a *chosen, variable* **consensus model**, and records a single
verifiable **decision**.

It is "a service to" each source — callable three ways, all reaching the same engine:
  * in-process   — ``await DojoArbiter.get_instance().decide(...)`` or module ``decide(...)``
  * over HTTP    — ``POST /dojo/decide``  (mindx_backend_service)
  * from the CLI — ``python scripts/dojo.py decide ...``

Every decision is recorded to three sinks (all best-effort, never raising into the caller):
  1. ``data/governance/dojo_decisions.jsonl`` — the Dojo's own append-only ledger;
  2. the canonical hash-linked VotingBooth (``agents.provenance_chain.council_booth``);
  3. a ``dojo.decision`` catalogue event (``agents.catalogue.events.emit_catalogue_event``).

Reuses, rather than re-implements, the existing consensus math:
  * supermajority  — Boardroom weighted tally (``daio/governance/boardroom.py``);
  * prime_ladder   — War Council prime-weighted tally (``mindx/war_council.py``);
  * two_of_three   — DAIO/JudgeDread 2/3-of-3-groups rule (``agents/judgedread_agent.py``).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── paths ──────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DECISIONS_FILE = _PROJECT_ROOT / "data" / "governance" / "dojo_decisions.jsonl"

# Boardroom soldier weights (mirrors daio/governance/boardroom.py:SOLDIER_WEIGHTS) —
# used when a raw soldier_id has no explicit weight.
SOLDIER_WEIGHTS = {
    "coo_operations": 1.0, "cfo_finance": 1.0, "cto_technology": 1.0,
    "ciso_security": 1.2, "clo_legal": 0.8, "cpo_product": 1.0, "cro_risk": 1.2,
}
SUPERMAJORITY_THRESHOLD = 0.666  # == boardroom.py
VALID_ORIGINS = ("boardroom", "warcouncil", "mindxtrain", "daio", "godel", "manual")
VALID_VOTES = ("approve", "reject", "abstain")


def _enabled() -> bool:
    """Advisory call sites (ascend/boardroom escalation) honor this; the core
    engine + CLI + HTTP always run regardless."""
    return os.getenv("MINDX_DOJO_ARBITER_ENABLED", "1").lower() not in ("0", "false", "no", "off")


# ── ballot ─────────────────────────────────────────────────────────────────
@dataclass
class Ballot:
    """One normalized vote into the Dojo, from any source."""
    origin: str                     # boardroom | warcouncil | mindxtrain | daio | godel | manual
    voter: str                      # soldier_id / seat role / "imprint" / group name
    vote: str                       # approve | reject | abstain
    weight: float = 1.0
    confidence: float = 1.0         # 0.0–1.0
    reasoning: str = ""
    seat: Optional[int] = None      # war-council seat 0..12 (prime_ladder only)
    group: Optional[str] = None     # DAIO group (two_of_three only)

    def to_dict(self) -> Dict[str, Any]:
        d = {"origin": self.origin, "voter": self.voter, "vote": self.vote,
             "weight": round(float(self.weight), 4), "confidence": round(float(self.confidence), 4),
             "reasoning": (self.reasoning or "")[:300]}
        if self.seat is not None:
            d["seat"] = self.seat
        if self.group is not None:
            d["group"] = self.group
        return d


def _coerce_ballot(b: Any) -> Ballot:
    """Accept a Ballot, a dict, or a boardroom SoldierVote-like object."""
    if isinstance(b, Ballot):
        return b
    if isinstance(b, dict):
        origin = str(b.get("origin", "manual")).lower()
        vote = str(b.get("vote", "abstain")).lower()
        if vote not in VALID_VOTES:
            vote = "abstain"
        weight = b.get("weight")
        voter = str(b.get("voter") or b.get("soldier_id") or b.get("role") or "anon")
        if weight is None:
            weight = SOLDIER_WEIGHTS.get(voter, 1.0)
        return Ballot(
            origin=origin if origin in VALID_ORIGINS else "manual",
            voter=voter, vote=vote,
            weight=float(weight), confidence=float(b.get("confidence", 1.0) or 1.0),
            reasoning=str(b.get("reasoning") or b.get("reason") or ""),
            seat=b.get("seat"), group=b.get("group"),
        )
    # duck-typed object (e.g. boardroom SoldierVote)
    return Ballot(
        origin=getattr(b, "origin", "manual"),
        voter=str(getattr(b, "soldier_id", getattr(b, "voter", "anon"))),
        vote=str(getattr(b, "vote", "abstain")).lower(),
        weight=float(getattr(b, "weight", 1.0)),
        confidence=float(getattr(b, "confidence", 1.0)),
        reasoning=str(getattr(b, "reasoning", "")),
    )


# ── consensus models (the "variable consensus including DAIO") ──────────────
# Each: (ballots, stakes) -> (decision, score, threshold, detail)
#   decision ∈ {approved, rejected, exploration, no_quorum}

def _cm_supermajority(ballots: List[Ballot], *, stakes: int = 0) -> tuple:
    """Boardroom-style weighted consensus: weight*confidence, threshold 0.666.
    Mixed approve+reject below threshold → exploration (dissent as a feature)."""
    threshold = SUPERMAJORITY_THRESHOLD
    approve = sum(b.weight * b.confidence for b in ballots if b.vote == "approve")
    reject = sum(b.weight * b.confidence for b in ballots if b.vote == "reject")
    denom = approve + reject
    if denom <= 0:
        return "no_quorum", 0.0, threshold, {"approve_w": approve, "reject_w": reject}
    score = approve / denom
    if score >= threshold:
        decision = "approved"
    elif approve > 0 and reject > 0:
        decision = "exploration"
    else:
        decision = "rejected"
    return decision, score, threshold, {"approve_w": round(approve, 4), "reject_w": round(reject, 4)}


def _cm_weighted_confidence(ballots: List[Ballot], *, stakes: int = 0) -> tuple:
    """Simple weight*confidence majority at 0.5 — decisive, no exploration band."""
    approve = sum(b.weight * b.confidence for b in ballots if b.vote == "approve")
    reject = sum(b.weight * b.confidence for b in ballots if b.vote == "reject")
    denom = approve + reject
    if denom <= 0:
        return "no_quorum", 0.0, 0.5, {"approve_w": approve, "reject_w": reject}
    score = approve / denom
    return ("approved" if score >= 0.5 else "rejected"), score, 0.5, {
        "approve_w": round(approve, 4), "reject_w": round(reject, 4)}


def _cm_prime_ladder(ballots: List[Ballot], *, stakes: int = 0) -> tuple:
    """War-council prime-weighted, accelerating-majority tally — never deadlocks."""
    try:
        from mindx.war_council import tally as wc_tally
    except Exception as e:  # pragma: no cover
        logger.warning(f"prime_ladder unavailable: {e}")
        return _cm_supermajority(ballots, stakes=stakes)
    votes = []
    for i, b in enumerate(ballots):
        seat = b.seat if b.seat is not None else (i % 13)
        votes.append({"seat": int(seat), "vote": b.vote})
    res = wc_tally(votes, stakes=stakes)
    decision = {"approved": "approved", "rejected": "rejected", "no_quorum": "no_quorum"}.get(
        res.get("verdict"), "no_quorum")
    score = float(res.get("weighted", {}).get("ratio", 0.0) or 0.0)
    threshold = float(res.get("threshold", {}).get("ratio", 0.0) or 0.0)
    return decision, score, threshold, {"seats": res.get("seats"), "weighted": res.get("weighted")}


def _cm_two_of_three(ballots: List[Ballot], *, stakes: int = 0) -> tuple:
    """DAIO/JudgeDread rule: group ballots, a group approves on its own majority,
    overall approved iff >= 2/3 of groups approve."""
    threshold = 2.0 / 3.0
    groups: Dict[str, List[Ballot]] = {}
    for b in ballots:
        key = b.group or b.voter or b.origin
        groups.setdefault(key, []).append(b)
    if not groups:
        return "no_quorum", 0.0, threshold, {}
    approved_groups = 0
    detail = {}
    for g, gb in groups.items():
        a = sum(1 for x in gb if x.vote == "approve")
        r = sum(1 for x in gb if x.vote == "reject")
        ok = a > r
        approved_groups += 1 if ok else 0
        detail[g] = {"approve": a, "reject": r, "approved": ok}
    score = approved_groups / len(groups)
    return ("approved" if score >= threshold else "rejected"), score, threshold, {"groups": detail}


def _cm_quorum(ballots: List[Ballot], *, stakes: int = 0) -> tuple:
    """Raw-headcount simple majority of non-abstaining ballots (unweighted)."""
    a = sum(1 for b in ballots if b.vote == "approve")
    r = sum(1 for b in ballots if b.vote == "reject")
    denom = a + r
    if denom <= 0:
        return "no_quorum", 0.0, 0.5, {"approve_n": a, "reject_n": r}
    score = a / denom
    return ("approved" if a > r else "rejected"), score, 0.5, {"approve_n": a, "reject_n": r}


CONSENSUS_MODELS: Dict[str, Callable[..., tuple]] = {
    "supermajority": _cm_supermajority,
    "weighted_confidence": _cm_weighted_confidence,
    "prime_ladder": _cm_prime_ladder,
    "two_of_three": _cm_two_of_three,
    "quorum": _cm_quorum,
}


def _dissent_branches(ballots: List[Ballot], decision: str) -> List[Dict[str, Any]]:
    """Dissent → explorable branches (mirrors boardroom._create_exploration_branches)."""
    out = []
    for b in ballots:
        if b.vote == "reject":
            out.append({"origin": b.origin, "voter": b.voter, "confidence": round(b.confidence, 3),
                        "reasoning": (b.reasoning or "")[:200],
                        "suggestion": f"Explore alternative per {b.voter}: {(b.reasoning or '')[:140]}"})
    return out


# ── normalizer adapters — the Dojo as a service to each source ──────────────
def from_boardroom(session: Any) -> List[Ballot]:
    """A BoardroomSession (object or dict) → ballots."""
    votes = getattr(session, "votes", None)
    if votes is None and isinstance(session, dict):
        votes = session.get("votes", [])
    out = []
    for v in (votes or []):
        b = _coerce_ballot(v)
        b.origin = "boardroom"
        out.append(b)
    return out


def from_warcouncil(seat_votes: List[Dict[str, Any]]) -> List[Ballot]:
    """War-council seat votes [{seat,vote,role?}] → ballots (seat preserved)."""
    out = []
    for sv in (seat_votes or []):
        out.append(Ballot(origin="warcouncil",
                           voter=str(sv.get("role") or f"seat{sv.get('seat')}"),
                           vote=str(sv.get("vote", "abstain")).lower(),
                           weight=float(sv.get("weight", 1.0)),
                           confidence=float(sv.get("confidence", 1.0)),
                           reasoning=str(sv.get("reasoning", "")),
                           seat=sv.get("seat")))
    return out


def from_mindxtrain(verdict: Dict[str, Any], *, min_delta: float = 0.0) -> List[Ballot]:
    """A mindXtrain imprint verdict (or self_eval training_eval) → one ballot.

    Approves iff the generation imprinted with a positive recall delta. Confidence
    scales with the delta magnitude so a marginal imprint carries less weight."""
    v = verdict or {}
    accepted = bool(v.get("accepted", v.get("imprinted", False)))
    delta = float(v.get("delta", v.get("last_delta", 0.0)) or 0.0)
    vote = "approve" if (accepted and delta >= min_delta) else "reject"
    conf = max(0.05, min(1.0, abs(delta) * 10.0)) if delta else (0.6 if accepted else 0.4)
    reason = v.get("reason") or (
        f"imprint accepted (delta={delta:+.4f})" if accepted else f"imprint rejected (delta={delta:+.4f})")
    return [Ballot(origin="mindxtrain", voter="imprint", vote=vote, weight=1.0,
                   confidence=conf, reasoning=str(reason))]


def from_daio(group_votes: Dict[str, Dict[str, bool]]) -> List[Ballot]:
    """JudgeDread-style {group: {voter: bool}} → per-voter ballots tagged by group."""
    out = []
    for group, voters in (group_votes or {}).items():
        for voter, approve in (voters or {}).items():
            out.append(Ballot(origin="daio", voter=f"{group}:{voter}",
                               vote="approve" if approve else "reject", group=group))
    return out


# ── the engine ──────────────────────────────────────────────────────────────
class DojoArbiter:
    """Singleton consensus-arbitration engine."""

    _instance: Optional["DojoArbiter"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.decisions_file = _DECISIONS_FILE
        self.decisions_file.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    async def get_instance(cls) -> "DojoArbiter":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    async def decide(self, *, subject: str, ballots: List[Any], stakes: int = 0,
                     consensus_model: str = "supermajority", council: str = "dojo",
                     record: bool = True) -> Dict[str, Any]:
        """Resolve disagreement among ``ballots`` under ``consensus_model`` into one
        recorded decision. Always runs (independent of MINDX_DOJO_ARBITER_ENABLED;
        that flag gates the advisory call sites, not the engine)."""
        model_fn = CONSENSUS_MODELS.get(consensus_model)
        if model_fn is None:
            raise ValueError(f"unknown consensus_model '{consensus_model}' "
                             f"(choices: {', '.join(CONSENSUS_MODELS)})")
        norm = [_coerce_ballot(b) for b in (ballots or [])]
        decision, score, threshold, detail = model_fn(norm, stakes=stakes)
        ts = int(time.time())
        rec: Dict[str, Any] = {
            "subject": subject, "council": council, "model": consensus_model, "stakes": stakes,
            "decision": decision, "score": round(float(score), 4), "threshold": round(float(threshold), 4),
            "ballots": [b.to_dict() for b in norm],
            "dissent": _dissent_branches(norm, decision),
            "rationale": (f"{consensus_model}: {decision} (score {score:.3f} vs threshold "
                          f"{threshold:.3f}, {len(norm)} ballots from "
                          f"{sorted(set(b.origin for b in norm))})"),
            "detail": detail, "ts": ts,
            "ts_utc": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
        }
        if record:
            rec["record_hash"] = await self._record(rec)
        return rec

    async def _record(self, rec: Dict[str, Any]) -> Optional[str]:
        """Hash-linked VotingBooth → Dojo ledger → catalogue. Guarded; the booth hash
        is computed first so the ledger line carries it too."""
        record_hash: Optional[str] = None
        # 1. canonical hash-linked VotingBooth
        try:
            from agents.provenance_chain import council_booth
            booth_rec = council_booth().record(
                council=rec["council"], subject=rec["subject"], decision=rec["decision"], ts=rec["ts"],
                tally={"model": rec["model"], "score": rec["score"], "threshold": rec["threshold"],
                       "stakes": rec["stakes"], "detail": rec["detail"]},
                votes=rec["ballots"], extra={"rationale": rec["rationale"], "dissent": rec["dissent"]})
            record_hash = (booth_rec or {}).get("record_hash")
        except Exception as e:  # pragma: no cover
            logger.warning(f"dojo VotingBooth record failed: {e}")
        if not record_hash:  # local fallback so callers always get a content id
            record_hash = "0x" + hashlib.sha256(
                json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()
        rec["record_hash"] = record_hash
        # 2. own append-only ledger (now carries record_hash)
        try:
            with self.decisions_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as e:  # pragma: no cover
            logger.warning(f"dojo ledger append failed: {e}")
        # 3. catalogue event (logs are memories)
        try:
            from agents.catalogue.events import emit_catalogue_event
            await emit_catalogue_event(
                kind="dojo.decision", actor="dojo",
                payload={k: rec[k] for k in ("subject", "council", "model", "decision",
                                             "score", "threshold", "stakes", "ts_utc")},
                source_log="governance/dojo_decisions.jsonl", source_ref=rec["subject"][:80])
        except Exception as e:  # pragma: no cover
            logger.debug(f"dojo catalogue emit skipped: {e}")
        return record_hash

    def recent(self, limit: int = 20, *, council: Optional[str] = None) -> List[Dict[str, Any]]:
        """Tail the Dojo decision ledger (newest first)."""
        if not self.decisions_file.exists():
            return []
        out: List[Dict[str, Any]] = []
        try:
            lines = self.decisions_file.read_text(encoding="utf-8").splitlines()
            for ln in reversed(lines):
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    r = json.loads(ln)
                except Exception:
                    continue
                if council and r.get("council") != council:
                    continue
                out.append(r)
                if len(out) >= limit:
                    break
        except Exception as e:  # pragma: no cover
            logger.warning(f"dojo recent read failed: {e}")
        return out


# ── module-level convenience (the in-process service API) ───────────────────
async def decide(*, subject: str, ballots: List[Any], stakes: int = 0,
                 consensus_model: str = "supermajority", council: str = "dojo",
                 record: bool = True) -> Dict[str, Any]:
    arb = await DojoArbiter.get_instance()
    return await arb.decide(subject=subject, ballots=ballots, stakes=stakes,
                            consensus_model=consensus_model, council=council, record=record)


async def recent(limit: int = 20, *, council: Optional[str] = None) -> List[Dict[str, Any]]:
    arb = await DojoArbiter.get_instance()
    return arb.recent(limit, council=council)
