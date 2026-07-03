# SPDX-License-Identifier: Apache-2.0
"""x402 facilitator — signs X402Receipts the BankonX402Attestor consumes (rail 0x02).

The payment layer (packages/web/payments.js) converts any denomination to USDC and
calls POST /x402/settle; this endpoint signs an EIP-712 X402Receipt with the
facilitator key so the registrar/hosting can mint without an inline ERC-20 transfer.

PRODUCTION: the facilitator MUST verify the USDC actually settled (on-chain transfer
to the treasury, a Circle CCTP/Gateway receipt, or an Algorand x402 proof) BEFORE
signing. This reference signs on request only when BANKON_X402_TRUST_REQUEST=1 (dev);
otherwise it 501s until a settlement verifier is wired. The facilitator EOA must be
registered via BankonX402Attestor.setFacilitator(addr, true).

Env:
  BANKON_X402_FACILITATOR_PK   facilitator EOA key (vault/env)
  BANKON_X402_ATTESTOR         attestor address (else read from deployments)
  BANKON_SETTLEMENT_CHAIN_ID   default 1
  BANKON_X402_TRUST_REQUEST    "1" to sign without a settlement verifier (DEV ONLY)
"""
from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path

from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/x402", tags=["bankon-payments"])


class SettleReq(BaseModel):
    payer: str
    usd6: str
    resource: str
    chainId: int = 1


def _attestor(chain_id: int) -> str:
    a = os.environ.get("BANKON_X402_ATTESTOR")
    if a:
        return a
    name = "local" if chain_id == 31337 else str(chain_id)
    p = Path(__file__).resolve().parent.parent / "deployments" / f"{name}.json"
    try:
        addr = json.loads(p.read_text()).get("bankon", {}).get("x402Attestor")
        if addr and int(addr, 16) != 0:
            return addr
    except Exception:
        pass
    raise HTTPException(503, "x402 attestor address not configured (BANKON_X402_ATTESTOR / deployments)")


@router.post("/settle")
async def settle(req: SettleReq):
    pk = os.environ.get("BANKON_X402_FACILITATOR_PK")
    if not pk:
        raise HTTPException(503, "facilitator key not configured (BANKON_X402_FACILITATOR_PK)")
    if os.environ.get("BANKON_X402_TRUST_REQUEST") != "1":
        raise HTTPException(
            501,
            "settlement verification not wired — set BANKON_X402_TRUST_REQUEST=1 for dev, or "
            "implement a verifier (on-chain USDC transfer / CCTP / Algorand x402) before signing.",
        )

    attestor = _attestor(req.chainId)
    acct = Account.from_key(pk)
    nonce = int.from_bytes(secrets.token_bytes(8), "big")
    expires_at = int(time.time()) + 600
    receipt_hash = "0x" + keccak(
        text=f"{req.payer.lower()}|{req.usd6}|{req.resource}|{nonce}|{expires_at}"
    ).hex()

    typed = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "X402Receipt": [
                {"name": "receiptHash", "type": "bytes32"},
                {"name": "claimant", "type": "address"},
                {"name": "usd6", "type": "uint256"},
                {"name": "nonce", "type": "uint64"},
                {"name": "expiresAt", "type": "uint64"},
            ],
        },
        "domain": {
            "name": "BankonX402Attestor",
            "version": "1",
            "chainId": req.chainId,
            "verifyingContract": attestor,
        },
        "primaryType": "X402Receipt",
        "message": {
            "receiptHash": receipt_hash,
            "claimant": req.payer,
            "usd6": int(req.usd6),
            "nonce": nonce,
            "expiresAt": expires_at,
        },
    }
    signable = encode_typed_data(full_message=typed)
    signed = Account.sign_message(signable, private_key=pk)
    sig = signed.signature.hex()
    if not sig.startswith("0x"):
        sig = "0x" + sig

    return {
        "receiptHash": receipt_hash,
        "claimant": req.payer,
        "usd6": req.usd6,
        "nonce": nonce,
        "expiresAt": expires_at,
        "signature": sig,
        "facilitator": acct.address,
        "attestor": attestor,
    }
