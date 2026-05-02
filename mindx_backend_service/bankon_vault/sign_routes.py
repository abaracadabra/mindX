# ╔══════════════════════════════════════════════════════════════════╗
# ║  BANKON Vault — Vault-as-Signing-Oracle                         ║
# ║                                                                  ║
# ║  POST /vault/sign/{agent_id}                                    ║
# ║                                                                  ║
# ║  Returns a valid EIP-191 signature on a payload, signed by the  ║
# ║  agent's private key — without that key ever leaving the vault. ║
# ║  Requires a fresh shadow-overlord signature on a server-issued  ║
# ║  challenge; nonce is single-use.                                ║
# ╚══════════════════════════════════════════════════════════════════╝

from __future__ import annotations

import hashlib
from typing import Any, Dict

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from web3 import Web3

from mindx_backend_service.bankon_vault import routes as _routes
from mindx_backend_service.bankon_vault.shadow_overlord import (
    SCOPE_AUTH,
    SCOPE_VAULT_SIGN,
    consume_signed_challenge,
    emit_shadow_audit,
    require_shadow_jwt,
)


sign_router = APIRouter(prefix="/vault/sign", tags=["vault-sign"])


class SignRequest(BaseModel):
    nonce: str
    signature: str
    message: str


@sign_router.post("/{agent_id:path}")
async def vault_sign(
    agent_id: str,
    req: SignRequest,
    _claims: Dict[str, Any] = Depends(require_shadow_jwt(SCOPE_AUTH)),
):
    """Sign `message` with the agent's private key, gated by shadow-overlord signature.

    The challenge bound to `nonce` must:
      - have scope == SCOPE_VAULT_SIGN
      - have params == {agent_id, message_sha256}

    Server recomputes message_sha256 from the request body, so a stolen JWT
    cannot redirect the signing oracle to a different payload.
    """
    expected_hash = "0x" + hashlib.sha256(req.message.encode("utf-8")).hexdigest()
    consume_signed_challenge(
        req.nonce,
        req.signature,
        expected_scope=SCOPE_VAULT_SIGN,
        expected_params={"agent_id": agent_id, "message_sha256": expected_hash},
    )
    from mindx_backend_service.bankon_vault.shadow_overlord import _shadow_address
    overlord = _shadow_address()

    pk_entry_id = f"{agent_id}:pk" if not agent_id.endswith(":pk") else agent_id

    if not _routes._vault.is_unlocked():
        try:
            _routes._vault.unlock_with_key_file()
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=f"vault locked: {e}")

    pk_hex = _routes._vault.retrieve(pk_entry_id)
    _routes._vault.lock()
    if not pk_hex:
        raise HTTPException(status_code=404, detail=f"no entry {pk_entry_id!r}")

    try:
        acct = Account.from_key(pk_hex)
        signable = encode_defunct(text=req.message)
        signed = acct.sign_message(signable)
        addr = Web3.to_checksum_address(acct.address)
    finally:
        # Best-effort zeroization. Python strings are immutable so we rely on
        # garbage collection; explicit overwrite of `pk_hex` here is informational
        # — the cryptographic guarantee is that the response carries no key field.
        pk_hex = None  # type: ignore[assignment]

    await emit_shadow_audit(
        "vault.sign",
        overlord,
        {"agent_id": agent_id, "address": addr, "message_sha256": expected_hash},
    )

    return {
        "agent_id": agent_id,
        "address": addr,
        "message_sha256": expected_hash,
        "signature": signed.signature.hex(),
    }
