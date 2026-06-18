"""x402 v2 multi-rail conformance tests: protocol codec, CAIP-2 router,
Algorand/Parsec paymentGroup, and the Arweave ANS-104 signer.

These are offline/unit tests — no chain, no facilitator, no network.
"""
from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

import pytest

from mindx_backend_service import x402_protocol as xp


# ── CAIP-2 + router ──────────────────────────────────────────────────────────
def test_caip2_normalization_round_trip():
    assert xp.to_caip2("base") == "eip155:8453"
    assert xp.to_caip2("eip155:8453") == "eip155:8453"
    assert xp.to_caip2("8453") == "eip155:8453"
    assert xp.to_caip2("algorand-mainnet").startswith("algorand:wGHE2")
    assert xp.to_caip2("tempo") == "eip155:4217"
    assert xp.to_caip2("arweave") == "arweave:permaweb"
    # unknown passes through unchanged (forward-compatible)
    assert xp.to_caip2("eip155:999999") == "eip155:999999"


def test_rail_for_dispatch():
    assert xp.rail_for("base") == "evm"
    assert xp.rail_for("eip155:8453") == "evm"
    assert xp.rail_for("algorand-mainnet") == "avm"
    assert xp.rail_for("algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=") == "avm"
    assert xp.rail_for("arweave:permaweb") == "arweave"
    with pytest.raises(ValueError):
        xp.rail_for("solana:xyz")


# ── envelope codec (v2 challenge + v1/v2 payment + settlement) ───────────────
def test_encode_requirements_is_v2_with_v1_alias_and_caip2():
    reqs = [{"scheme": "exact", "network": "base", "asset": "0xA", "payTo": "0xB", "maxAmountRequired": "2000"}]
    body, header = xp.encode_requirements("/x", reqs)
    assert body["x402Version"] == 2
    assert body["accepts"] == body["paymentRequirements"]  # both keys, same list
    assert body["accepts"][0]["network"] == "eip155:8453"  # normalized
    # PAYMENT-REQUIRED header decodes back to the same accepts
    decoded = json.loads(base64.b64decode(header))
    assert decoded["x402Version"] == 2 and decoded["accepts"][0]["network"] == "eip155:8453"


def test_decode_payment_prefers_v2_then_v1():
    env = {"scheme": "exact", "network": "base", "payload": {"authorization": {"nonce": "0x01"}}}
    enc = base64.b64encode(json.dumps(env).encode()).decode()
    # v2 header
    got, ver = xp.decode_payment({"PAYMENT-SIGNATURE": enc})
    assert ver == 2 and got["scheme"] == "exact"
    # v1 header
    got, ver = xp.decode_payment({"X-PAYMENT": enc})
    assert ver == 1 and got["network"] == "base"
    # v2 wins when both present
    _, ver = xp.decode_payment({"PAYMENT-SIGNATURE": enc, "X-PAYMENT": enc})
    assert ver == 2
    # absent / undecodable
    assert xp.decode_payment({}) == (None, 1)
    assert xp.decode_payment({"X-PAYMENT": "@@@not-b64@@@"})[0] is None


def test_replay_key_evm_and_avm():
    evm = xp.replay_key("base", {"authorization": {"nonce": "0xabc"}})
    assert evm == "eip155:8453:0xabc"
    avm = xp.replay_key("algorand-mainnet", {"txid": "ALGOTX123"})
    assert avm.endswith(":ALGOTX123") and avm.startswith("algorand:")
    # AVM with only a paymentGroup → deterministic hash key
    g = xp.replay_key("algorand-mainnet", {"paymentGroup": ["aaa", "bbb"]})
    assert g and g == xp.replay_key("algorand-mainnet", {"paymentGroup": ["aaa", "bbb"]})


def test_settlement_headers_emit_both_versions():
    hdrs = xp.settlement_headers({"tx_hash": "0xdead", "rail": "evm"})
    assert "PAYMENT-RESPONSE" in hdrs and "X-PAYMENT-RESPONSE" in hdrs
    assert json.loads(base64.b64decode(hdrs["PAYMENT-RESPONSE"]))["tx_hash"] == "0xdead"


# ── Algorand / Parsec payment group ──────────────────────────────────────────
def test_avm_parsec_payment_group_fee_abstracted():
    pytest.importorskip("algosdk")
    from algosdk import account, mnemonic, encoding
    from tools.x402_avm_client import X402AvmClient

    sk, _ = account.generate_account()
    mn = mnemonic.from_private_key(sk)
    _, fee_payer = account.generate_account()
    _, payee = account.generate_account()
    client = X402AvmClient(buyer_mnemonic=mn, facilitator_url="http://disabled.invalid")
    challenge = {
        "scheme": "exact", "network": "algorand-testnet", "amount": "100000",
        "payTo": payee, "extra": {"assetId": 10458941, "feePayer": fee_payer},
    }
    env = json.loads(base64.b64decode(client._sign_payment(challenge)))
    assert env["x402Version"] == 2
    assert env["network"].startswith("algorand:")
    pl = env["payload"]
    assert pl["paymentIndex"] == 1 and len(pl["paymentGroup"]) == 2
    t0 = encoding.msgpack_decode(pl["paymentGroup"][0])      # unsigned facilitator pay
    t1 = encoding.msgpack_decode(pl["paymentGroup"][1])      # signed client axfer
    inner1 = t1.transaction if hasattr(t1, "transaction") else t1
    assert bytes(t0.note) == b"x402-fee-payer"
    assert bytes(inner1.note) == b"x402-payment-v2"
    assert t0.group and t0.group == inner1.group             # atomic group id set + matches
    assert getattr(t1, "signature", None)                    # client axfer is signed


def test_avm_single_txn_fallback_without_fee_payer():
    pytest.importorskip("algosdk")
    from algosdk import account, mnemonic
    from tools.x402_avm_client import X402AvmClient

    sk, _ = account.generate_account()
    _, payee = account.generate_account()
    client = X402AvmClient(buyer_mnemonic=mnemonic.from_private_key(sk), facilitator_url="http://disabled.invalid")
    env = json.loads(base64.b64decode(client._sign_payment(
        {"scheme": "exact", "network": "algorand-testnet", "amount": "100000", "payTo": payee, "extra": {"assetId": 10458941}}
    )))
    assert env["payload"]["paymentIndex"] == 0 and len(env["payload"]["paymentGroup"]) == 1


# ── Arweave ANS-104 signer ───────────────────────────────────────────────────
def test_arweave_dataitem_sign_offline():
    pytest.importorskip("cryptography")
    import tools.arweave_turbo as at

    wallet = at.load_or_create_wallet(Path(tempfile.mktemp(suffix=".json")))
    assert len(wallet.address) == 43  # base64url sha256(n)
    item, item_id = at.build_and_sign_dataitem(
        wallet, b"hello permaweb", [("Content-Type", "text/plain"), ("App-Name", "THOT")]
    )
    assert item[:2] == (1).to_bytes(2, "little")  # sig_type = 1 (arweave RSA)
    assert len(item) > 1024 and len(item_id) == 32
