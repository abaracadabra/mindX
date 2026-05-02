"""End-to-end protocol unit test — no AXL, just signed envelope roundtrips.

This catches the most common bugs (canonical encoding, signature
verification, quorum math, motion id determinism) without needing the
Go AXL binary in CI.
"""
from __future__ import annotations

import time

import pytest

from conclave import (
    Acclaim,
    Adjourn,
    ConveneManifest,
    Envelope,
    KeyPair,
    Motion,
    QuorumPolicy,
    Resolution,
    SessionOpen,
    Speak,
    Vote,
)
from conclave.crypto import canonical_bytes, sha256
from conclave.messages import MessageKind
from conclave.roles import Member, MotionClass, Role
from conclave.session import (
    MotionRecord,
    Session,
    build_session_from_manifest,
)


def _make_cabinet():
    """Return (kps, members) where each entry is one of the 8 roles."""
    roles = [Role.CEO, Role.COO, Role.CFO, Role.CTO,
             Role.CISO, Role.GC, Role.COS, Role.OPS]
    kps = {r: KeyPair.generate() for r in roles}
    members = [Member(pubkey=kps[r].peer_id, role=r) for r in roles]
    return kps, members


# ---------- crypto / canonical encoding ---------- #


def test_canonical_encoding_is_deterministic():
    a = {"b": 1, "a": 2, "z": [3, 1, 2]}
    b = {"a": 2, "z": [3, 1, 2], "b": 1}
    assert canonical_bytes(a) == canonical_bytes(b)


def test_keypair_peer_id_is_stable_across_load():
    seed = b"\xaa" * 32
    kp1 = KeyPair.from_seed(seed)
    kp2 = KeyPair.from_seed(seed)
    assert kp1.peer_id == kp2.peer_id
    assert len(kp1.peer_id) == 2 + 64  # "0x" + 64 hex


# ---------- envelope sign / verify ---------- #


def test_envelope_sign_and_verify():
    kp = KeyPair.generate()
    env = Envelope(
        v=1, kind="Speak", session_id="0x" + "11" * 32,
        from_=kp.peer_id, seq=0, ts=int(time.time()),
        body={"role": "CEO", "content": "hello", "content_type": "text/plain",
              "parent": None, "tools_used": []},
    ).signed_with(kp)
    assert env.verify_signature()

    # Tamper with body -> sig fails.
    env.body["content"] = "tampered"
    assert not env.verify_signature()


def test_envelope_roundtrip_via_canonical_bytes():
    kp = KeyPair.generate()
    env = Speak(role=Role.CFO, content="hi").envelope(
        kp, session_id="0x" + "22" * 32, seq=3,
    )
    raw = env.to_bytes()
    decoded = Envelope.from_bytes(raw)
    assert decoded.verify_signature()
    assert decoded.from_ == kp.peer_id
    assert decoded.body["role"] == "CFO"


# ---------- manifest / session bootstrap ---------- #


def test_manifest_envelope_sets_session_id_to_body_hash():
    kps, members = _make_cabinet()
    cm = ConveneManifest(
        conclave_id="0x" + "00" * 31 + "01",
        title="Q3 M&A",
        agenda_hash="0x" + "ab" * 32,
        members=members,
        quorum=QuorumPolicy.cabinet_default(),
        expiry=int(time.time()) + 600,
        session_ttl=7200,
    )
    env = cm.envelope(kps[Role.CEO])
    assert env.verify_signature()
    # session id == sha256(canonical(body))
    assert env.session_id == "0x" + sha256(canonical_bytes(cm.to_body())).hex()


def test_build_session_from_manifest():
    kps, members = _make_cabinet()
    cm = ConveneManifest(
        conclave_id="0x" + "00" * 31 + "01",
        title="t", agenda_hash="0x" + "ab" * 32,
        members=members, quorum=QuorumPolicy.cabinet_default(),
        expiry=int(time.time()) + 600, session_ttl=600,
    )
    env = cm.envelope(kps[Role.CEO])
    sess = build_session_from_manifest(env)
    assert sess.session_id == env.session_id
    assert sess.convener == kps[Role.CEO].peer_id
    assert len(sess.members) == 8
    assert sess.is_member(kps[Role.GC].peer_id)
    assert not sess.is_member("0x" + "ff" * 32)


