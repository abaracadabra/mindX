"""
Per-(participant, chain) deploy-key resolution.

The deployer signing key is a *vault-scoped* key, NOT the UI wallet (the UI
wallet only authorizes; see authorization.py). Resolution mirrors
`agents/blockchain/contracts.py::minter_private_key` env layering and reuses
`IDManagerAgent.get_private_key_for_guardian` for vault retrieval.

Entity-id convention for deploy keys:
    EVM:      blockchain.deployer.<chain>     (e.g. blockchain.deployer.base-sepolia)
    Algorand: algorand.deployer.<chain>       (e.g. algorand.deployer.algorand-testnet)
"""

from __future__ import annotations

import os
from typing import Optional

from utils.logging_config import get_logger

logger = get_logger(__name__)

# Anvil account[0] — local-dev default for chain 1337/31337 only.
ANVIL_ACCOUNT0_PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def _env_chain_suffix(chain: str) -> str:
    return chain.upper().replace("-", "_").replace(".", "_")


async def resolve_deployer_key(deployer_entity: str, chain: str, chain_id: int) -> Optional[str]:
    """EVM deployer private key (hex).

    Order: explicit per-chain env -> generic env -> vault (id_manager) ->
    Anvil default (local chains only).
    """
    suffix = _env_chain_suffix(chain)
    # 1. explicit per-chain env
    pk = os.environ.get(f"DEPLOYER_PRIVATE_KEY_{suffix}") or os.environ.get(f"BLOCKCHAIN_MINTER_PK_{suffix}")
    if pk:
        return pk
    # 2. generic env
    pk = os.environ.get("DEPLOYER_PRIVATE_KEY") or os.environ.get("BLOCKCHAIN_MINTER_PK")
    if pk:
        return pk
    # 3. vault, scoped to the deploy entity
    try:
        from agents.core.id_manager_agent import IDManagerAgent

        idm = await IDManagerAgent.get_instance()
        pk = idm.get_private_key_for_guardian(deployer_entity)
        if pk:
            return pk
    except Exception as e:  # pragma: no cover - vault optional
        logger.debug(f"deployer key vault lookup failed for {deployer_entity}: {e}")
    # 4. local-dev default
    if chain_id in (1337, 31337):
        return ANVIL_ACCOUNT0_PK
    return None


async def resolve_deployer_mnemonic(deployer_entity: str, chain: str, mnemonic_env: str) -> Optional[str]:
    """Algorand deployer 25-word mnemonic.

    Order: stage-declared env -> per-chain env -> x402 convention env -> vault.
    """
    suffix = _env_chain_suffix(chain)
    for key in (mnemonic_env, f"ALGORAND_DEPLOYER_MNEMONIC_{suffix}", "ALGORAND_DEPLOYER_MNEMONIC", "ALGORAND_MNEMONIC"):
        if key:
            val = os.environ.get(key)
            if val:
                return val
    try:
        from agents.core.id_manager_agent import IDManagerAgent

        idm = await IDManagerAgent.get_instance()
        # vault may hold the mnemonic under the deploy entity id
        val = idm.get_private_key_for_guardian(deployer_entity)
        if val and len(val.split()) >= 24:  # looks like a mnemonic, not a hex key
            return val
    except Exception as e:  # pragma: no cover
        logger.debug(f"algorand mnemonic vault lookup failed for {deployer_entity}: {e}")
    return None
