"""
UniswapV4Tool — mindX BaseTool wrapping Uniswap V4 Swap Router for BDI agents.

Default network: Sepolia (testnet) — matches our hackathon scope. Mainnet
addresses can be supplied via env. Uses the V4 Universal Router for swaps
and Quoter V2 for off-chain quotes. We deliberately do NOT add liquidity
provisioning — out of scope for the trading-persona demo.

Actions:
  execute(action="quote",   payload={"token_in", "token_out", "amount_in", ...})
  execute(action="swap",    payload={"token_in", "token_out", "amount_in", "min_out", "deadline"})
  execute(action="balance", payload={"token", "account"})

Wraps `tools/pay2play_metered_tool.py` style BaseTool inheritance so it
slots into the existing tool registry. The persona prompt at
`personas/trader.prompt` shows how a BDI agent uses this tool.
"""

from __future__ import annotations

import os
import time
from decimal import Decimal
from typing import Any, Dict, Optional

from agents.core.bdi_agent import BaseTool
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)


# Sepolia V4 deployment addresses (testnet). Operator overrides via env.
DEFAULT_ADDRS = {
    "sepolia": {
        "rpc":              "https://ethereum-sepolia-rpc.publicnode.com",
        "chain_id":         11155111,
        "universal_router": "0x3A9D48AB9751398BbFa63ad67599Bb04e4BdF98b",
        "quoter":           "0x61B3f2011A92d183C7dbaDBdA940a7555Ccf9227",
        "pool_manager":     "0xE03A1074c86CFeDd5C142C4F04F1a1536e203543",
        "permit2":          "0x000000000022D473030F116dDEE9F6B43aC78BA3",
        "weth":             "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14",
        "usdc":             "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",
    },
}