# ---------- voting + tally ---------- #


def test_quorum_passes_at_threshold():
    kps, members = _make_cabinet()
    sess = _proposed_session(kps, members)

    motion_body = Motion(text="approve", deadline=int(time.time()) + 60).envelope(
        kps[Role.CEO], sess.session_id, 0,
    ).body
    motion_id = motion_body["motion_id"]
    sess.add_motion(MotionRecord(
        motion_id=motion_id, text="approve", deadline=motion_body["deadline"],
        class_=MotionClass.STANDARD, proposer_pubkey=kps[Role.CEO].peer_id,
    ))

    # 5 yea, 1 nay, 2 abstain -> standard threshold is 5 -> passes
    voters = [Role.CEO, Role.CFO, Role.CTO, Role.GC, Role.COO]
    for r in voters:
        sess.record_vote(motion_id, kps[r].peer_id, "yea")
    sess.record_vote(motion_id, kps[Role.CISO].peer_id, "nay")
    sess.record_vote(motion_id, kps[Role.COS].peer_id, "abstain")
    sess.record_vote(motion_id, kps[Role.OPS].peer_id, "abstain")

    outcome, tally = sess.evaluate_motion(motion_id)
    assert outcome == "passed"
    assert tally["yea"] == 5


def test_trade_secret_treats_abstain_as_nay():
    kps, members = _make_cabinet()
    sess = _proposed_session(kps, members)

    body = Motion(text="release",
                  deadline=int(time.time()) + 60,
                  class_=MotionClass.TRADE_SECRET).envelope(
        kps[Role.CEO], sess.session_id, 0,
    ).body
    mid = body["motion_id"]
    sess.add_motion(MotionRecord(
        motion_id=mid, text="release", deadline=body["deadline"],
        class_=MotionClass.TRADE_SECRET, proposer_pubkey=kps[Role.CEO].peer_id,
    ))

    # 5 yea, 1 nay, 2 abstain
    for r in [Role.CEO, Role.CFO, Role.CTO, Role.GC, Role.COO]:
        sess.record_vote(mid, kps[r].peer_id, "yea")
    sess.record_vote(mid, kps[Role.CISO].peer_id, "nay")
    sess.record_vote(mid, kps[Role.COS].peer_id, "abstain")
    sess.record_vote(mid, kps[Role.OPS].peer_id, "abstain")

    outcome, _ = sess.evaluate_motion(mid)
    # 5 yea < 6 trade_secret threshold -> failed (not pending; abstains
    # were promoted to nay so no votes remain to flip)
    assert outcome == "failed"


def test_seq_replay_rejected():
    kps, _ = _make_cabinet()
    cm = ConveneManifest(
        conclave_id="0x01", title="t",
        agenda_hash="0x" + "ab" * 32,
        members=[Member(pubkey=kps[Role.CEO].peer_id, role=Role.CEO)],
        quorum=QuorumPolicy(acclaim=1, standard=1, trade_secret=1, membership=1),
        expiry=int(time.time()) + 600, session_ttl=600,
    )
    env0 = cm.envelope(kps[Role.CEO])
    sess = build_session_from_manifest(env0)

    e1 = Speak(role=Role.CEO, content="a").envelope(
        kps[Role.CEO], sess.session_id, 1)
    e2 = Speak(role=Role.CEO, content="b").envelope(
        kps[Role.CEO], sess.session_id, 1)  # replayed seq
    assert sess.check_seq(e1)
    assert not sess.check_seq(e2)


# ---------- helpers ---------- #


def _proposed_session(kps, members) -> Session:
    cm = ConveneManifest(
        conclave_id="0x" + "00" * 31 + "01",
        title="t", agenda_hash="0x" + "ab" * 32,
        members=members, quorum=QuorumPolicy.cabinet_default(),
        expiry=int(time.time()) + 600, session_ttl=600,
    )
    env = cm.envelope(kps[Role.CEO])
    return build_session_from_manifest(env)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
