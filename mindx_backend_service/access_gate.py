"""
Access gate: require wallet to hold NFT or fungible for session issuance.

Identity is still proved by wallet signature (public key). This module optionally
gates *issuance* of access (session + vault folder) on on-chain state:
- ERC20: wallet balanceOf >= min_balance at contract on chain.
- ERC721: wallet owns specific token id, or balanceOf(wallet) >= 1.

Uses JSON-RPC eth_call; no web3 dependency. Config via env:
  MINDX_ACCESS_GATE_ENABLED=true
  MINDX_ACCESS_GATE_CHAIN_ID=1
  MINDX_ACCESS_GATE_CONTRACT=0x...
  MINDX_ACCESS_GATE_TYPE=erc20|erc721
  MINDX_ACCESS_GATE_MIN_BALANCE=1          # for erc20 (wei/smallest unit) or erc721 (count)
  MINDX_ACCESS_GATE_TOKEN_ID=123           # optional; for erc721 "owns this token"
  MINDX_ACCESS_GATE_RPC_URL=https://...   # required when gate enabled
"""

import os
import re
import json
from typing import Tuple, Optional

import requests

from utils.logging_config import get_logger

logger = get_logger(__name__)

# Selectors (first 4 bytes of keccak256)
SELECTOR_BALANCE_OF = "0x70a08231"   # balanceOf(address)
SELECTOR_OWNER_OF = "0x6352211e"     # ownerOf(uint256)


def _addr_to_32hex(wallet_address: str) -> str:
    """Encode address as 32-byte hex (64 chars) for ABI."""
    raw = wallet_address.strip().lower()
    if raw.startswith("0x"):
        raw = raw[2:]
    return raw.zfill(64)


def _uint_to_32hex(value: int) -> str:
    """Encode uint256 as 32-byte hex."""
    h = hex(int(value))[2:].replace("L", "")
    return h.zfill(64)


def _eth_call(rpc_url: str, to: str, data: str, block: str = "latest") -> Optional[str]:
    """JSON-RPC eth_call. Returns result hex or None."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [{"to": to, "data": data}, block],
    }
    try:
        r = requests.post(rpc_url, json=payload, timeout=10)
        r.raise_for_status()
        out = r.json()
        if "error" in out:
            logger.warning(f"eth_call error: {out['error']}")
            return None
        return out.get("result")
    except Exception as e:
        logger.warning(f"eth_call request failed: {e}")
        return None


def _decode_uint32(hex_result: Optional[str]) -> Optional[int]:
    """Decode 32-byte uint from eth_call result (0x + 64 hex)."""
    if not hex_result or hex_result == "0x":
        return 0
    raw = hex_result[2:] if hex_result.startswith("0x") else hex_result
    if len(raw) < 64:
        raw = raw.zfill(64)
    return int(raw[:64], 16)


def _decode_address_32(hex_result: Optional[str]) -> Optional[str]:
    """Decode 20-byte address from last 40 hex chars of 32-byte result."""
    if not hex_result or hex_result == "0x":
        return None
    raw = hex_result[2:] if hex_result.startswith("0x") else hex_result
    if len(raw) < 64:
        raw = raw.zfill(64)
    return "0x" + raw[-40:].lower()


def check_access_gate(wallet_address: str) -> Tuple[bool, str]:
    """
    Check if the wallet satisfies the configured token gate (if any).
    Returns (allowed, message). allowed=True means issue session; False means 403 with message.
    """
    enabled = os.environ.get("MINDX_ACCESS_GATE_ENABLED", "").strip().lower() in ("1", "true", "yes")
    if not enabled:
        return True, ""

    rpc_url = os.environ.get("MINDX_ACCESS_GATE_RPC_URL", "").strip()
    if not rpc_url:
        logger.warning("MINDX_ACCESS_GATE_ENABLED but MINDX_ACCESS_GATE_RPC_URL not set")
        return False, "Access gate configured but RPC URL missing."

    contract = os.environ.get("MINDX_ACCESS_GATE_CONTRACT", "").strip()
    if not contract or not re.match(r"^0x[0-9a-fA-F]{40}$", contract):
        return False, "Access gate: invalid contract address."

    gate_type = os.environ.get("MINDX_ACCESS_GATE_TYPE", "").strip().lower()
    if gate_type not in ("erc20", "erc721"):
        return False, "Access gate: type must be erc20 or erc721."

    wallet = wallet_address.strip()
    if not wallet or not re.match(r"^0x[0-9a-fA-F]{40}$", wallet):
        return False, "Invalid wallet address."

    if gate_type == "erc20":
        min_balance_str = os.environ.get("MINDX_ACCESS_GATE_MIN_BALANCE", "1").strip()
        try:
            min_balance = int(min_balance_str)
        except ValueError:
            min_balance = 1
        data = SELECTOR_BALANCE_OF + _addr_to_32hex(wallet)
        result = _eth_call(rpc_url, contract, data)
        if result is None:
            return False, "Could not verify token balance; try again later."
        balance = _decode_uint32(result)
        if balance < min_balance:
            return False, f"Access requires holding at least {min_balance} token(s) at {contract}."
        return True, ""

    if gate_type == "erc721":
        token_id_str = os.environ.get("MINDX_ACCESS_GATE_TOKEN_ID", "").strip()
        if token_id_str:
            try:
                token_id = int(token_id_str)
            except ValueError:
                return False, "Access gate: invalid MINDX_ACCESS_GATE_TOKEN_ID."
            data = SELECTOR_OWNER_OF + _uint_to_32hex(token_id)
            result = _eth_call(rpc_url, contract, data)
            if result is None:
                return False, "Could not verify NFT ownership; try again later."
            owner = _decode_address_32(result)
            if owner is None:
                return False, "Could not verify NFT ownership; try again later."
            if owner != wallet.lower():
                return False, f"Access requires owning token id {token_id} from {contract}."
            return True, ""
        else:
            min_balance = 1
            data = SELECTOR_BALANCE_OF + _addr_to_32hex(wallet)
            result = _eth_call(rpc_url, contract, data)
            if result is None:
                return False, "Could not verify NFT balance; try again later."
            balance = _decode_uint32(result)
            if balance < min_balance:
                return False, f"Access requires holding at least one NFT from {contract}."
            return True, ""

    return False, "Access gate: unsupported type."
