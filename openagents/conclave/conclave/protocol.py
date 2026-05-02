"""CONCLAVE protocol state machine.

The `Conclave` class is the per-member runtime: it owns the local
keypair, the AXL client, the active sessions, and the dispatch loop
that ingests envelopes from `/recv`.

Convener-specific orchestration (publishing manifests, gathering
acclaims, broadcasting SessionOpen, anchoring resolutions on chain) is
exposed as explicit methods rather than baked into the dispatcher, so
that the same class can act as either Convener or Counsellor.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable

from .axl_client import AXLClient
from .crypto import KeyPair, sha256, canonical_bytes, hex32
from .messages import (
    Acclaim,
    Adjourn,
    ConveneManifest,
    Envelope,
    MessageKind,
    Motion,
    Resolution,
    SessionOpen,
    Speak,
    Vote,
)
from .roles import Member, MotionClass, QuorumPolicy, Role
from .session import (
    MotionRecord,
    Session,
    SessionState,
    build_session_from_manifest,
)


log = logging.getLogger("conclave")


SpeakHandler = Callable[[Session, Envelope], None]
MotionHandler = Callable[[Session, Envelope], str]    # returns vote choice


@dataclass
class Conclave:
    """Per-member CONCLAVE runtime."""

    keypair: KeyPair
    role: Role
    axl: AXLClient
    sessions: dict[str, Session] = field(default_factory=dict)

    # Optional callbacks an embedding agent (mindX) plugs in.
    on_speak: SpeakHandler | None = None
    on_motion: MotionHandler | None = None

    # ---------------------------------------------------------------- #
    # Identity                                                         #
    # ---------------------------------------------------------------- #

    @property
    def peer_id(self) -> str:
        return self.keypair.peer_id

    # ---------------------------------------------------------------- #
    # Convener actions                                                 #
    # ---------------------------------------------------------------- #

    def convene(
        self,
        conclave_id: str,
        title: str,
        agenda_hash: str,
        members: list[Member],
        quorum: QuorumPolicy | None = None,
        ttl_seconds: int = 7200,
        acclaim_window_seconds: int = 600,
    ) -> Session:
        """Publish a ConveneManifest to all named members.

        Returns the newly-constructed local Session in PROPOSED state.
        """
        q = quorum or QuorumPolicy.cabinet_default()
        manifest = ConveneManifest(
            conclave_id=conclave_id,
            title=title,
            agenda_hash=agenda_hash,
            members=members,
            quorum=q,
            expiry=int(time.time()) + acclaim_window_seconds,
            session_ttl=ttl_seconds,
        )
        env = manifest.envelope(self.keypair, seq=0)
        sess = build_session_from_manifest(env)
        self.sessions[sess.session_id] = sess
        sess.append_transcript(env)
        # Convener auto-acclaims their own session
        sess.add_acclaim(self.peer_id)

        for m in members:
            if m.pubkey.lower() == self.peer_id.lower():
                continue
            try:
                self.axl.send_envelope(env, m.pubkey)
            except Exception as e:  # noqa: BLE001
                log.warning("manifest send to %s failed: %s", m.pubkey, e)

        log.info("conclave proposed: %s (session %s)", title, sess.session_id)
        return sess

    def open_session_if_quorum(self, session_id: str) -> bool:
        """If acclaim quorum is reached, broadcast SessionOpen and flip ACTIVE."""
        sess = self._require_session(session_id)
        if sess.state is not SessionState.PROPOSED:
            return False
        if not sess.acclaim_quorum_reached():
            return False
        manifest_hash = self._session_manifest_hash(sess)
        so = SessionOpen(
            manifest_hash=manifest_hash,
            acclaimers=sorted(sess.acclaimers),
            started_at=int(time.time()),
        )
        seq = self._next_seq(sess)
        env = so.envelope(self.keypair, sess.session_id, seq)
        sess.open()
        sess.append_transcript(env)
        self._broadcast(sess, env)
        log.info("session %s opened with %d acclaimers",
                 sess.session_id, len(sess.acclaimers))
        return True

    def propose_motion(
        self,
        session_id: str,
        text: str,
        class_: MotionClass = MotionClass.STANDARD,
        deadline_seconds: int = 600,
    ) -> str:
        """Convener (or any member) proposes a Motion. Returns motion_id."""
        sess = self._require_session(session_id)
        if sess.state is not SessionState.ACTIVE:
            raise RuntimeError(f"session not ACTIVE (state={sess.state})")
        m = Motion(
            text=text,
            deadline=int(time.time()) + deadline_seconds,
            class_=class_,
            proposer_role=self.role,
        )
        env = m.envelope(self.keypair, sess.session_id, self._next_seq(sess))
        motion_id = env.body["motion_id"]
        sess.add_motion(MotionRecord(
            motion_id=motion_id,
            text=text,
            deadline=int(env.body["deadline"]),
            class_=class_,
            proposer_pubkey=self.peer_id,
        ))
        sess.append_transcript(env)
        self._broadcast(sess, env)
        return motion_id

    def cast_vote(self, session_id: str, motion_id: str, choice: str) -> None:
        sess = self._require_session(session_id)
        v = Vote(motion_id=motion_id, choice=choice)
        env = v.envelope(self.keypair, sess.session_id, self._next_seq(sess))
        sess.record_vote(motion_id, self.peer_id, choice)
        sess.append_transcript(env)
        self._broadcast(sess, env)

    def resolve_motion(self, session_id: str, motion_id: str,
                       summary: str) -> Resolution | None:
        """Convener-only. Returns Resolution if outcome is decided, else None."""
        sess = self._require_session(session_id)
        outcome, tally = sess.evaluate_motion(motion_id)
        if outcome == "pending":
            return None
        mr = sess.motions[motion_id]
        mr.resolved = True
        res = Resolution(
            motion_id=motion_id,
            tally=tally,
            outcome=outcome,
            voters=mr.yea_voters() if outcome == "passed" else [],
            summary=summary,
        )
        env = res.envelope(self.keypair, sess.session_id, self._next_seq(sess))
        sess.append_transcript(env)
        self._broadcast(sess, env)
        sess.state = SessionState.RESOLVED
        return res

    def adjourn(self, session_id: str, redacted_summary: str) -> None:
        sess = self._require_session(session_id)
        merkle = self._transcript_merkle_root(sess)
        resolved_ids = sorted(
            mr.motion_id for mr in sess.motions.values() if mr.resolved
        )
        adj = Adjourn(
            final_hash=hex32(merkle),
            resolutions=resolved_ids,
            redacted_summary=redacted_summary,
        )
        env = adj.envelope(self.keypair, sess.session_id, self._next_seq(sess))
        sess.append_transcript(env)
        self._broadcast(sess, env)
        sess.state = SessionState.ADJOURNED

    # ---------------------------------------------------------------- #
    # Counsellor actions                                               #
    # ---------------------------------------------------------------- #

    def acclaim(self, manifest_envelope: Envelope) -> None:
        """Counsellor: acknowledge a received ConveneManifest."""
        cm = ConveneManifest.from_envelope(manifest_envelope)
        sess = self.sessions.get(manifest_envelope.session_id)
        if sess is None:
            sess = build_session_from_manifest(manifest_envelope)
            self.sessions[sess.session_id] = sess
            sess.append_transcript(manifest_envelope)

        if not sess.is_member(self.peer_id):
            log.warning("manifest %s does not include us; ignoring",
                        manifest_envelope.session_id)
            return

        manifest_hash = self._session_manifest_hash(sess)
        a = Acclaim(manifest_hash=manifest_hash)
        env = a.envelope(self.keypair, sess.session_id, self._next_seq(sess))
        sess.add_acclaim(self.peer_id)
        sess.append_transcript(env)
        # Send to convener only.
        try:
            self.axl.send_envelope(env, sess.convener)
        except Exception as e:  # noqa: BLE001
            log.warning("acclaim send failed: %s", e)

    def speak(
        self,
        session_id: str,
        content: str,
        parent: str | None = None,
        tools_used: list[dict] | None = None,
    ) -> None:
        sess = self._require_session(session_id)
        s = Speak(
            role=self.role,
            content=content,
            parent=parent,
            tools_used=tools_used or [],
        )
        env = s.envelope(self.keypair, sess.session_id, self._next_seq(sess))
        sess.append_transcript(env)
        self._broadcast(sess, env)

    # ---------------------------------------------------------------- #
    # Inbound dispatch                                                 #
    # ---------------------------------------------------------------- #

    def poll_once(self) -> bool:
        """Pull one inbound message from AXL and dispatch. Returns True if any."""
        msg = self.axl.recv()
        if msg is None:
            return False
        try:
            env = Envelope.from_bytes(msg.data)
        except Exception as e:  # noqa: BLE001
            log.warning("undecodable inbound bytes from %s: %s", msg.from_peer, e)
            return True

        if env.from_.lower() != msg.from_peer.lower():
            log.warning(
                "envelope from=%s does not match transport peer=%s — dropping",
                env.from_, msg.from_peer,
            )
            return True

        if not env.verify_signature():
            log.warning("bad signature on envelope from %s — dropping", env.from_)
            return True

        self.dispatch(env)
        return True

    def run(self, idle_sleep: float = 0.05) -> None:
        """Blocking dispatch loop. Suitable for `examples/*_node.py`."""
        log.info("conclave dispatcher running as %s (peer %s)",
                 self.role.value, self.peer_id)
        while True:
            handled = self.poll_once()
            if not handled:
                time.sleep(idle_sleep)

    def dispatch(self, env: Envelope) -> None:
        """Route an envelope to the appropriate handler."""
        kind = env.kind
        if kind == MessageKind.CONVENE_MANIFEST.value:
            self.acclaim(env)
            return

        sess = self.sessions.get(env.session_id)
        if sess is None:
            log.warning("envelope for unknown session %s — dropping",
                        env.session_id)
            return

        if not sess.is_member(env.from_):
            log.warning("envelope from non-member %s — dropping", env.from_)
            return

        if not sess.check_seq(env):
            log.warning("seq replay/regression from %s — dropping", env.from_)
            return

        sess.append_transcript(env)

        if kind == MessageKind.ACCLAIM.value:
            sess.add_acclaim(env.from_)
            # Convener: open session if quorum reached.
            if sess.convener.lower() == self.peer_id.lower():
                self.open_session_if_quorum(sess.session_id)

        elif kind == MessageKind.SESSION_OPEN.value:
            if sess.state is SessionState.PROPOSED:
                sess.state = SessionState.ACTIVE
                sess.started_at = int(env.body.get("started_at", time.time()))

        elif kind == MessageKind.SPEAK.value:
            if self.on_speak is not None:
                try:
                    self.on_speak(sess, env)
                except Exception as e:  # noqa: BLE001
                    log.exception("on_speak handler raised: %s", e)

        elif kind == MessageKind.MOTION.value:
            mr = MotionRecord(
                motion_id=env.body["motion_id"],
                text=env.body["text"],
                deadline=int(env.body["deadline"]),
                class_=MotionClass(env.body["class"]),
                proposer_pubkey=env.from_,
            )
            sess.add_motion(mr)
            if self.on_motion is not None:
                try:
                    choice = self.on_motion(sess, env)
                    if choice in env.body["ballot"]:
                        self.cast_vote(sess.session_id, mr.motion_id, choice)
                except Exception as e:  # noqa: BLE001
                    log.exception("on_motion handler raised: %s", e)

        elif kind == MessageKind.VOTE.value:
            sess.record_vote(
                motion_id=env.body["motion_id"],
                voter=env.from_,
                choice=env.body["choice"],
            )
            # Convener: try to resolve.
            if sess.convener.lower() == self.peer_id.lower():
                outcome, _ = sess.evaluate_motion(env.body["motion_id"])
                if outcome != "pending":
                    self.resolve_motion(
                        sess.session_id,
                        env.body["motion_id"],
                        summary=f"motion {env.body['motion_id']} {outcome}",
                    )

        elif kind == MessageKind.RESOLUTION.value:
            sess.state = SessionState.RESOLVED
            mid = env.body["motion_id"]
            if mid in sess.motions:
                sess.motions[mid].resolved = True

        elif kind == MessageKind.ADJOURN.value:
            sess.state = SessionState.ADJOURNED

        else:
            log.warning("unknown kind %s — dropping", kind)

    # ---------------------------------------------------------------- #
    # Internals                                                        #
    # ---------------------------------------------------------------- #

    def _require_session(self, session_id: str) -> Session:
        s = self.sessions.get(session_id)
        if s is None:
            raise KeyError(f"unknown session {session_id}")
        return s

    def _next_seq(self, sess: Session) -> int:
        cur = sess.last_seq_by.get(self.peer_id.lower(), -1)
        nxt = cur + 1
        sess.last_seq_by[self.peer_id.lower()] = nxt
        return nxt

    def _broadcast(self, sess: Session, env: Envelope) -> None:
        """Send the envelope to every member except ourselves."""
        for m in sess.members:
            if m.pubkey.lower() == self.peer_id.lower():
                continue
            try:
                self.axl.send_envelope(env, m.pubkey)
            except Exception as e:  # noqa: BLE001
                log.warning("broadcast to %s failed: %s", m.pubkey, e)

    def _session_manifest_hash(self, sess: Session) -> str:
        """The hash of the manifest body — stored as the session_id itself."""
        return sess.session_id

    def _transcript_merkle_root(self, sess: Session) -> bytes:
        """Plain Merkle root over canonical envelope bytes.

        Not pretending this is RFC-9162; it's a simple, reproducible root.
        Pairs are duplicated when count is odd, which is the Bitcoin
        convention and the simplest verifier.
        """
        leaves = [sha256(e.to_bytes()) for e in sess.transcript]
        if not leaves:
            return b"\x00" * 32
        layer = leaves
        while len(layer) > 1:
            if len(layer) % 2 == 1:
                layer.append(layer[-1])
            layer = [sha256(layer[i] + layer[i + 1])
                     for i in range(0, len(layer), 2)]
        return layer[0]
