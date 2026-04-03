# ╔══════════════════════════════════════════════════════════════════╗
# ║  BANKON Vault API Routes — Admin-only credential management    ║
# ╚══════════════════════════════════════════════════════════════════╝

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from mindx_backend_service.bankon_vault.vault import BankonVault
from mindx_backend_service.bankon_vault.credential_provider import (
    CredentialProvider,
    PROVIDER_ENV_MAP,
)

router = APIRouter(prefix="/vault/credentials", tags=["bankon-vault"])

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
async def list_credentials():
    """List stored credentials (IDs and metadata only, no secrets)."""
    try:
        entries = _provider.list_credentials()
        return {"entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/store")
async def store_credential(req: StoreRequest):
    """Store a provider API key in the vault (AES-256-GCM encrypted)."""
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
async def delete_credential(req: DeleteRequest):
    """Delete a provider credential from the vault."""
    try:
        result = _provider.remove_credential(req.provider_id)
        if result:
            return {"status": "deleted", "provider_id": req.provider_id}
        raise HTTPException(status_code=404, detail=f"Not found: {req.provider_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
