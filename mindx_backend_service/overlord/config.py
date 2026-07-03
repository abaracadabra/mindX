# SPDX-License-Identifier: Apache-2.0
"""
overlord.config — env-driven configuration for the mindX overlord/overseer
access-control model. Mirror of openagents/overlord/src/model.ts (OverlordConfig
/ HoldingConfig / LevelBand). Keep in sync with the canonical TS module.

Nothing is hardcoded: the overlord address is the canonical SHADOW_OVERLORD_ADDRESS;
overseers, the qualifying holding, and the level bands are all per-deployment env.

The whole subsystem is gated by MINDX_OVERLORD_ENABLED=1 so it can ship dark and
cut over only once verified — the existing /admin/shadow/* gate is untouched.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class LevelBand:
    """Minimum holding amount AND chronos-verified tenure to reach `level`."""
    level: int
    min_amount: int          # raw token units (wei / token count)
    min_tenure_sec: int      # 0 = no tenure requirement
    label: str = ""


@dataclass(frozen=True)
class HoldingConfig:
    rpc: str
    token: str
    standard: str            # erc20 | erc721 | erc1155
    chain_id: int
    threshold: int           # the public/privileged boundary
    level_bands: Tuple[LevelBand, ...]
    from_block: int = 0      # token deploy block — keeps getLogs in range
    token_id: int = 0        # erc1155
    decimals: int = 18       # display only


@dataclass(frozen=True)
class OverlordConfig:
    overlord: str                       # SHADOW_OVERLORD_ADDRESS
    overseers: Tuple[str, ...]          # MINDX_OVERSEER_ADDRESSES
    holding: Optional[HoldingConfig]    # None ⇒ no member axis (admin-only model)
    domain: str


def is_enabled() -> bool:
    return os.environ.get("MINDX_OVERLORD_ENABLED", "0").strip() == "1"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def load_config() -> OverlordConfig:
    overlord = _env("SHADOW_OVERLORD_ADDRESS")
    overseers = tuple(
        a.strip() for a in _env("MINDX_OVERSEER_ADDRESSES").split(",") if a.strip()
    )

    holding: Optional[HoldingConfig] = None
    token = _env("MINDX_OVERLORD_HOLDING_TOKEN")
    if token:
        threshold = int(_env("MINDX_OVERLORD_HOLDING_THRESHOLD", "1") or "1")
        bands_raw = _env("MINDX_OVERLORD_LEVEL_BANDS", "")
        bands: List[LevelBand] = []
        if bands_raw:
            try:
                for b in json.loads(bands_raw):
                    bands.append(
                        LevelBand(
                            level=int(b["level"]),
                            min_amount=int(b.get("min_amount", b.get("minAmount", threshold))),
                            min_tenure_sec=int(b.get("min_tenure_sec", b.get("minTenureSec", 0))),
                            label=str(b.get("label", "")),
                        )
                    )
            except Exception:
                bands = []
        if not bands:
            bands = [LevelBand(level=1, min_amount=threshold, min_tenure_sec=0)]
        holding = HoldingConfig(
            rpc=_env("MINDX_OVERLORD_HOLDING_RPC"),
            token=token,
            standard=_env("MINDX_OVERLORD_HOLDING_STANDARD", "erc20") or "erc20",
            chain_id=int(_env("MINDX_OVERLORD_HOLDING_CHAIN_ID", "1") or "1"),
            threshold=threshold,
            level_bands=tuple(bands),
            from_block=int(_env("MINDX_OVERLORD_HOLDING_FROM_BLOCK", "0") or "0"),
            token_id=int(_env("MINDX_OVERLORD_HOLDING_TOKEN_ID", "0") or "0"),
            decimals=int(_env("MINDX_OVERLORD_HOLDING_DECIMALS", "18") or "18"),
        )

    return OverlordConfig(
        overlord=overlord,
        overseers=overseers,
        holding=holding,
        domain=_env("MINDX_DOMAIN", "mindx.pythai.net") or "mindx.pythai.net",
    )
