# SPDX-License-Identifier: Apache-2.0
"""Tests for the mindX Python overlord resolver (mirror of @openagents/overlord).

No network: holdings/acquisition are injected; chronos `now_unix` is passed in.
Signatures are real (eth_account) so identity proof is exercised end-to-end.
"""
import asyncio

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct

from mindx_backend_service.overlord.config import HoldingConfig, LevelBand, OverlordConfig
from mindx_backend_service.overlord.resolver import (
    can,
    member_level,
    resolve_privilege,
)

# anvil dev keys (well-known; test only)
ACCT_A = Account.from_key("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d")
ACCT_B = Account.from_key("0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a")

NOW = 1_900_000_000
CHRONOS = {"consensus": "correlated", "promised_by": "chronos.agent"}


def _cfg(overlord, overseers=()):
    return OverlordConfig(
        overlord=overlord,
        overseers=tuple(overseers),
        domain="test.local",
        holding=HoldingConfig(
            rpc="http://invalid", token="0x1111111111111111111111111111111111111111",
            standard="erc20", chain_id=1, threshold=100,
            level_bands=(
                LevelBand(1, 100, 0),
                LevelBand(2, 100, 86_400 * 30),
                LevelBand(3, 1_000, 86_400 * 30),
            ),
        ),
    )


def _sign(acct, msg):
    return acct.sign_message(encode_defunct(text=msg)).signature.hex()


def _hold(balance=0, acquired=None):
    async def _read(_h, _o):
        return balance
    async def _acq(_h, _o):
        return acquired
    return _read, _acq


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


MESSAGE = "OVERLORD-LOGIN\ndomain: test.local\nwallet: x\nscope: s\nnonce: 0x1\nissued_at: 1\nexp: 2"


def test_overlord_role():
    cfg = _cfg(ACCT_A.address)
    sig = _sign(ACCT_A, MESSAGE)
    p = _run(resolve_privilege(ACCT_A.address, MESSAGE, sig, cfg, now_unix=NOW, chronos=CHRONOS))
    assert p["role"] == "overlord" and p["privileged"]


def test_overseer_role():
    cfg = _cfg(ACCT_B.address, overseers=[ACCT_A.address])
    sig = _sign(ACCT_A, MESSAGE)
    p = _run(resolve_privilege(ACCT_A.address, MESSAGE, sig, cfg, now_unix=NOW, chronos=CHRONOS))
    assert p["role"] == "overseer"


def test_public_no_holding():
    cfg = _cfg(ACCT_B.address)
    sig = _sign(ACCT_A, MESSAGE)
    rh, ra = _hold(balance=0)
    p = _run(resolve_privilege(ACCT_A.address, MESSAGE, sig, cfg, now_unix=NOW, chronos=CHRONOS,
                               read_holding_fn=rh, acq_fn=ra))
    assert p["role"] == "public" and not p["privileged"]


def test_member_level_by_tenure():
    cfg = _cfg(ACCT_B.address)
    sig = _sign(ACCT_A, MESSAGE)
    rh, ra = _hold(balance=500, acquired=NOW - 86_400 * 40)  # 40d, ≥ band-2, < band-3 amount
    p = _run(resolve_privilege(ACCT_A.address, MESSAGE, sig, cfg, now_unix=NOW, chronos=CHRONOS,
                               read_holding_fn=rh, acq_fn=ra))
    assert p["role"] == "member" and p["level"] == 2
    assert p["holding"]["tenure_sec"] == 86_400 * 40


def test_member_recent_stays_l1():
    cfg = _cfg(ACCT_B.address)
    sig = _sign(ACCT_A, MESSAGE)
    rh, ra = _hold(balance=500, acquired=NOW - 86_400)  # 1d
    p = _run(resolve_privilege(ACCT_A.address, MESSAGE, sig, cfg, now_unix=NOW, chronos=CHRONOS,
                               read_holding_fn=rh, acq_fn=ra))
    assert p["role"] == "member" and p["level"] == 1


def test_bad_signature_public():
    cfg = _cfg(ACCT_A.address)
    sig = _sign(ACCT_B, MESSAGE)  # B signs, A claimed
    p = _run(resolve_privilege(ACCT_A.address, MESSAGE, sig, cfg, now_unix=NOW, chronos=CHRONOS))
    assert p["role"] == "public" and "identity" in p["reason"]


def test_capabilities_separation():
    for a in ("clear", "destroy.cabinet", "rotate.keys", "release.key"):
        assert can("overlord", a) is True
        assert can("overseer", a) is False
        assert can("member", a) is False
    assert can("overseer", "distribute.privilege") is True
    assert can("member", "distribute.privilege") is False
    assert can("public", "read.member") is False
    assert can("public", "read.public") is True


def test_member_level_fn():
    bands = [LevelBand(1, 100, 0), LevelBand(2, 100, 100), LevelBand(3, 1000, 100)]
    assert member_level(bands, 100, 0) == 1
    assert member_level(bands, 100, 200) == 2
    assert member_level(bands, 2000, 200) == 3
    assert member_level(bands, 2000, 50) == 1
    assert member_level(bands, 5000, None) == 1
