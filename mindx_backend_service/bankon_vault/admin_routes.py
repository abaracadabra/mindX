# ╔══════════════════════════════════════════════════════════════════╗
# ║  BANKON Vault — Shadow-Overlord Admin Routes                    ║
# ║                                                                  ║
# ║  /admin/shadow/{challenge,verify}                               ║
# ║  /admin/cabinet/{company}/{preflight,provision,clear}           ║
# ║  /admin/shadow/release-key/{agent_id}                           ║
# ║  /cabinet/{company}                       (public)              ║
# ╚══════════════════════════════════════════════════════════════════╝

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from mindx_backend_service.bankon_vault.cabinet import (
    CabinetExists,
    CabinetMissing,
    CabinetProvisioner,
    vault_pk_id,
)
from mindx_backend_service.bankon_vault import routes as _routes  # access _routes._vault lazily
from mindx_backend_service.bankon_vault.shadow_overlord import (
    SCOPE_AUTH,
    SCOPE_CABINET_CLEAR,
    SCOPE_CABINET_PROVISION,
    SCOPE_RELEASE_KEY,
    consume_signed_challenge,
    emit_shadow_audit,
    issue_challenge,
    issue_jwt,
    require_shadow_jwt,
    verify_shadow_signature,
)


admin_router = APIRouter(prefix="/admin", tags=["shadow-overlord"])
public_cabinet_router = APIRouter(prefix="/cabinet", tags=["cabinet"])

_provisioner: Optional[CabinetProvisioner] = None


def _get_provisioner() -> CabinetProvisioner:
    """Lazy provisioner so tests can swap routes._vault before first use."""
    global _provisioner
    if _provisioner is None:
        _provisioner = CabinetProvisioner(_routes._vault)
    return _provisioner


# ─── pydantic ─────────────────────────────────────────────────────


class ChallengeRequest(BaseModel):
    scope: str
    params: Optional[Dict[str, Any]] = None


class VerifyRequest(BaseModel):
    nonce: str
    signature: str


class ProvisionRequest(BaseModel):
    nonce: str
    signature: str


class ClearRequest(BaseModel):
    nonce: str
    signature: str
    confirm: str  # must literally equal "DESTROY-{COMPANY}-CABINET"


class ReleaseRequest(BaseModel):
    nonce: str
    signature: str
    confirm: str  # must literally equal "RELEASE-PRIVATE-KEY"


# ─── /admin/shadow/{challenge,verify} ─────────────────────────────


@admin_router.post("/shadow/challenge")
async def shadow_challenge(req: ChallengeRequest):
    """Issue a fresh server-canonical challenge bound to a scope and params.

    Public endpoint — anyone can request a challenge, but only the
    shadow-overlord (matching SHADOW_OVERLORD_ADDRESS) can sign it.
    """
    return issue_challenge(req.scope, req.params)


@admin_router.post("/shadow/verify")
async def shadow_verify(req: VerifyRequest):
    """Consume an auth-scope challenge; on success, issue a 5-minute JWT."""
    consume_signed_challenge(req.nonce, req.signature, expected_scope=SCOPE_AUTH)
    from mindx_backend_service.bankon_vault.shadow_overlord import _shadow_address
    addr = _shadow_address()
    res = issue_jwt(addr, scope=SCOPE_AUTH, jti=req.nonce)
    await emit_shadow_audit("auth.success", addr, {"jti": req.nonce})
    return res


# ─── /admin/cabinet/{company}/* ───────────────────────────────────


@admin_router.get("/cabinet/{company}/preflight")
async def cabinet_preflight(
    company: str,
    _claims: Dict[str, Any] = Depends(require_shadow_jwt(SCOPE_AUTH)),
):
    return _get_provisioner().preflight(company)


