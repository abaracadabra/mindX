# SPDX-License-Identifier: Apache-2.0
"""On-chain tier resolution for the bankon.eth hierarchical login.

Three tiers, decided by ENS holdings (read live — ownership transfers move the
tier automatically):

  admin   — owns bankon.eth (NameWrapper.ownerOf(node) == wallet)
  member  — holds any *.bankon.eth subname
  visitor — neither

Member detection (no on-chain enumeration exists):
  1. manual/explicit label  → NameWrapper.ownerOf(namehash(label.bankon.eth)) == wallet
                              (works for any wrapped subname, registrar-independent)
  2. auto-discovery          → scan BankonSubnameRegistrar SubnameRegistered(owner indexed)
                              logs (only when the registrar is deployed)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from eth_utils import keccak, to_checksum_address
from web3 import Web3

BANKON_ETH_NODE = bytes.fromhex(
    "79c178642317fc2d61d186f3b412440f06590d8314f126362d6a88929a6cbe1a"
)
NAME_WRAPPER = Web3.to_checksum_address("0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401")

_NAME_WRAPPER_ABI = [
    {
        "type": "function",
        "name": "ownerOf",
        "stateMutability": "view",
        "inputs": [{"name": "id", "type": "uint256"}],
        "outputs": [{"name": "", "type": "address"}],
    }
]
# SubnameRegistered(bytes32 indexed node, string label, address indexed owner, ...)
_SUBNAME_REGISTERED_TOPIC = "0x" + keccak(
    text="SubnameRegistered(bytes32,string,address,uint64,uint256,bytes32,uint256,bool)"
).hex()

ZERO = "0x0000000000000000000000000000000000000000"


def _rpc() -> str:
    return (
        os.environ.get("BANKON_GATE_RPC")
        or os.environ.get("MAINNET_RPC")
        or "https://ethereum-rpc.publicnode.com"
    )


def _w3() -> Web3:
    return Web3(Web3.HTTPProvider(_rpc(), request_kwargs={"timeout": 10}))


def _deployments(chain_id: int = 1) -> dict:
    name = "local" if chain_id == 31337 else str(chain_id)
    p = Path(__file__).resolve().parent.parent / "deployments" / f"{name}.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def subname_node(label: str) -> bytes:
    """namehash(label.bankon.eth) = keccak(bankonNode || keccak(label))."""
    return keccak(BANKON_ETH_NODE + keccak(text=label.lower()))


def owner_of(w3: Web3, node: bytes) -> Optional[str]:
    nw = w3.eth.contract(address=NAME_WRAPPER, abi=_NAME_WRAPPER_ABI)
    try:
        owner = nw.functions.ownerOf(int.from_bytes(node, "big")).call()
        return None if owner == ZERO else to_checksum_address(owner)
    except Exception:
        return None  # not minted / not wrapped


def owns_root(w3: Web3, address: str) -> bool:
    owner = owner_of(w3, BANKON_ETH_NODE)
    return owner is not None and owner.lower() == address.lower()


def owns_label(w3: Web3, address: str, label: str) -> bool:
    owner = owner_of(w3, subname_node(label))
    return owner is not None and owner.lower() == address.lower()


def discover_subnames(w3: Web3, address: str, chain_id: int = 1) -> list[str]:
    """Auto-discover *.bankon.eth held by `address` via SubnameRegistered logs.
    Returns [] when the registrar isn't deployed or the RPC rejects the range."""
    reg = (_deployments(chain_id).get("bankon", {}) or {}).get("subnameRegistrar", ZERO)
    if not reg or reg == ZERO:
        return []
    owner_topic = "0x" + address.lower().replace("0x", "").rjust(64, "0")
    try:
        logs = w3.eth.get_logs(
            {
                "address": Web3.to_checksum_address(reg),
                "fromBlock": "earliest",
                "toBlock": "latest",
                # topic0 = event sig, topic1 = node (any), topic2 = owner
                "topics": [_SUBNAME_REGISTERED_TOPIC, None, owner_topic],
            }
        )
    except Exception:
        return []
    # label is the first non-indexed arg; decode minimally from data.
    names: list[str] = []
    for lg in logs:
        try:
            label = _decode_first_string(bytes(lg["data"]))
            if label:
                names.append(f"{label}.bankon.eth")
        except Exception:
            continue
    return names


def _decode_first_string(data: bytes) -> Optional[str]:
    # ABI: head[0] = offset to the string (first dynamic arg). Read len + bytes.
    if len(data) < 32:
        return None
    off = int.from_bytes(data[:32], "big")
    if off + 32 > len(data):
        return None
    ln = int.from_bytes(data[off : off + 32], "big")
    raw = data[off + 32 : off + 32 + ln]
    return raw.decode("utf-8", "replace") if raw else None


def resolve_tier(address: str, *, label: Optional[str] = None, chain_id: int = 1) -> dict:
    """Return {tier, address, names?}. Reads ENS live; never trusts the client."""
    address = to_checksum_address(address)
    w3 = _w3()
    if owns_root(w3, address):
        return {"tier": "admin", "address": address, "root": "bankon.eth"}
    if label and owns_label(w3, address, label):
        return {"tier": "member", "address": address, "names": [f"{label.lower()}.bankon.eth"]}
    discovered = discover_subnames(w3, address, chain_id)
    if discovered:
        return {"tier": "member", "address": address, "names": discovered}
    return {"tier": "visitor", "address": address}
