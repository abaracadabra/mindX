"""Typed CONCLAVE message envelopes.

Each message kind is a frozen dataclass with `to_envelope()` and
`from_envelope()` for wire serialization. The `Envelope` itself is
the signed wrapper.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .crypto import (
    KeyPair,
    canonical_bytes,
    motion_id_for,
    session_id_for,
    sha256,
    sign,
    verify,
)
from .roles import Member, MotionClass, QuorumPolicy, Role


PROTOCOL_VERSION = 1


class MessageKind(str, Enum):
    CONVENE_MANIFEST = "ConveneManifest"
    ACCLAIM = "Acclaim"
    SESSION_OPEN = "SessionOpen"
    SPEAK = "Speak"
    MOTION = "Motion"
    VOTE = "Vote"
    RESOLUTION = "Resolution"
    ADJOURN = "Adjourn"
    PROTOCOL_ERROR = "ProtocolError"


# ------------------------------------------------------------------ #
# Envelope                                                           #
# ------------------------------------------------------------------ #


@dataclass
class Envelope:
    """The signed outer wrapper of every CONCLAVE wire message."""

    v: int
    kind: str
    session_id: str
    from_: str            # 'from' is reserved in Python; serialize as "from"
    seq: int
    ts: int
    body: dict[str, Any]
    sig: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "v": self.v,
            "kind": self.kind,
            "session_id": self.session_id,
            "from": self.from_,
            "seq": self.seq,
            "ts": self.ts,
            "body": self.body,
            "sig": self.sig,
        }

    def signing_payload(self) -> dict[str, Any]:
        """The dict that gets signed: everything except `sig`."""
        d = self.to_dict()
        d.pop("sig", None)
        return d

    def signed_with(self, kp: KeyPair) -> "Envelope":
        self.sig = sign(kp, self.signing_payload())
        return self

    def verify_signature(self) -> bool:
        return verify(self.from_, self.signing_payload(), self.sig)

    def to_bytes(self) -> bytes:
        """Canonical wire bytes for /send."""
        return canonical_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Envelope":
        return cls(
            v=int(d["v"]),
            kind=str(d["kind"]),
            session_id=str(d["session_id"]),
            from_=str(d["from"]),
            seq=int(d["seq"]),
            ts=int(d["ts"]),
            body=dict(d["body"]),
            sig=str(d.get("sig", "")),
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "Envelope":
        import cbor2  # local import keeps top-level fast
        return cls.from_dict(cbor2.loads(data))


# ------------------------------------------------------------------ #
# Bodies                                                             #
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class ConveneManifest:
    """Body of the kick-off envelope. The convener publishes this."""

    conclave_id: str          # on-chain registration id
    title: str
    agenda_hash: str
    members: list[Member]
    quorum: QuorumPolicy
    expiry: int               # unix seconds — acclaim deadline
    session_ttl: int          # seconds after CONVENED
    adjourn_grace: int = 300

    def to_body(self) -> dict[str, Any]:
        return {
            "conclave_id": self.conclave_id,
            "title": self.title,
            "agenda_hash": self.agenda_hash,
            "members": [m.to_manifest_dict() for m in self.members],
            "quorum": self.quorum.to_dict(),
            "expiry": self.expiry,
            "session_ttl": self.session_ttl,
            "adjourn_grace": self.adjourn_grace,
        }

    def session_id(self) -> str:
        return session_id_for(self.to_body())

    def envelope(self, convener: KeyPair, seq: int = 0) -> Envelope:
        body = self.to_body()
        env = Envelope(
            v=PROTOCOL_VERSION,
            kind=MessageKind.CONVENE_MANIFEST.value,
            session_id=session_id_for(body),
            from_=convener.peer_id,
            seq=seq,
            ts=int(time.time()),
            body=body,
        )
        return env.signed_with(convener)

    @classmethod
    def from_envelope(cls, env: Envelope) -> "ConveneManifest":
        b = env.body
        members = [
            Member(pubkey=m["pubkey"], role=Role(m["role"]))
            for m in b["members"]
        ]
        return cls(
            conclave_id=b["conclave_id"],
            title=b["title"],
            agenda_hash=b["agenda_hash"],
            members=members,
            quorum=QuorumPolicy.from_dict(b["quorum"]),
            expiry=int(b["expiry"]),
            session_ttl=int(b["session_ttl"]),
            adjourn_grace=int(b.get("adjourn_grace", 300)),
        )


@dataclass(frozen=True)
class Acclaim:
    manifest_hash: str

    def envelope(self, kp: KeyPair, session_id: str, seq: int) -> Envelope:
        env = Envelope(
            v=PROTOCOL_VERSION,
            kind=MessageKind.ACCLAIM.value,
            session_id=session_id,
            from_=kp.peer_id,
            seq=seq,
            ts=int(time.time()),
            body={"manifest_hash": self.manifest_hash},
        )
        return env.signed_with(kp)


@dataclass(frozen=True)
class SessionOpen:
    manifest_hash: str
    acclaimers: list[str]
    started_at: int

    def envelope(self, convener: KeyPair, session_id: str, seq: int) -> Envelope:
        env = Envelope(
            v=PROTOCOL_VERSION,
            kind=MessageKind.SESSION_OPEN.value,
            session_id=session_id,
            from_=convener.peer_id,
            seq=seq,
            ts=int(time.time()),
            body={
                "manifest_hash": self.manifest_hash,
                "acclaimers": self.acclaimers,
                "started_at": self.started_at,
            },
        )
        return env.signed_with(convener)


@dataclass(frozen=True)
class Speak:
    role: Role
    content: str
    content_type: str = "text/markdown"
    parent: str | None = None
    tools_used: list[dict[str, Any]] = field(default_factory=list)

    def envelope(self, kp: KeyPair, session_id: str, seq: int) -> Envelope:
        env = Envelope(
            v=PROTOCOL_VERSION,
            kind=MessageKind.SPEAK.value,
            session_id=session_id,
            from_=kp.peer_id,
            seq=seq,
            ts=int(time.time()),
            body={
                "role": self.role.value,
                "content_type": self.content_type,
                "content": self.content,
                "parent": self.parent,
                "tools_used": self.tools_used,
            },
        )
        return env.signed_with(kp)


@dataclass(frozen=True)
class Motion:
    text: str
    deadline: int
    class_: MotionClass = MotionClass.STANDARD
    proposer_role: Role = Role.CEO
    ballot: list[str] = field(default_factory=lambda: ["yea", "nay", "abstain"])

    def envelope(self, kp: KeyPair, session_id: str, seq: int) -> Envelope:
        body_no_id = {
            "class": self.class_.value,
            "proposer_role": self.proposer_role.value,
            "text": self.text,
            "ballot": self.ballot,
            "deadline": self.deadline,
        }
        body = {"motion_id": motion_id_for(body_no_id), **body_no_id}
        env = Envelope(
            v=PROTOCOL_VERSION,
            kind=MessageKind.MOTION.value,
            session_id=session_id,
            from_=kp.peer_id,
            seq=seq,
            ts=int(time.time()),
            body=body,
        )
        return env.signed_with(kp)


@dataclass(frozen=True)
class Vote:
    motion_id: str
    choice: str

    def envelope(self, kp: KeyPair, session_id: str, seq: int) -> Envelope:
        env = Envelope(
            v=PROTOCOL_VERSION,
            kind=MessageKind.VOTE.value,
            session_id=session_id,
            from_=kp.peer_id,
            seq=seq,
            ts=int(time.time()),
            body={"motion_id": self.motion_id, "choice": self.choice},
        )
        return env.signed_with(kp)


@dataclass(frozen=True)
class Resolution:
    motion_id: str
    tally: dict[str, int]
    outcome: str          # "passed" | "failed"
    voters: list[str]
    summary: str
    anchor: str | None = None

    def envelope(self, kp: KeyPair, session_id: str, seq: int) -> Envelope:
        env = Envelope(
            v=PROTOCOL_VERSION,
            kind=MessageKind.RESOLUTION.value,
            session_id=session_id,
            from_=kp.peer_id,
            seq=seq,
            ts=int(time.time()),
            body={
                "motion_id": self.motion_id,
                "tally": self.tally,
                "outcome": self.outcome,
                "voters": self.voters,
                "summary": self.summary,
                "anchor": self.anchor,
            },
        )
        return env.signed_with(kp)

    def anchor_payload(self) -> dict[str, Any]:
        """The body without `anchor` — what gets hashed for on-chain anchoring."""
        return {
            "motion_id": self.motion_id,
            "tally": self.tally,
            "outcome": self.outcome,
            "voters": self.voters,
            "summary": self.summary,
        }

    def anchor_hash(self) -> bytes:
        return sha256(canonical_bytes(self.anchor_payload()))


@dataclass(frozen=True)
class Adjourn:
    final_hash: str
    resolutions: list[str]
    redacted_summary: str

    def envelope(self, kp: KeyPair, session_id: str, seq: int) -> Envelope:
        env = Envelope(
            v=PROTOCOL_VERSION,
            kind=MessageKind.ADJOURN.value,
            session_id=session_id,
            from_=kp.peer_id,
            seq=seq,
            ts=int(time.time()),
            body={
                "final_hash": self.final_hash,
                "resolutions": self.resolutions,
                "redacted_summary": self.redacted_summary,
            },
        )
        return env.signed_with(kp)