@admin_router.post("/cabinet/{company}/provision")
async def cabinet_provision(
    company: str,
    req: ProvisionRequest,
    _claims: Dict[str, Any] = Depends(require_shadow_jwt(SCOPE_AUTH)),
):
    """Mint 8 wallets (CEO + 7 soldiers) into the vault under company namespace."""
    consume_signed_challenge(
        req.nonce,
        req.signature,
        expected_scope=SCOPE_CABINET_PROVISION,
        expected_params={"company": company},
    )
    from mindx_backend_service.bankon_vault.shadow_overlord import _shadow_address
    addr = _shadow_address()

    if not _routes._vault.is_unlocked():
        try:
            _routes._vault.unlock_with_key_file()
        except RuntimeError as e:
            raise HTTPException(
                status_code=503,
                detail=f"vault locked under HumanOverseer custody — POST /vault/credentials/reunlock first ({e})",
            )

    try:
        result = _get_provisioner().provision(company, addr)
    except CabinetExists as e:
        raise HTTPException(status_code=409, detail=str(e))
    finally:
        _routes._vault.lock()

    await emit_shadow_audit(
        "cabinet.provision",
        addr,
        {"company": company, "ceo": result.get("ceo"), "soldier_count": len(result.get("soldiers", {}))},
    )
    return result


@admin_router.post("/cabinet/{company}/clear")
async def cabinet_clear(
    company: str,
    req: ClearRequest,
    _claims: Dict[str, Any] = Depends(require_shadow_jwt(SCOPE_AUTH)),
):
    expected_confirm = f"DESTROY-{company.upper()}-CABINET"
    if req.confirm != expected_confirm:
        raise HTTPException(
            status_code=400,
            detail=f"confirm string must equal {expected_confirm!r}",
        )
    consume_signed_challenge(
        req.nonce,
        req.signature,
        expected_scope=SCOPE_CABINET_CLEAR,
        expected_params={"company": company},
    )
    from mindx_backend_service.bankon_vault.shadow_overlord import _shadow_address
    addr = _shadow_address()

    if not _routes._vault.is_unlocked():
        try:
            _routes._vault.unlock_with_key_file()
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=f"vault locked: {e}")

    try:
        result = _get_provisioner().clear(company)
    except CabinetMissing as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        _routes._vault.lock()

    await emit_shadow_audit("cabinet.clear", addr, {"company": company, **result})
    return result


# ─── /admin/shadow/release-key/{agent_id} ────────────────────────


@admin_router.post("/shadow/release-key/{agent_id:path}")
async def release_private_key(
    agent_id: str,
    req: ReleaseRequest,
    _claims: Dict[str, Any] = Depends(require_shadow_jwt(SCOPE_AUTH)),
):
    """Emergency: release a single private key in plaintext. One-time, audited."""
    if req.confirm != "RELEASE-PRIVATE-KEY":
        raise HTTPException(
            status_code=400,
            detail='confirm string must equal "RELEASE-PRIVATE-KEY"',
        )
    consume_signed_challenge(
        req.nonce,
        req.signature,
        expected_scope=SCOPE_RELEASE_KEY,
        expected_params={"agent_id": agent_id},
    )
    from mindx_backend_service.bankon_vault.shadow_overlord import _shadow_address
    addr = _shadow_address()

    pk_entry_id = f"{agent_id}:pk" if not agent_id.endswith(":pk") else agent_id
    if not _routes._vault.is_unlocked():
        try:
            _routes._vault.unlock_with_key_file()
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=f"vault locked: {e}")
    try:
        pk_hex = _routes._vault.retrieve(pk_entry_id)
    finally:
        _routes._vault.lock()
    if not pk_hex:
        raise HTTPException(status_code=404, detail=f"no entry {pk_entry_id!r}")

    await emit_shadow_audit(
        "release.key",
        addr,
        {"agent_id": agent_id, "pk_entry_id": pk_entry_id, "released": True},
    )
    return {"private_key_hex": pk_hex, "agent_id": agent_id}


# ─── public read ─────────────────────────────────────────────────


@public_cabinet_router.get("/{company}")
async def cabinet_public(company: str):
    """Public read — only addresses, entity_ids, role labels. No vault_pk_id leak."""
    try:
        return _get_provisioner().read_public(company)
    except CabinetMissing:
        raise HTTPException(status_code=404, detail=f"no cabinet for {company!r}")
