# SPDX-License-Identifier: Apache-2.0
"""
overlord.resolver — the mindX (Python) authority for the overlord/overseer
privilege model. A faithful mirror of openagents/overlord/src/{resolver,
capabilities,holdings}.ts — KEEP IN SYNC with that canonical module.

One privilege axis, public at the floor (privilege = the access the public
lacks), levels within each role:

  public   — no qualifying holding ⇒ no privileged access
  member   — holds the qualifying asset ⇒ privileged; level = f(amount, tenure)
  overseer — moderator / distributor of privilege (signature-proven address)
  overlord — admin (SHADOW_OVERLORD_ADDRESS); the only role that may run
             DESTRUCTIVE ops

Identity = a public wallet key proven by signature (ECDSA recover, reusing
shadow_overlord.recover_signer). Privilege = on-chain holdings (balanceOf), and
a holding's blockchain timestamp (earliest inbound Transfer block) gives tenure,
measured against chronos promised time. resolve_privilege() is a pure-ish
function of (address, signature, holdings, tenure, chronos); holdings/tenure are
injectable for tests.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from eth_utils import to_checksum_address

from .config import HoldingConfig, LevelBand, OverlordConfig

logger = logging.getLogger("mindx.overlord.resolver")

ROLE_ORDINAL = {"public": 0, "member": 1, "overseer": 2, "overlord": 3}

# Integrity-affecting actions — overlord ONLY, at any level. This is the
# intentional separation: the overseer distributes/moderates privilege but
# cannot destroy system integrity.
DESTRUCTIVE = frozenset({"clear", "destroy.cabinet", "rotate.keys", "release.key"})

_CAPS = {
    "public": frozenset({"read.public"}),
    "member": frozenset({"read.public", "read.member", "act.member"}),
    "overseer": frozenset(
        {"read.public", "read.member", "act.member", "distribute.privilege", "moderate", "admin.read"}
    ),
    "overlord": frozenset(
        {
            "read.public", "read.member", "act.member", "distribute.privilege",
            "moderate", "admin.read", "clear", "destroy.cabinet", "rotate.keys", "release.key",
        }
    ),
}


def can(role: str, action: str) -> bool:
    """Capability check. Destructive actions are overlord-only by construction."""
    if action in DESTRUCTIVE:
        return role == "overlord"
    return action in _CAPS.get(role, frozenset())


def is_privileged(role: str) -> bool:
    return ROLE_ORDINAL.get(role, 0) >= ROLE_ORDINAL["member"]


def _addr_eq(a: str, b: str) -> bool:
    try:
        return to_checksum_address(a) == to_checksum_address(b)
    except Exception:
        return False


def member_level(bands: List[LevelBand], amount: int, tenure: Optional[int]) -> int:
    """Highest band the holder qualifies for by amount AND chronos-verified tenure."""
    lvl = 1
    for b in sorted(bands, key=lambda x: x.level):
        tenure_ok = (b.min_tenure_sec == 0) if tenure is None else (tenure >= b.min_tenure_sec)
        if amount >= b.min_amount and tenure_ok:
            lvl = max(lvl, b.level)
    return lvl


# ── on-chain reads (web3.py AsyncWeb3) ──────────────────────────────────────
_ERC20_721_ABI = [{
    "name": "balanceOf", "type": "function", "stateMutability": "view",
    "inputs": [{"name": "owner", "type": "address"}],
    "outputs": [{"name": "", "type": "uint256"}],
}]
_ERC1155_ABI = [{
    "name": "balanceOf", "type": "function", "stateMutability": "view",
    "inputs": [{"name": "owner", "type": "address"}, {"name": "id", "type": "uint256"}],
    "outputs": [{"name": "", "type": "uint256"}],
}]
# Transfer(address,address,uint256) — topic0 identical for ERC-20/721
_TRANSFER_TOPIC0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


async def read_holding(h: HoldingConfig, owner: str) -> int:
    """balanceOf(owner). Returns 0 on any failure."""
    try:
        from web3 import AsyncWeb3
        w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(h.rpc))
        token = to_checksum_address(h.token)
        owner_cs = to_checksum_address(owner)
        if h.standard == "erc1155":
            c = w3.eth.contract(address=token, abi=_ERC1155_ABI)
            return int(await c.functions.balanceOf(owner_cs, h.token_id).call())
        c = w3.eth.contract(address=token, abi=_ERC20_721_ABI)
        return int(await c.functions.balanceOf(owner_cs).call())
    except Exception as e:
        logger.debug("read_holding failed: %s", e)
        return 0


async def acquisition_timestamp(h: HoldingConfig, owner: str) -> Optional[int]:
    """Block timestamp (unix s) of the earliest inbound Transfer to `owner` — the
    holding's blockchain timestamp / tenure root. None when unknown (RPC log
    limits, never received). Scans from h.from_block (set this to the deploy
    block to avoid 0→latest range rejections)."""
    try:
        from web3 import AsyncWeb3
        w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(h.rpc))
        owner_topic = "0x" + to_checksum_address(owner)[2:].lower().rjust(64, "0")
        # to is the 3rd topic for both ERC-20 and ERC-721 Transfer.
        logs = await w3.eth.get_logs({
            "address": to_checksum_address(h.token),
            "fromBlock": int(h.from_block),
            "toBlock": "latest",
            "topics": [_TRANSFER_TOPIC0, None, owner_topic],
        })
        if not logs:
            return None
        earliest = min(logs, key=lambda l: int(l["blockNumber"]))
        block = await w3.eth.get_block(int(earliest["blockNumber"]))
        return int(block["timestamp"])
    except Exception as e:
        logger.debug("acquisition_timestamp failed: %s", e)
        return None


# Injectable hooks for tests (default to the real web3 reads).
HoldingReader = Callable[[HoldingConfig, str], Awaitable[int]]
AcqReader = Callable[[HoldingConfig, str], Awaitable[Optional[int]]]


def _mk(role: str, level: int, address: str, reason: str,
        now_unix: Optional[int], chronos: Optional[Dict[str, Any]],
        holding: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "role": role,
        "level": level,
        "privileged": role != "public",
        "address": address,
        "reason": reason,
        "as_of_unix": now_unix,
        "chronos": chronos or {"consensus": "offline", "promised_by": "local"},
        "holding": holding,
    }


async def resolve_privilege(
    address: str,
    message: str,
    signature: str,
    cfg: OverlordConfig,
    *,
    now_unix: Optional[int] = None,
    chronos: Optional[Dict[str, Any]] = None,
    read_holding_fn: Optional[HoldingReader] = None,
    acq_fn: Optional[AcqReader] = None,
) -> Dict[str, Any]:
    """Resolve {role, level, privileged} from (address, signature, holdings,
    tenure, chronos). Identity is proven by ECDSA recovery; the address-set match
    yields overlord/overseer; otherwise the chronos-verified holding yields
    member+level, or public when no qualifying holding."""
    from mindx_backend_service.bankon_vault.shadow_overlord import recover_signer

    # 1. Identity — the signature must recover to the claimed address.
    try:
        recovered = recover_signer(message, signature)
    except Exception:
        return _mk("public", 0, address, "signature did not prove identity", now_unix, chronos)
    if not _addr_eq(recovered, address):
        return _mk("public", 0, address, "signature did not prove identity", now_unix, chronos)
    addr = to_checksum_address(address)

    # 2. Admin axis — signature-proven address match.
    if cfg.overlord and _addr_eq(addr, cfg.overlord):
        return _mk("overlord", 1, addr, "overlord address (signature-proven)", now_unix, chronos)
    if any(_addr_eq(addr, o) for o in cfg.overseers):
        return _mk("overseer", 1, addr, "overseer address (signature-proven)", now_unix, chronos)

    # 3. Member axis — privilege from holdings + chronos-verified tenure.
    if not cfg.holding:
        return _mk("public", 0, addr, "no holding config", now_unix, chronos)
    reader = read_holding_fn or read_holding
    amount = await reader(cfg.holding, addr)
    if amount < cfg.holding.threshold:
        return _mk("public", 0, addr, "no qualifying holding", now_unix, chronos,
                   {"amount": str(amount), "acquired_at": None, "tenure_sec": None})
    acq_reader = acq_fn or acquisition_timestamp
    acquired_at = await acq_reader(cfg.holding, addr)
    tenure = None if (acquired_at is None or now_unix is None) else max(0, now_unix - acquired_at)
    level = member_level(list(cfg.holding.level_bands), amount, tenure)
    return _mk("member", level, addr, "qualifying holding (chronos-verified tenure)", now_unix, chronos,
               {"amount": str(amount), "acquired_at": acquired_at, "tenure_sec": tenure})
