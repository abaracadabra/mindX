"""Driver contract shared by the foundry (EVM) and algorand (AVM) backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PreflightCheck:
    name: str          # rpc | compiled | balance | gas-budget | network-flag
    passed: bool
    detail: str = ""


@dataclass
class DeployResult:
    ok: bool
    record: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    logs: str = ""


class DeployDriver:
    """Abstract deploy driver. Subclasses implement preflight + deploy."""

    name = "base"

    async def preflight(self, stage, key) -> List[PreflightCheck]:  # noqa: ANN001
        raise NotImplementedError

    async def estimate(self, stage, key) -> Dict[str, Any]:  # noqa: ANN001
        return {"native": None, "usd": None}

    async def deploy(self, stage, key, *, project: str, deployer_of_record: str) -> DeployResult:  # noqa: ANN001
        raise NotImplementedError


def get_driver(driver_name: str) -> DeployDriver:
    if driver_name == "foundry":
        from .foundry_driver import FoundryDriver

        return FoundryDriver()
    if driver_name == "algorand":
        from .algorand_driver import AlgorandDriver

        return AlgorandDriver()
    raise ValueError(f"unknown driver '{driver_name}'")
