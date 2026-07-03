# ╔══════════════════════════════════════════════════════════════════╗
# ║  BANKON Vault — Python Implementation                          ║
# ║  (c) BANKON — cypherpunk2048 standard · bankon.pythai.net      ║
# ║  License: GPL-3.0                                              ║
# ║                                                                ║
# ║  AES-256-GCM + HKDF-SHA512 encrypted credential storage       ║
# ║  Modular inclusion from pmVPN BANKON Vault specification       ║
# ╚══════════════════════════════════════════════════════════════════╝

from .vault import BankonVault
from .credential_provider import CredentialProvider
from .routes import router as bankon_vault_router
from .cabinet import (
    CABINET_ROLES,
    CabinetProvisioner,
)
from .admin_routes import (
    admin_router as shadow_admin_router,
    public_cabinet_router,
)
from .sign_routes import sign_router as vault_sign_router
from .shadow_overlord import (
    issue_challenge,
    issue_jwt,
    verify_jwt,
    verify_shadow_signature,
    consume_signed_challenge,
    require_shadow_jwt,
)

__all__ = [
    "BankonVault",
    "CredentialProvider",
    "bankon_vault_router",
    "CABINET_ROLES",
    "CabinetProvisioner",
    "shadow_admin_router",
    "public_cabinet_router",
    "vault_sign_router",
    "issue_challenge",
    "issue_jwt",
    "verify_jwt",
    "verify_shadow_signature",
    "consume_signed_challenge",
    "require_shadow_jwt",
]
