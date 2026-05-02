"""In-memory session state.

Holds the convened manifest, observed acclaims, motions, and the
*latest* vote per (motion_id, voter). Supplies tally-and-decide
helpers used by the protocol state machine.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from .messages import Envelope, MessageKind
from .roles import Member, MotionClass, QuorumPolicy


class SessionState(str, Enum):
    PROPOSED = "proposed"
    CONVENED = "convened"
    ACTIVE = "active"
    RESOLVED = "resolved"
    ADJOURNED = "adjourned"
    ABORTED = "aborted"


@dataclass
class MotionRecord:
    motion_id: str
    text: str
    deadline: int
    class_: MotionClass
    proposer_pubkey: str
    # Latest vote per voter pubkey.
    votes: dict[str, str] = field(default_factory=dict)
    resolved: bool = False

    def tally(self) -> dict[str, int]:
        out: dict[str, int] = defaultdict(int)
        for choice in self.votes.values():
            out[choice] += 1
        return dict(out)

    def yea_voters(self) -> list[str]:
        return sorted(pk for pk, c in self.votes.items() if c == "yea")


@dataclass
class Session:
    """Mutable in-memory state of a single CONCLAVE session."""

    session_id: str
    title: str
    conclave_id: str
    convener: str               # pubkey
    members: list[Member]
    quorum: QuorumPolicy
    expiry: int
    session_ttl: int
    started_at: int = 0          # filled when SessionOpen issued
    state: SessionState = SessionState.PROPOSED

    acclaimers: set[str] = field(default_factory=set)
    motions: dict[str, MotionRecord] = field(default_factory=dict)
    transcript: list[Envelope] = field(default_factory=list)
    last_seq_by: dict[str, int] = field(default_factory=dict)

    # ---- membership ---- #

    def member_pubkeys(self) -> list[str]:
        return [m.pubkey.lower() for m in self.members]

    def is_member(self, pubkey: str) -> bool:
        return pubkey.lower() in {m.pubkey.lower() for m in self.members}

    def role_for(self, pubkey: str) -> str | None:
        for m in self.members:
            if m.pubkey.lower() == pubkey.lower():
                return m.role.value
        return None

    # ---- acclaim ---- #

    def add_acclaim(self, voter: str) -> None:
        if not self.is_member(voter):
            raise ValueError(f"non-member acclaim from {voter}")
        self.acclaimers.add(voter.lower())

    def acclaim_quorum_reached(self) -> bool:
        return len(self.acclaimers) >= self.quorum.acclaim

    def open(self, now: int | None = None) -> None:
        if not self.acclaim_quorum_reached():
            raise RuntimeError("acclaim quorum not yet reached")
        self.state = SessionState.ACTIVE
        self.started_at = int(now if now is not None else time.time())

    # ---- motions ---- #

    def add_motion(self, mr: MotionRecord) -> None:
        if mr.motion_id in self.motions:
            return  # idempotent
        self.motions[mr.motion_id] = mr

    def record_vote(self, motion_id: str, voter: str, choice: str) -> None:
        if motion_id not in self.motions:
            raise ValueError(f"unknown motion {motion_id}")
        if not self.is_member(voter):
            raise ValueError(f"non-member vote from {voter}")
        self.motions[motion_id].votes[voter.lower()] = choice

    def evaluate_motion(self, motion_id: str) -> tuple[str, dict[str, int]]:
        """Return (outcome, tally). Outcome is 'passed', 'failed', or 'pending'."""
        mr = self.motions[motion_id]
        threshold = self.quorum.for_class(mr.class_)
        tally = mr.tally()
        yea = tally.get("yea", 0)
        nay = tally.get("nay", 0)
        abstain = tally.get("abstain", 0)
        total_members = len(self.members)
        votes_cast = yea + nay + abstain

        # trade_secret motions count abstain as nay
        if mr.class_ is MotionClass.TRADE_SECRET:
            nay += abstain
            abstain = 0

        if yea >= threshold:
            return "passed", tally
        # failed only if it's mathematically impossible to reach threshold
        remaining = total_members - votes_cast
        if yea + remaining < threshold:
            return "failed", tally
        return "pending", tally

    # ---- replay protection ---- #

    def check_seq(self, env: Envelope) -> bool:
        """Strictly increasing seq per (session, sender)."""
        last = self.last_seq_by.get(env.from_.lower(), -1)
        if env.seq <= last:
            return False
        self.last_seq_by[env.from_.lower()] = env.seq
        return True

    def append_transcript(self, env: Envelope) -> None:
        self.transcript.append(env)


def build_session_from_manifest(manifest_envelope: Envelope) -> Session:
    """Construct a fresh Session from a verified ConveneManifest envelope."""
    if manifest_envelope.kind != MessageKind.CONVENE_MANIFEST.value:
        raise ValueError("not a ConveneManifest envelope")
    from .messages import ConveneManifest  # avoid cycle at import time

    cm = ConveneManifest.from_envelope(manifest_envelope)
    return Session(
        session_id=manifest_envelope.session_id,
        title=cm.title,
        conclave_id=cm.conclave_id,
        convener=manifest_envelope.from_,
        members=list(cm.members),
        quorum=cm.quorum,
        expiry=cm.expiry,
        session_ttl=cm.session_ttl,
    )


def session_members(s: Session) -> Iterable[Member]:
    return iter(s.members)
