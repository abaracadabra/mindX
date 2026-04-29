# ╔══════════════════════════════════════════════════════════════════╗
# ║  BANKON Vault API Routes — Admin-only credential management    ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from mindx_backend_service.bankon_vault.vault import BankonVault
from mindx_backend_service.bankon_vault.credential_provider import (
    CredentialProvider,
    PROVIDER_ENV_MAP,
)
from mindx_backend_service.bankon_vault.overseer import (
    HumanOverseer,
    load_human_from_proof,
)

# Admin-auth dep — lists/mutations require a valid session bound to an
# address in security.admin_addresses.  See the custody-handoff plan:
# https://.../glimmering-growing-scroll.md §"Route authentication".
try:
    from mindx_backend_service.security_middleware import require_admin_access
except ImportError:  # pragma: no cover — only hit if security_middleware is unavailable
    require_admin_access = None  # type: ignore

router = APIRouter(prefix="/vault/credentials", tags=["bankon-vault"])


def _admin_dep():
    """Return the admin-auth dependency if available; else a pass-through
    that raises 503 at request time (never silently allow unauth access)."""
    if require_admin_access is not None:
        return Depends(require_admin_access)

    async def _unavailable():
        raise HTTPException(status_code=503, detail="admin auth unavailable")
    return Depends(_unavailable)

# Singleton vault instance (created at import, unlocked on demand)
_vault = BankonVault()
_provider = CredentialProvider(_vault)


class StoreRequest(BaseModel):
    provider_id: str
    value: str


class DeleteRequest(BaseModel):
    provider_id: str


@router.get("/status")
async def vault_status():
    """BANKON Vault status (no secrets exposed)."""
    info = _vault.info()
    info.pop("vault_dir", None)  # Don't expose filesystem paths
    return info


@router.get("/providers")
async def list_providers():
    """List all supported provider IDs and their env var mappings."""
    return {
        "providers": [
            {"id": k, "env_var": v}
            for k, v in sorted(PROVIDER_ENV_MAP.items())
        ]
    }


@router.get("/list")
async def list_credentials(wallet: str = _admin_dep()):
    """List stored credentials (IDs and metadata only, no secrets).  ADMIN ONLY."""
    try:
        entries = _provider.list_credentials()
        return {"entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/store")
async def store_credential(req: StoreRequest, wallet: str = _admin_dep()):
    """Store a provider API key in the vault (AES-256-GCM encrypted).  ADMIN ONLY."""
    try:
        _provider.store_credential(req.provider_id, req.value)
        return {
            "status": "stored",
            "provider_id": req.provider_id,
            "cipher": "aes-256-gcm",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete")
async def delete_credential(req: DeleteRequest, wallet: str = _admin_dep()):
    """Delete a provider credential from the vault.  ADMIN ONLY."""
    try:
        result = _provider.remove_credential(req.provider_id)
        if result:
            return {"status": "deleted", "provider_id": req.provider_id}
        raise HTTPException(status_code=404, detail=f"Not found: {req.provider_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────
# Sentinel-mode re-unlock — recovers credential loading after a service
# restart where unlock_with_key_file refused (HumanOverseer custody).
#
# Flow A (default): vault dir has .overseer_proof.json — re-unlock by
# replaying the persisted EIP-191 signature. No new signing needed.
#
# Flow B (fallback): caller supplies fresh {address, signature, message}
# in the request body. Used when the proof file is lost.
#
# Either way: after unlock, every PROVIDER_ENV_MAP entry is loaded into
# os.environ so the rest of the service (LLM factory, IPFS provider,
# chain anchor) can run; vault is then locked again.
# ─────────────────────────────────────────────────────────────────────────


class ReunlockRequest(BaseModel):
    address: Optional[str] = None
    signature: Optional[str] = None
    message: Optional[str] = None


@router.post("/reunlock")
async def reunlock(
    req: Optional[ReunlockRequest] = None,
    wallet: str = _admin_dep(),
):
    """Re-unlock the vault under HumanOverseer custody and re-populate
    provider credentials in os.environ.  ADMIN ONLY.

    Body shape:
      - {} or absent  → use .overseer_proof.json from disk (Flow A)
      - {"address", "signature", "message"} → fresh evidence (Flow B)
    """
    sentinel = _vault.vault_dir / ".human_overseer_active"
    if not sentinel.exists():
        raise HTTPException(
            status_code=409,
            detail="vault is not under HumanOverseer custody — "
                   "use unlock_with_key_file path / restart the service",
        )

    proof_path = _vault.vault_dir / ".overseer_proof.json"
    have_body_evidence = bool(
        req and req.address and req.signature and req.message
    )

    try:
        if have_body_evidence:
            assert req is not None  # mypy
            overseer = HumanOverseer(
                eth_address=req.address,
                vault_salt=_vault._salt,
            )
            sig = req.signature if req.signature.startswith("0x") else "0x" + req.signature
            evidence = {
                "kind": "human",
                "signature": sig,
                "message": req.message,
            }
            challenge_bytes = req.message.encode("utf-8")
        elif proof_path.exists():
            overseer, challenge_bytes, evidence = load_human_from_proof(
                proof_path, _vault._salt,
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"{proof_path.name} missing and no body evidence supplied — "
                       "either restore the proof file or POST {address, signature, message}",
            )

        if _vault.is_unlocked():
            _vault.lock()  # force a clean unlock path

        _vault.unlock_with_overseer(overseer, challenge_bytes, evidence)

        loaded: list[str] = []
        for vault_id, env_var in PROVIDER_ENV_MAP.items():
            value = _vault.retrieve(vault_id)
            if value:
                os.environ[env_var] = value
                loaded.append(env_var)

        _vault.lock()
        return {
            "status": "unlocked",
            "fingerprint": overseer.fingerprint(),
            "providers_loaded": len(loaded),
            "env_vars": loaded,
            "source": "body_evidence" if have_body_evidence else "proof_file",
        }
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=f"unlock failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
