"""
Contract address resolution for the blockchain.agents module.

Addresses are loaded from `data/config/blockchain_addresses.json` keyed by
stringified chain id. If that file lacks an entry for the requested chain, we
fall back to reading the Foundry deploy receipt written by
`daio/contracts/script/DeployTier1.s.sol` at
`daio/contracts/deployments/<chainId>/tier1.json`.

This keeps the Python side agnostic: the canonical source of truth is whatever
`forge script DeployTier1` produced; the JSON config is a convenience cache the
bootstrap script populates.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

# tier1.json key -> our canonical name
_TIER1_KEYS = {
    "inft7857": "inft7857",
    "agentRegistry": "agentRegistry",
    "thot": "thot",
    "x402Receipt": "x402Receipt",
    "bankonSubnameRegistrar": "bankonSubnameRegistrar",
}

DEFAULT_RPC_URLS = {
    1337: "http://127.0.0.1:8545",
    31337: "http://127.0.0.1:8545",
}

# Well-known Anvil account[0] — the DeployTier1 deployer/owner/MINTER on a fresh
# local node. Used only as a local-dev default; override with BLOCKCHAIN_MINTER_PK.
ANVIL_ACCOUNT0_PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


@dataclass
class ChainContracts:
    chain_id: int
    rpc_url: str
    inft7857: Optional[str] = None
    agentRegistry: Optional[str] = None
    thot: Optional[str] = None
    x402Receipt: Optional[str] = None
    bankonSubnameRegistrar: Optional[str] = None
    # Optional standalone marketplace / bankon vault (not in Tier1; config-only).
    agenticPlace: Optional[str] = None
    bankonVault: Optional[str] = None

    @property
    def mintable(self) -> bool:
        return bool(self.inft7857)


def _config_path() -> str:
    return os.path.join(str(PROJECT_ROOT), "data", "config", "blockchain_addresses.json")


def _tier1_path(chain_id: int) -> str:
    return os.path.join(
        str(PROJECT_ROOT), "daio", "contracts", "deployments", str(chain_id), "tier1.json"
    )


def _load_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(f"blockchain.contracts: failed to read {path}: {e}")
        return None


def load_contracts(chain_id: int = 1337, rpc_url: Optional[str] = None) -> ChainContracts:
    """Resolve contract addresses for a chain.

    Precedence: data/config/blockchain_addresses.json -> forge tier1.json.
    Always returns a ChainContracts (possibly with empty addresses if nothing
    is deployed yet); callers check `.mintable`.
    """
    rpc = (
        rpc_url
        or os.environ.get("BLOCKCHAIN_RPC_URL")
        or DEFAULT_RPC_URLS.get(chain_id, "http://127.0.0.1:8545")
    )
    cc = ChainContracts(chain_id=chain_id, rpc_url=rpc)

    cfg = _load_json(_config_path()) or {}
    entry = cfg.get(str(chain_id)) or {}

    # tier1 fallback fills anything the config omits
    tier1 = _load_json(_tier1_path(chain_id)) or {}
    merged = {**tier1, **entry}  # config wins over forge receipt

    cc.inft7857 = merged.get("inft7857") or merged.get("iNFT7857")
    cc.agentRegistry = merged.get("agentRegistry")
    cc.thot = merged.get("thot")
    cc.x402Receipt = merged.get("x402Receipt")
    cc.bankonSubnameRegistrar = merged.get("bankonSubnameRegistrar")
    cc.agenticPlace = merged.get("agenticPlace")
    cc.bankonVault = merged.get("bankonVault")
    return cc


def minter_private_key() -> str:
    """Private key the factory signs mint txs with.

    Order: BLOCKCHAIN_MINTER_PK env -> MEMORY_ANCHOR_TREASURY_PK env ->
    Anvil account[0] (local-dev default, holds MINTER_ROLE on a fresh DeployTier1).
    """
    return (
        os.environ.get("BLOCKCHAIN_MINTER_PK")
        or os.environ.get("MEMORY_ANCHOR_TREASURY_PK")
        or ANVIL_ACCOUNT0_PK
    )
