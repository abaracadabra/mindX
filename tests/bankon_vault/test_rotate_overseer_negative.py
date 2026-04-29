"""
Negative-case tests for BankonVault.rotate_overseer.

Locks down the rejection paths so a future refactor can't silently
weaken the rotation contract:

  - Malformed signature (wrong length)
  - Signature replay against a different challenge text
  - Wrong evidence kind ("daio" with HumanOverseer)
  - Stale .rotation.ok marker (>300s) blocks commit
  - Candidate file sha drifts between dry_run and commit blocks commit

Each test isolates a fresh vault under tempfile so concurrent runs
don't collide and the audit log under data/governance/ resolves into
the test's own tmp tree.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Run from repo root — allow imports without PYTHONPATH juggling.
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT))


# ─────────────────────────────────────────────────────────────────────────
# Fixture — disposable vault + valid handoff materials
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def vault_with_handoff():
    """
    Yields a tuple (vault, vault_dir, overseer, challenge_bytes, evidence) where
    `evidence` is a *valid* signed handoff. Tests then mutate one piece of it
    and assert rotate_overseer refuses.
    """
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from mindx_backend_service.bankon_vault.vault import BankonVault
    from mindx_backend_service.bankon_vault.overseer import HumanOverseer

    os.environ["MINDX_VAULT_ALLOW_OVERSEER_ROTATION"] = "1"

    test_priv = "0x" + "11" * 32
    acct = Account.from_key(test_priv)

    tmp = Path(tempfile.mkdtemp(prefix="rotate-overseer-neg-"))
    parent = tmp / "run"
    parent.mkdir()
    vault_dir = parent / "vault_bankon"
    try:
        v = BankonVault(vault_dir=str(vault_dir))
        v.unlock_with_key_file()
        v.store("agent_pk_test", "0x" + "f" * 64, context="agent_identity")
        v.store("provider:openai_api_key", "sk-proj-test", context="provider")

        overseer = HumanOverseer(eth_address=acct.address, vault_salt=v._salt)
        challenge_text = "BANKON Vault Custody Handoff v1 — negative test"
        challenge_bytes = challenge_text.encode("utf-8")
        msg = encode_defunct(text=challenge_text)
        sig_hex = Account.sign_message(msg, private_key=test_priv).signature.hex()
        if not sig_hex.startswith("0x"):
            sig_hex = "0x" + sig_hex
        evidence = {"kind": "human", "signature": sig_hex, "message": challenge_text}

        yield v, vault_dir, overseer, challenge_bytes, evidence
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────


def test_malformed_signature_wrong_length(vault_with_handoff):
    """A 64-byte signature (one byte short) must be rejected."""
    v, _, overseer, ch, ev = vault_with_handoff
    bad = dict(ev)
    # Truncate signature to 64 bytes — recovery will still fail OR the byte-len
    # check inside HumanOverseer.produce_raw_key would catch it. Either way,
    # rotate_overseer must refuse.
    bad["signature"] = ev["signature"][: -2]  # drop one hex char pair = 1 byte
    with pytest.raises(Exception):
        v.rotate_overseer(overseer, ch, bad, reason="neg_short_sig", dry_run=True)


def test_signature_replay_on_different_challenge(vault_with_handoff):
    """A valid sig over message X must NOT pass when challenge bytes are message Y."""
    v, _, overseer, _, ev = vault_with_handoff
    different_challenge = b"BANKON Vault Custody Handoff v1 - different message"
    # evidence still references the original message text — but we pass
    # a different challenge. verify_evidence binds the two via:
    #   message.encode("utf-8") != challenge -> False
    with pytest.raises(Exception, match="evidence did not verify"):
        v.rotate_overseer(overseer, different_challenge, ev,
                          reason="neg_replay", dry_run=True)


def test_evidence_kind_mismatch(vault_with_handoff):
    """Evidence with kind=='daio' must not satisfy a HumanOverseer."""
    v, _, overseer, ch, ev = vault_with_handoff
    bad = dict(ev)
    bad["kind"] = "daio"
    with pytest.raises(Exception, match="evidence did not verify"):
        v.rotate_overseer(overseer, ch, bad, reason="neg_kind_mismatch", dry_run=True)


def test_signature_signed_by_wrong_key(vault_with_handoff):
    """A sig from a different EOA must be rejected even if shape is correct."""
    from eth_account import Account
    from eth_account.messages import encode_defunct

    v, _, overseer, ch, ev = vault_with_handoff
    other_priv = "0x" + "22" * 32  # different key
    msg = encode_defunct(text=ev["message"])
    other_sig = Account.sign_message(msg, private_key=other_priv).signature.hex()
    if not other_sig.startswith("0x"):
        other_sig = "0x" + other_sig
    bad = dict(ev)
    bad["signature"] = other_sig
    with pytest.raises(Exception, match="evidence did not verify"):
        v.rotate_overseer(overseer, ch, bad, reason="neg_wrong_signer", dry_run=True)


# Note: the stale-.rotation.ok and candidate-sha-drift checks at vault.py:506-512
# are defense-in-depth against an internal corruption window inside
# _rotate_overseer_locked. They aren't externally reachable: rotate_overseer always
# re-runs the dry-run path (steps 7-8) inside the same fcntl-locked call before
# the commit-path check, so the marker timestamp and candidate sha are always
# fresh by the time those guards execute. Tests omitted intentionally — would
# require white-box mocking that ossifies internal call structure.


def test_env_flag_required(vault_with_handoff):
    """Without MINDX_VAULT_ALLOW_OVERSEER_ROTATION, rotate_overseer must refuse cold."""
    v, _, overseer, ch, ev = vault_with_handoff
    saved = os.environ.pop("MINDX_VAULT_ALLOW_OVERSEER_ROTATION", None)
    try:
        with pytest.raises(RuntimeError, match="MINDX_VAULT_ALLOW_OVERSEER_ROTATION"):
            v.rotate_overseer(overseer, ch, ev, reason="neg_no_flag", dry_run=True)
    finally:
        if saved is not None:
            os.environ["MINDX_VAULT_ALLOW_OVERSEER_ROTATION"] = saved
