# SPDX-License-Identifier: MIT
"""Tests for the OVERSEER/OVERLORD handoff: owner recognition + gated walletgen."""
import os
import sys
import tempfile

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from walletcreator.bankon_vault import BankonVault  # noqa: E402
from walletcreator.wallet_creator import WalletCreator  # noqa: E402
from walletcreator.participant_issuer import (  # noqa: E402
    OverlordHandoff, build_handoff_challenge, HandoffError,
)


def _handoff():
    tmp = tempfile.mkdtemp()
    vault = BankonVault(os.path.join(tmp, "vault.json"), "test-pass", salt=b"\x00" * 16)
    return OverlordHandoff(WalletCreator(vault))


def _sign(acct, room_id, chain_id, nonce):
    msg = build_handoff_challenge(room_id=room_id, chain_id=chain_id, nonce=nonce)
    return acct.sign_message(encode_defunct(text=msg)).signature.hex()


def test_owner_recognized_by_signature_no_custody():
    owner = Account.create()
    msg = "login: prove you are the overlord"
    sig = owner.sign_message(encode_defunct(text=msg)).signature.hex()
    h = _handoff()
    assert h.recognize_owner(message=msg, signature=sig, expected_owner=owner.address)
    # a different address is not recognized
    assert not h.recognize_owner(message=msg, signature=sig, expected_owner=Account.create().address)


def test_issue_participant_under_owner_signature():
    owner = Account.create()
    h = _handoff()
    sig = _sign(owner, room_id=42, chain_id=137, nonce="n1")
    out = h.issue_participant_wallet(
        owner_address=owner.address, room_id=42, chain_id=137, nonce="n1", signature=sig, label="alice"
    )
    assert out["participant_address"].startswith("0x")
    assert out["authorized_by"].lower() == owner.address.lower()
    assert out["vault_id"].startswith("wallet:evm:")
    assert out["custody"] == "vault"


def test_wrong_signer_rejected():
    owner = Account.create()
    attacker = Account.create()
    h = _handoff()
    sig = _sign(attacker, room_id=1, chain_id=137, nonce="x")
    with pytest.raises(HandoffError):
        h.issue_participant_wallet(
            owner_address=owner.address, room_id=1, chain_id=137, nonce="x", signature=sig
        )


def test_replay_rejected():
    owner = Account.create()
    h = _handoff()
    sig = _sign(owner, room_id=5, chain_id=137, nonce="once")
    h.issue_participant_wallet(owner_address=owner.address, room_id=5, chain_id=137, nonce="once", signature=sig)
    with pytest.raises(HandoffError):
        h.issue_participant_wallet(owner_address=owner.address, room_id=5, chain_id=137, nonce="once", signature=sig)


def test_cross_room_replay_rejected():
    # a signature for room 5 cannot authorize room 6 (message binding)
    owner = Account.create()
    h = _handoff()
    sig = _sign(owner, room_id=5, chain_id=137, nonce="bind")
    with pytest.raises(HandoffError):
        h.issue_participant_wallet(owner_address=owner.address, room_id=6, chain_id=137, nonce="bind", signature=sig)
