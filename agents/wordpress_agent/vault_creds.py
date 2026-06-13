# SPDX-License-Identifier: Apache-2.0
"""BANKON vault loader for wordpress.agent — decrypt-on-demand, never in env.

The wordpress.agent's secrets live in one isolated vault namespace,
``context="wordpress.agent.keys"``:

    wordpress.agent:pk               -- wallet private key (hex)
    wordpress.agent:address          -- derived checksum address (public identity)
    wordpress.agent:wp_base_url      -- https://rage.pythai.net
    wordpress.agent:wp_user          -- WordPress username
    wordpress.agent:wp_app_password  -- WordPress Application Password (the API key)

None of these are loaded into ``os.environ`` at startup. The wordpress-agent service
opens the vault on each /publish, retrieves what it needs, then ``lock()``s. The WP
API key is plaintext only for the milliseconds of an authorized publish.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Optional

from .config import Settings

logger = logging.getLogger("wordpress_agent.vault_creds")

# Vault entry IDs. The :pk / :address suffixes match the /vault/sign/{agent_id}
# oracle convention so wordpress.agent can also sign via that route.
_AGENT_ID = "wordpress.agent"
ENTRY_PK = f"{_AGENT_ID}:pk"
ENTRY_ADDRESS = f"{_AGENT_ID}:address"
ENTRY_WP_BASE_URL = f"{_AGENT_ID}:wp_base_url"
ENTRY_WP_USER = f"{_AGENT_ID}:wp_user"
ENTRY_WP_APP_PASSWORD = f"{_AGENT_ID}:wp_app_password"

# All wordpress.agent secrets share this cryptographic namespace (HKDF context).
VAULT_CONTEXT = "wordpress.agent.keys"


def _open_unlocked_vault():
    """Open a BankonVault and unlock it (machine mode, with HumanOverseer fallback).

    Returns the unlocked vault, or ``None`` if it can't be unlocked.
    """
    try:
        from mindx_backend_service.bankon_vault.vault import BankonVault
    except Exception as e:
        logger.debug(f"BANKON vault module not importable here: {e}")
        return None

    vault = BankonVault()
    try:
        vault.unlock_with_key_file()
        return vault
    except RuntimeError as e:
        # HumanOverseer sentinel present — try the persisted proof file.
        try:
            from mindx_backend_service.bankon_vault import overseer as _ov
            proof = vault.vault_dir / ".overseer_proof.json"
            if proof.exists():
                ov, challenge, evidence = _ov.load_human_from_proof(proof, vault._salt)
                vault.unlock_with_overseer(ov, challenge, evidence)
                return vault
        except Exception as ee:
            logger.warning(f"vault HumanOverseer re-unlock failed: {ee}")
        logger.warning(f"vault unlock_with_key_file refused: {e}")
        return None
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(f"vault open failed: {e}")
        return None


def load_wp_settings_from_vault() -> Optional[Settings]:
    """Decrypt wordpress.agent's WP credentials and return a Settings, then re-lock.

    Returns ``None`` (logged) if the vault is unavailable, locked-without-proof, or
    any of the three required entries (base_url / user / app_password) is missing.
    Callers should treat ``None`` as "fall back to env" (dev only).
    """
    vault = _open_unlocked_vault()
    if vault is None:
        return None
    try:
        base_url = vault.retrieve(ENTRY_WP_BASE_URL)
        user = vault.retrieve(ENTRY_WP_USER)
        app_password = vault.retrieve(ENTRY_WP_APP_PASSWORD)
    finally:
        vault.lock()

    if not (base_url and user and app_password):
        logger.warning(
            "wordpress.agent vault namespace incomplete "
            f"(base_url={'set' if base_url else 'MISSING'}, "
            f"user={'set' if user else 'MISSING'}, "
            f"app_password={'set' if app_password else 'MISSING'})"
        )
        return None

    try:
        return Settings(  # type: ignore[call-arg]
            base_url=base_url,
            user=user,
            app_password=app_password,
        )
    except Exception as e:
        logger.warning(f"vault-sourced Settings rejected: {e}")
        return None


def sign_as(agent_id: str, message: str) -> Optional[tuple[str, str]]:
    """Sign ``message`` (typically a sha256/challenge string) with the vault key
    of *any* agent, by the ``{agent_id}:pk`` convention (same naming the
    /vault/sign/{agent_id} oracle uses). Returns ``(signature_hex, address)`` or
    ``None`` when that agent has no provisioned key — so callers can build a
    chain of custody across agents (ceo, soldiers, author.agent, editor.agent,
    artist.agent, wordpress.agent) and degrade gracefully on any missing link.

    Decrypts ``{agent_id}:pk`` and immediately re-locks; the private key never
    leaves this function's stack.
    """
    entry = agent_id if agent_id.endswith(":pk") else f"{agent_id}:pk"
    vault = _open_unlocked_vault()
    if vault is None:
        return None
    try:
        pk_hex = vault.retrieve(entry)
    finally:
        vault.lock()
    if not pk_hex:
        return None

    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
        from web3 import Web3
    except ImportError:  # pragma: no cover
        logger.warning("eth_account/web3 not available; cannot sign")
        return None

    try:
        acct = Account.from_key(pk_hex)
        signed = acct.sign_message(encode_defunct(text=message))
        signature = signed.signature.hex()
        if not signature.startswith("0x"):
            signature = "0x" + signature
        address = Web3.to_checksum_address(acct.address)
        return signature, address
    except Exception as e:
        logger.warning(f"sign_as({agent_id}) failed: {e}")
        return None
    finally:
        pk_hex = None  # best-effort GC hint; Python strings are immutable


def sign_with_agent_wallet(message: str) -> Optional[tuple[str, str]]:
    """Sign ``message`` with wordpress.agent's vault-held wallet key (the default
    publishing identity). Thin wrapper over :func:`sign_as`."""
    return sign_as(_AGENT_ID, message)


def sha256_hex(payload: str) -> str:
    """Helper — sha256 of a UTF-8 string, returned as ``0x``-prefixed hex."""
    return "0x" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "load_wp_settings_from_vault",
    "sign_with_agent_wallet",
    "sign_as",
    "sha256_hex",
    "ENTRY_PK",
    "ENTRY_ADDRESS",
    "ENTRY_WP_BASE_URL",
    "ENTRY_WP_USER",
    "ENTRY_WP_APP_PASSWORD",
    "VAULT_CONTEXT",
]
