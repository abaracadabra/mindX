"""OpenAgents contract registry — generic ABI loader for all 12 deployed contracts.

Loads addresses from openagents/deployments/<network>.json and ABIs from the
foundry build output (or vendored copies under openagents/contracts/abi/).
Returns ready-to-call web3 Contract instances.

Usage:

    from openagents.contracts.registry import OpenAgentsContracts

    # Read-only
    oac = OpenAgentsContracts(network="0g_mainnet")
    total = oac.AgentRegistry.functions.totalSupply().call()
    name  = oac.iNFT_7857.functions.name().call()

    # With signer (for state-changing calls)
    oac = OpenAgentsContracts(network="0g_mainnet", signer_pk="0x...")
    tx = oac.DatasetRegistry.functions.registerDataset(
        b"\\x00" * 32, "ipfs://Qm..."
    ).build_transaction({"from": oac.signer.address, "nonce": ...})

    # Introspect
    oac.list()                 # ['AgentRegistry', 'THOT', 'iNFT_7857', ...]
    oac.address("AgentRegistry") # "0x..."
    oac.abi("AgentRegistry")     # [...]

The registry maps each contract to a (foundry_path, vendored_abi_path)
tuple. Vendored ABIs live at openagents/contracts/abi/<Contract>.json so
the runtime doesn't depend on a fresh foundry build.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from web3 import Web3

logger = logging.getLogger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_OPENAGENTS_ROOT = _HERE.parent
_REPO_ROOT = _OPENAGENTS_ROOT.parent
_DEPLOYMENTS_DIR = _OPENAGENTS_ROOT / "deployments"
_VENDORED_ABI_DIR = _HERE / "abi"

# Foundry build output candidates — we probe these in order
_FOUNDRY_OUT_DIRS = [
    _REPO_ROOT / "daio" / "contracts" / "out",
    _REPO_ROOT / "openagents" / "conclave" / "contracts" / "out",
]

# ─── Network presets ─────────────────────────────────────────────────
_NETWORK_RPC = {
    "0g_mainnet":      "https://evmrpc.0g.ai",
    "anvil":           "http://127.0.0.1:8545",
    "sepolia":         "https://sepolia.drpc.org",
    "ethereum_mainnet":"https://eth.drpc.org",
    "anvil_bankon":    "http://127.0.0.1:8545",
}
_NETWORK_CHAIN_ID = {
    "0g_mainnet": 16661,
    "anvil": 31337,
    "sepolia": 11155111,
    "ethereum_mainnet": 1,
    "anvil_bankon": 31337,
}


# ─── Contract catalog ────────────────────────────────────────────────
@dataclass
class ContractSpec:
    """Maps a contract name to its source files for ABI resolution."""
    name: str            # canonical name in deployments JSON
    foundry_path: str    # e.g. "AgentRegistry.sol/AgentRegistry.json"
    group: str           # "A" (0G mainnet) or "B" (Eth)


CATALOG: List[ContractSpec] = [
    # Group A — 0G mainnet (8 contracts)
    ContractSpec("AgentRegistry",   "AgentRegistry.sol/AgentRegistry.json",     "A"),
    ContractSpec("THOT",            "THOT.sol/THOT.json",                       "A"),
    ContractSpec("iNFT_7857",       "iNFT_7857.sol/iNFT_7857.json",             "A"),
    ContractSpec("DatasetRegistry", "DatasetRegistry.sol/DatasetRegistry.json", "A"),
    ContractSpec("Tessera",         "Tessera.sol/Tessera.json",                 "A"),
    ContractSpec("Censura",         "Censura.sol/Censura.json",                 "A"),
    ContractSpec("Conclave",        "Conclave.sol/Conclave.json",               "A"),
    ContractSpec("ConclaveBond",    "ConclaveBond.sol/ConclaveBond.json",       "A"),
    # Group B — Eth (4 BANKON contracts)
    ContractSpec("BankonPriceOracle",       "BankonPriceOracle.sol/BankonPriceOracle.json",             "B"),
    ContractSpec("BankonReputationGate",    "BankonReputationGate.sol/BankonReputationGate.json",       "B"),
    ContractSpec("BankonPaymentRouter",     "BankonPaymentRouter.sol/BankonPaymentRouter.json",         "B"),
    ContractSpec("BankonSubnameRegistrar",  "BankonSubnameRegistrar.sol/BankonSubnameRegistrar.json",   "B"),
]
CATALOG_BY_NAME = {c.name: c for c in CATALOG}


# ─── ABI loader ──────────────────────────────────────────────────────
def _load_abi(spec: ContractSpec) -> List[Dict[str, Any]]:
    """Resolve ABI from vendored copy first, then foundry build dirs.

    Vendored ABIs are stable across runtimes; foundry out/ may not exist
    in production environments where contracts shipped pre-compiled.
    """
    # 1. Vendored — preferred for production runtime
    vendored = _VENDORED_ABI_DIR / f"{spec.name}.json"
    if vendored.exists():
        try:
            data = json.loads(vendored.read_text())
            # accept either {abi: [...]} or just [...]
            return data["abi"] if isinstance(data, dict) and "abi" in data else data
        except Exception as e:
            logger.warning(f"vendored ABI {spec.name} unreadable: {e}")

    # 2. Foundry build dirs
    for out_dir in _FOUNDRY_OUT_DIRS:
        candidate = out_dir / spec.foundry_path
        if candidate.exists():
            try:
                return json.loads(candidate.read_text())["abi"]
            except Exception as e:
                logger.warning(f"foundry ABI {candidate} unreadable: {e}")

    raise FileNotFoundError(
        f"ABI for '{spec.name}' not found. Looked at:\n"
        f"  {vendored}\n"
        + "\n".join(f"  {d / spec.foundry_path}" for d in _FOUNDRY_OUT_DIRS)
        + "\nRun `forge build` in daio/contracts and openagents/conclave/contracts, "
        f"or vendor the ABI to {vendored}."
    )


# ─── Deployments loader ─────────────────────────────────────────────
def _load_deployments(network: str) -> Dict[str, Any]:
    path = _DEPLOYMENTS_DIR / f"{network}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"deployments file {path} not found. Run the deploy script for "
            f"this network first (openagents/deploy/deploy_*.sh)."
        )
    return json.loads(path.read_text())


# ─── Public API ──────────────────────────────────────────────────────
class OpenAgentsContracts:
    """Lazy-loaded registry of all deployed openagents contracts.

    Access contracts as attributes: `registry.AgentRegistry`, `registry.THOT`,
    etc. Each access returns a web3 Contract instance bound to the chain's
    RPC and the deployed address.
    """

    def __init__(
        self,
        network: str = "0g_mainnet",
        rpc_url: Optional[str] = None,
        signer_pk: Optional[str] = None,
    ):
        if network not in _NETWORK_RPC:
            raise ValueError(f"unknown network '{network}'. Supported: {list(_NETWORK_RPC)}")
        self.network = network
        self.rpc_url = rpc_url or os.environ.get(f"{network.upper()}_RPC_URL") or _NETWORK_RPC[network]
        self.chain_id = _NETWORK_CHAIN_ID[network]
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            logger.warning(f"RPC {self.rpc_url} unreachable; reads will fail until it is.")

        self.deployments = _load_deployments(network)
        self.addresses: Dict[str, str] = self.deployments.get("contracts", {})
        self._contracts: Dict[str, Any] = {}

        self.signer = None
        if signer_pk:
            from eth_account import Account
            self.signer = Account.from_key(signer_pk)

    # ─── Introspection ───────────────────────────────────────────
    def list(self) -> List[str]:
        """Names of contracts deployed on this network."""
        return [c.name for c in CATALOG if c.name in self.addresses]

    def address(self, name: str) -> str:
        if name not in self.addresses:
            raise KeyError(f"'{name}' not deployed on '{self.network}'. "
                           f"Have: {list(self.addresses)}")
        return self.addresses[name]

    def abi(self, name: str) -> List[Dict[str, Any]]:
        if name not in CATALOG_BY_NAME:
            raise KeyError(f"unknown contract '{name}'. Catalog: {[c.name for c in CATALOG]}")
        return _load_abi(CATALOG_BY_NAME[name])

    # ─── Contract instance access ────────────────────────────────
    def get(self, name: str):
        """Return a web3 Contract instance for `name`."""
        if name in self._contracts:
            return self._contracts[name]
        addr = self.address(name)
        abi  = self.abi(name)
        c = self.w3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)
        self._contracts[name] = c
        return c

    def __getattr__(self, name: str):
        # Allow `registry.AgentRegistry` → contract instance
        if name.startswith("_") or name in ("network", "rpc_url", "chain_id", "w3",
                                              "deployments", "addresses", "signer"):
            raise AttributeError(name)
        try:
            return self.get(name)
        except KeyError:
            raise AttributeError(name)

    # ─── Catalog summary ─────────────────────────────────────────
    def summary(self) -> Dict[str, Any]:
        """Snapshot suitable for /api/contracts response."""
        return {
            "network": self.network,
            "chain_id": self.chain_id,
            "rpc": self.rpc_url,
            "deployer": self.deployments.get("deployer"),
            "contracts": [
                {
                    "name": spec.name,
                    "address": self.addresses.get(spec.name),
                    "deployed": spec.name in self.addresses,
                    "group": spec.group,
                }
                for spec in CATALOG
            ],
        }


# ─── CLI smoke harness ─────────────────────────────────────────────
def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="OpenAgents contracts registry smoke test")
    parser.add_argument("--network", default="0g_mainnet",
                        choices=list(_NETWORK_RPC.keys()))
    parser.add_argument("--list",   action="store_true", help="list deployed contracts")
    parser.add_argument("--summary",action="store_true", help="full catalog snapshot")
    parser.add_argument("--call",   help="contract.method to call (read-only)")
    parser.add_argument("--args",   nargs="*", default=[], help="positional args for --call")
    args = parser.parse_args()

    try:
        oac = OpenAgentsContracts(network=args.network)
    except FileNotFoundError as e:
        print(f"deployments missing: {e}")
        return 1

    if args.list:
        for name in oac.list():
            print(f"  {name:32} {oac.address(name)}")
    elif args.summary:
        print(json.dumps(oac.summary(), indent=2))
    elif args.call:
        contract_name, method = args.call.split(".", 1)
        c = oac.get(contract_name)
        fn = getattr(c.functions, method)
        result = fn(*args.args).call()
        print(json.dumps({"contract": contract_name, "method": method,
                          "args": args.args, "result": str(result)}, indent=2))
    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
