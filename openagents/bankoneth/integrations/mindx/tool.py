# SPDX-License-Identifier: Apache-2.0
"""mindX BaseTool wrapper around the @bankoneth/cli command.

Registers under tool_id `bankoneth_tool`. Lets mindX agents claim
their own bankon.eth subname, buy a .eth, or issue under a hosted parent.

Usage (mindX side):
    from openagents.bankoneth.integrations.mindx.tool import BankonethTool
    tool = BankonethTool(cli_path="/usr/local/bin/bankoneth")
    result = await tool.execute(action="claim", label="agent-01",
                                duration_years=1, payment="eth",
                                inft_mode_a=True, list_on_agenticplace=False)
    # → {"status": "ok", "tx_hash": "0x..."}
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

logger = logging.getLogger("bankoneth.integrations.mindx")


@dataclass(frozen=True)
class BankonethToolConfig:
    """Configurable knobs passed to the bankoneth CLI via env."""

    cli_path:     str               = "bankoneth"
    rpc_url:      Optional[str]     = None         # falls back to BANKONETH_RPC_URL
    chain:        Literal["mainnet", "sepolia"] = "mainnet"
    addresses_json: Optional[str]   = None         # falls back to BANKONETH_ADDRESSES_JSON
    pk_env:       str               = "BANKONETH_PK"  # env var to read the wallet key from
    timeout_s:    float             = 120.0


class BankonethTool:
    """mindX-side tool wrapping the bankoneth CLI."""

    tool_id     = "bankoneth_tool"
    description = (
        "Claim a bankon.eth subname, purchase a .eth 2LD, or issue a subname "
        "under a hosted .eth via bankoneth. Tri-rail payments (ETH / USDC permit "
        "/ x402-avm Algorand USDC). Optional ERC-7857 iNFT wrap + ERC-6551 TBA "
        "+ optional listing on agenticplace.pythai.net."
    )

    def __init__(self, config: Optional[BankonethToolConfig] = None):
        self.config = config or BankonethToolConfig()

    # ── mindX BaseTool surface ─────────────────────────────────────

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        action: str = kwargs.get("action", "")
        try:
            if action == "claim":
                return await self._claim(**kwargs)
            if action == "purchase":
                return await self._purchase(**kwargs)
            if action == "host_issue":
                return await self._host_issue(**kwargs)
            if action == "quote":
                return await self._quote(**kwargs)
            return {"status": "error", "error": f"unknown action: {action}"}
        except Exception as e:  # pragma: no cover — defensive
            logger.exception("BankonethTool action %r failed", action)
            return {"status": "error", "error": str(e)}

    def get_schema(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "description": self.description,
            "actions": {
                "claim": {
                    "label":              "str — subname to claim, without .bankon.eth",
                    "duration_years":     "int — registration duration",
                    "payment":            "'eth' | 'usdc-permit' | 'x402-avm'",
                    "inft_mode_a":        "bool — wrap as ERC-7857 iNFT on 0G",
                    "list_on_agenticplace": "bool — opt-in listing",
                },
                "purchase": {
                    "label":          "str — .eth 2LD to buy (without .eth)",
                    "duration_years": "int",
                    "payment":        "'eth' | 'x402-avm'",
                },
                "host_issue": {
                    "parent_domain": "str — parent .eth that's enrolled with bankoneth",
                    "label":         "str — subname to mint under it",
                    "payment":       "'eth' | 'x402-avm'",
                },
                "quote": {
                    "label":          "str — label to price",
                    "duration_years": "int",
                },
            },
        }

    # ── Action handlers ────────────────────────────────────────────

    async def _claim(self, **kwargs: Any) -> Dict[str, Any]:
        label    = kwargs["label"]
        duration = int(kwargs.get("duration_years", 1))
        payment  = kwargs.get("payment", "eth")
        inft     = bool(kwargs.get("inft_mode_a", True))
        listing  = bool(kwargs.get("list_on_agenticplace", False))

        argv = [self.config.cli_path, "claim", label,
                "--duration", str(duration), "--rail", payment]
        if inft:    argv.append("--inft")
        if listing: argv.append("--list")
        return await self._spawn(argv)

    async def _purchase(self, **kwargs: Any) -> Dict[str, Any]:
        label    = kwargs["label"]
        duration = int(kwargs.get("duration_years", 1))
        payment  = kwargs.get("payment", "eth")
        argv = [self.config.cli_path, "purchase", label,
                "--duration", str(duration), "--rail", payment]
        return await self._spawn(argv)

    async def _host_issue(self, **kwargs: Any) -> Dict[str, Any]:
        parent_domain = kwargs["parent_domain"]
        label         = kwargs["label"]
        payment       = kwargs.get("payment", "eth")
        argv = [self.config.cli_path, "host:issue", label, parent_domain,
                "--rail", payment]
        return await self._spawn(argv)

    async def _quote(self, **kwargs: Any) -> Dict[str, Any]:
        label    = kwargs["label"]
        duration = int(kwargs.get("duration_years", 1))
        argv = [self.config.cli_path, "quote", label, "--duration", str(duration)]
        return await self._spawn(argv)

    # ── Process plumbing ───────────────────────────────────────────

    async def _spawn(self, argv: list) -> Dict[str, Any]:
        env = dict(os.environ)
        if self.config.rpc_url:        env["BANKONETH_RPC_URL"] = self.config.rpc_url
        if self.config.addresses_json: env["BANKONETH_ADDRESSES_JSON"] = self.config.addresses_json
        env["BANKONETH_CHAIN"] = self.config.chain

        logger.info("spawn: %s", shlex.join(argv))
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=self.config.timeout_s)
        except asyncio.TimeoutError:
            proc.kill()
            return {"status": "error", "error": "bankoneth CLI timeout"}

        stdout = out.decode("utf-8", errors="replace").strip()
        stderr = err.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            return {"status": "error", "exit_code": proc.returncode,
                    "stdout": stdout, "stderr": stderr}

        # CLI prints "tx: 0x…" or "quote: …" on stdout. Try to parse JSON first;
        # fall back to a tx_hash regex.
        try:
            return {"status": "ok", "result": json.loads(stdout)}
        except (json.JSONDecodeError, ValueError):
            return {"status": "ok", "stdout": stdout, "stderr": stderr}