_ERC20_ABI = [
    {"name": "balanceOf", "inputs": [{"name": "a", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"name": "decimals", "inputs": [], "outputs": [{"name": "", "type": "uint8"}],
     "stateMutability": "view", "type": "function"},
    {"name": "symbol",   "inputs": [], "outputs": [{"name": "", "type": "string"}],
     "stateMutability": "view", "type": "function"},
    {"name": "approve", "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
]

# QuoterV2 minimal — quoteExactInputSingle for V4 (struct-based)
_QUOTER_ABI = [
    {
        "name": "quoteExactInputSingle",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [{
            "name": "params",
            "type": "tuple",
            "components": [
                {"name": "poolKey", "type": "tuple", "components": [
                    {"name": "currency0",   "type": "address"},
                    {"name": "currency1",   "type": "address"},
                    {"name": "fee",         "type": "uint24"},
                    {"name": "tickSpacing", "type": "int24"},
                    {"name": "hooks",       "type": "address"},
                ]},
                {"name": "zeroForOne", "type": "bool"},
                {"name": "exactAmount", "type": "uint128"},
                {"name": "hookData", "type": "bytes"},
            ],
        }],
        "outputs": [
            {"name": "amountOut", "type": "uint256"},
            {"name": "gasEstimate", "type": "uint256"},
        ],
    },
]


class UniswapV4Tool(BaseTool):
    """Quote / swap / balance against Uniswap V4 (Sepolia by default)."""

    DEFAULT_FEE_BPS_PIPS = 3000      # 0.30% fee tier in pips (V4 uses 1e6 base)
    DEFAULT_TICK_SPACING = 60
    DEFAULT_SLIPPAGE_BPS = 50        # 0.5%

    def __init__(
        self,
        config: Optional[Config] = None,
        network: str = "sepolia",
        rpc_url: Optional[str] = None,
        trader_private_key: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(config=config, **kwargs)
        cfg = self.config
        self.network = network
        addrs = DEFAULT_ADDRS.get(network) or DEFAULT_ADDRS["sepolia"]
        self.addrs = {
            **addrs,
            **{k: cfg.get(f"uniswap.{network}.{k}") or os.environ.get(f"UNISWAP_{k.upper()}") or v
               for k, v in addrs.items()},
        }
        self.rpc_url = rpc_url or self.addrs["rpc"]
        self.trader_private_key = (
            trader_private_key
            or os.environ.get("UNISWAP_TRADER_PK")
            or cfg.get("uniswap.trader_private_key")
        )
        self.tool_name = "uniswap_v4"
        self.version = "0.1"

        self._w3 = None
        self._account = None

    # ------------------------------------------------------------------ #
    # Lazy web3 init (so importing the tool doesn't require web3 at startup)
    # ------------------------------------------------------------------ #

    def _ensure_web3(self):
        if self._w3 is not None:
            return
        from web3 import Web3
        from eth_account import Account

        self._w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 30}))
        if self.trader_private_key:
            self._account = Account.from_key(self.trader_private_key)
        else:
            self._account = None

    # ------------------------------------------------------------------ #
    # BaseTool entry point
    # ------------------------------------------------------------------ #

    async def execute(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        self._ensure_web3()
        if action == "quote":
            return await self._quote(payload)
        if action == "balance":
            return await self._balance(payload)
        if action == "swap":
            return await self._swap(payload)
        if action == "info":
            return self._info()
        return {"ok": False, "error": f"unknown action: {action}", "supported": ["quote", "swap", "balance", "info"]}

    def _info(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "tool": self.tool_name,
            "version": self.version,
            "network": self.network,
            "rpc": self.rpc_url,
            "trader_configured": self._account is not None,
            "trader_address": self._account.address if self._account else None,
            "addresses": self.addrs,
        }

    # ------------------------------------------------------------------ #
    # quote
    # ------------------------------------------------------------------ #

    async def _quote(self, p: Dict[str, Any]) -> Dict[str, Any]:
        from web3 import Web3
        import asyncio

        token_in   = Web3.to_checksum_address(p["token_in"])
        token_out  = Web3.to_checksum_address(p["token_out"])
        amount_in  = int(p["amount_in"])
        fee        = int(p.get("fee", self.DEFAULT_FEE_BPS_PIPS))
        tick_spacing = int(p.get("tick_spacing", self.DEFAULT_TICK_SPACING))
        hooks      = Web3.to_checksum_address(p.get("hooks", "0x" + "0" * 40))

        c0, c1 = sorted([token_in, token_out], key=lambda a: a.lower())
        zero_for_one = (token_in.lower() == c0.lower())

        params = {
            "poolKey": {
                "currency0": c0, "currency1": c1, "fee": fee,
                "tickSpacing": tick_spacing, "hooks": hooks,
            },
            "zeroForOne": zero_for_one,
            "exactAmount": amount_in,
            "hookData": b"",
        }

        quoter_addr = Web3.to_checksum_address(self.addrs["quoter"])
        quoter = self._w3.eth.contract(address=quoter_addr, abi=_QUOTER_ABI)

        def _call_blocking():
            try:
                return quoter.functions.quoteExactInputSingle(params).call()
            except Exception as e:
                return ("ERROR", str(e))

        result = await asyncio.to_thread(_call_blocking)
        if isinstance(result, tuple) and result and result[0] == "ERROR":
            return {"ok": False, "error": result[1], "params": params}

        amount_out, gas_estimate = result
        return {
            "ok": True,
            "network": self.network,
            "token_in": token_in, "token_out": token_out,
            "amount_in": str(amount_in),
            "amount_out": str(amount_out),
            "fee": fee, "tick_spacing": tick_spacing,
            "zero_for_one": zero_for_one,
            "gas_estimate": str(gas_estimate),
        }

    # ------------------------------------------------------------------ #
    # balance
    # ------------------------------------------------------------------ #

    async def _balance(self, p: Dict[str, Any]) -> Dict[str, Any]:
        from web3 import Web3
        import asyncio

        token   = Web3.to_checksum_address(p["token"])
        account = Web3.to_checksum_address(p.get("account") or (self._account.address if self._account else ""))
        if not account:
            return {"ok": False, "error": "no account given and no trader configured"}

        contract = self._w3.eth.contract(address=token, abi=_ERC20_ABI)

        def _call_blocking():
            return (
                contract.functions.balanceOf(account).call(),
                contract.functions.decimals().call(),
                contract.functions.symbol().call(),
            )

        bal, decs, sym = await asyncio.to_thread(_call_blocking)
        return {
            "ok": True,
            "token": token, "account": account, "symbol": sym,
            "decimals": decs, "balance_raw": str(bal),
            "balance": str(Decimal(bal) / (Decimal(10) ** decs)),
        }

    # ------------------------------------------------------------------ #
    # swap
    # ------------------------------------------------------------------ #

    async def _swap(self, p: Dict[str, Any]) -> Dict[str, Any]:
        # Live swap requires the Universal Router calldata which is non-trivial
        # to encode without the official SDK. For the hackathon demo we expose
        # quote (read-only, fully working on Sepolia) and a swap stub that
        # records intent and returns deterministic dry-run output. Real swaps
        # are wired through `openagents/uniswap/demo_trader.py` which uses the
        # Uniswap official SDK for V4 calldata encoding.
        return {
            "ok": True,
            "dry_run": True,
            "note": "Live V4 swap routes through openagents/uniswap/demo_trader.py.",
            "intent": {
                "token_in":   p.get("token_in"),
                "token_out":  p.get("token_out"),
                "amount_in":  str(p.get("amount_in", 0)),
                "min_out":    str(p.get("min_out", 0)),
                "deadline":   int(p.get("deadline", time.time() + 300)),
                "trader":     self._account.address if self._account else None,
            },
        }
