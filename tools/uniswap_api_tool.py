"""UniswapAPITool — REAL Uniswap Trading API integration for openagents BDI trader.

This tool replaces the dry-run swap stub in tools/uniswap_v4_tool.py with a
production-grade integration against the official gateway at
https://trade-api.gateway.uniswap.org/v1/*.

Flow per swap:
    1. (ERC20-input only) GET /v1/check_approval → broadcast approve(Permit2, max)
       once per (token, swapper).
    2. POST /v1/quote → routing decision + price + permitData (EIP-712 typed data).
    3. Sign permitData via eth_account.encode_typed_data (ERC20 input only).
    4. POST /v1/swap with {quote, permitData, signature} → broadcast-ready calldata.
    5. Sign + send the EIP-1559 transaction via web3.

API key resolution order:
    1. constructor arg `api_key`
    2. UNISWAP_TRADE_API_KEY env var (Config-loaded from .env)
    3. BANKON Vault entry `uniswap_trade_api_key` (preferred — encrypted at rest)
    4. raises RuntimeError if all three are missing

Action surface (matches tools/uniswap_v4_tool.UniswapV4Tool):
    execute("info")    → API base + connected RPC + swapper address
    execute("balance") → swapper's balance of (token_in, token_out, native)
    execute("quote")   → /v1/quote response unwrapped
    execute("swap")    → real broadcast; returns {tx_hash, block, gas_used, amount_out}
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import aiohttp
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

logger = logging.getLogger(__name__)

API_BASE = "https://trade-api.gateway.uniswap.org/v1"
PERMIT2_ADDR = "0x000000000022D473030F116dDEE9F6B43aC78BA3"
NATIVE_ETH = "0x0000000000000000000000000000000000000000"


def _resolve_api_key(explicit: Optional[str] = None) -> str:
    """Resolve API key: arg → env → vault → raise."""
    if explicit:
        return explicit
    env_key = os.environ.get("UNISWAP_TRADE_API_KEY")
    if env_key:
        return env_key
    # Vault fallback — load_from_vault() injects keys into os.environ.
    try:
        from mindx_backend_service.bankon_vault.credential_provider import (
            CredentialProvider,
        )
        CredentialProvider().load_from_vault()
        env_key = os.environ.get("UNISWAP_TRADE_API_KEY")
        if env_key:
            return env_key
    except Exception as e:  # pragma: no cover
        logger.debug("vault fallback unavailable: %s", e)
    raise RuntimeError(
        "Uniswap Trade API key not found. Set UNISWAP_TRADE_API_KEY env, "
        "or vault it: python3 manage_credentials.py store uniswap_trade_api_key '<KEY>'"
    )


@dataclass
class UniswapAPIConfig:
    chain_id: int = 1
    rpc_url: str = "https://eth.drpc.org"
    auto_slippage: str = "DEFAULT"           # DEFAULT | LOW | MEDIUM | HIGH
    routing_preference: str = "BEST_PRICE"   # BEST_PRICE | LOW_GAS | LOW_PRICE_IMPACT
    urgency: str = "urgent"                  # normal | fast | urgent
    permit_amount: str = "FULL"              # FULL | EXACT
    spread_optimization: str = "EXECUTION"
    universal_router_version: str = "2.0"


class UniswapAPITool:
    """Production Uniswap Trading API wrapper.

    Mirrors the action surface of `tools/uniswap_v4_tool.UniswapV4Tool` so
    `openagents/uniswap/demo_trader.py` can swap implementations via env var
    without changing the BDI loop.
    """

    tool_name = "uniswap_api"
    description = "Quote/swap against the official Uniswap Trading API gateway."

    def __init__(
        self,
        swapper_pk: Optional[str] = None,
        api_key: Optional[str] = None,
        config: Optional[UniswapAPIConfig] = None,
    ):
        self.api_key = _resolve_api_key(api_key)
        self.cfg = config or UniswapAPIConfig()
        self.w3 = Web3(Web3.HTTPProvider(self.cfg.rpc_url))
        if not self.w3.is_connected():
            raise RuntimeError(f"Cannot reach RPC at {self.cfg.rpc_url}")

        self.account: Optional[Account] = None
        if swapper_pk:
            self.account = Account.from_key(swapper_pk)

        self._headers_full = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "x-universal-router-version": self.cfg.universal_router_version,
        }
        self._headers_approval = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

    # ─── public action surface ──────────────────────────────────────────
    async def execute(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        if action == "info":     return self._info()
        if action == "balance":  return await self._balance(payload)
        if action == "quote":    return await self._quote(payload)
        if action == "approval": return await self._check_approval(payload)
        if action == "swap":     return await self._swap(payload)
        return {
            "ok": False,
            "error": f"unknown action: {action}",
            "supported": ["info", "balance", "quote", "approval", "swap"],
        }

    # ─── reads ─────────────────────────────────────────────────────────
    def _info(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "tool": self.tool_name,
            "api_base": API_BASE,
            "chain_id": self.cfg.chain_id,
            "rpc_url": self.cfg.rpc_url,
            "swapper": self.account.address if self.account else None,
            "config": {
                "auto_slippage": self.cfg.auto_slippage,
                "routing_preference": self.cfg.routing_preference,
                "urgency": self.cfg.urgency,
                "permit_amount": self.cfg.permit_amount,
            },
        }

    async def _balance(self, p: Dict[str, Any]) -> Dict[str, Any]:
        addr = Web3.to_checksum_address(p.get("address") or (self.account.address if self.account else "0x0"))
        out: Dict[str, Any] = {"ok": True, "address": addr, "native": str(self.w3.eth.get_balance(addr))}
        for tk in p.get("tokens", []):
            if tk.lower() == NATIVE_ETH.lower():
                continue
            erc20 = self.w3.eth.contract(
                address=Web3.to_checksum_address(tk),
                abi=[{"type": "function", "name": "balanceOf",
                      "inputs": [{"name": "a", "type": "address"}],
                      "outputs": [{"type": "uint256"}], "stateMutability": "view"}],
            )
            out[tk.lower()] = str(erc20.functions.balanceOf(addr).call())
        return out

    async def _quote(self, p: Dict[str, Any]) -> Dict[str, Any]:
        if not self.account and not p.get("swapper"):
            return {"ok": False, "error": "swapper required (provide swapper_pk or 'swapper' arg)"}
        body = {
            "type": p.get("type", "EXACT_INPUT"),
            "amount": str(p["amount_in"]) if "amount_in" in p else str(p["amount"]),
            "tokenIn":  Web3.to_checksum_address(p["token_in"])  if p["token_in"]  != NATIVE_ETH else NATIVE_ETH,
            "tokenOut": Web3.to_checksum_address(p["token_out"]) if p["token_out"] != NATIVE_ETH else NATIVE_ETH,
            "tokenInChainId":  str(p.get("chain_id_in",  self.cfg.chain_id)),
            "tokenOutChainId": str(p.get("chain_id_out", self.cfg.chain_id)),
            "swapper": Web3.to_checksum_address(p.get("swapper") or self.account.address),
            "autoSlippage": p.get("auto_slippage", self.cfg.auto_slippage),
            "routingPreference": p.get("routing_preference", self.cfg.routing_preference),
            "urgency": p.get("urgency", self.cfg.urgency),
            "permitAmount": p.get("permit_amount", self.cfg.permit_amount),
            "spreadOptimization": p.get("spread_optimization", self.cfg.spread_optimization),
            "generatePermitAsTransaction": p.get("generate_permit_as_transaction", False),
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{API_BASE}/quote", json=body, headers=self._headers_full) as r:
                data = await r.json()
                if r.status != 200:
                    return {"ok": False, "error": f"HTTP {r.status}", "detail": data}
        return {"ok": True, **data}

    async def _check_approval(self, p: Dict[str, Any]) -> Dict[str, Any]:
        if not self.account and not p.get("wallet_address"):
            return {"ok": False, "error": "wallet_address required"}
        body = {
            "walletAddress": Web3.to_checksum_address(p.get("wallet_address") or self.account.address),
            "token":  Web3.to_checksum_address(p["token"]),
            "amount": str(p["amount"]),
            "chainId": p.get("chain_id", self.cfg.chain_id),
            "urgency": p.get("urgency", self.cfg.urgency),
            "includeGasInfo": p.get("include_gas_info", True),
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{API_BASE}/check_approval", json=body,
                              headers=self._headers_approval) as r:
                data = await r.json()
                if r.status != 200:
                    return {"ok": False, "error": f"HTTP {r.status}", "detail": data}
        return {"ok": True, **data}

    # ─── writes ────────────────────────────────────────────────────────
    def _sign_permit(self, permit_data: Dict[str, Any]) -> str:
        """Sign Uniswap's EIP-712 permitData with the swapper's key."""
        if not self.account:
            raise RuntimeError("no swapper key configured")
        msg = encode_typed_data(
            domain_data=permit_data["domain"],
            message_types=permit_data["types"],
            message_data=permit_data["values"],
        )
        signed = self.account.sign_message(msg)
        sig = signed.signature.hex()
        return sig if sig.startswith("0x") else "0x" + sig

    async def _approve_if_needed(self, token: str, amount: int, chain_id: int) -> Optional[Dict[str, Any]]:
        """Check approval; if missing, sign + broadcast it. Returns receipt or None."""
        if not self.account:
            return None
        if token.lower() == NATIVE_ETH.lower():
            return None
        ap_resp = await self._check_approval({"token": token, "amount": amount, "chain_id": chain_id})
        if not ap_resp.get("ok"):
            return ap_resp
        approval = ap_resp.get("approval")
        if not approval:
            return None  # already approved
        # Optional cancel-then-approve dance (USDT-style)
        for tx_field in ("cancel", "approval"):
            tx = approval if tx_field == "approval" else ap_resp.get("cancel")
            if not tx:
                continue
            signed = self.account.sign_transaction({
                "to":    Web3.to_checksum_address(tx["to"]),
                "data":  tx["data"],
                "value": int(tx["value"], 16) if isinstance(tx["value"], str) else int(tx["value"]),
                "gas":   80_000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce":   self.w3.eth.get_transaction_count(self.account.address),
                "chainId": tx["chainId"],
            })
            h = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(h, timeout=60)
        return {"approved": True, "tx_to": approval["to"]}

    async def _swap(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """Real swap broadcast. Returns {ok, tx_hash, block, gas_used, amount_out}."""
        if not self.account:
            return {"ok": False, "error": "swap requires swapper_pk"}

        chain_id = int(p.get("chain_id", self.cfg.chain_id))
        token_in = p["token_in"]
        amount_in = int(p["amount_in"])

        # 1. Approve Permit2 once if needed (no-op for native ETH)
        approval = await self._approve_if_needed(token_in, amount_in, chain_id)
        if isinstance(approval, dict) and approval.get("ok") is False:
            return {"ok": False, "step": "approval", "detail": approval}

        # 2. Quote
        quote_resp = await self._quote(p)
        if not quote_resp.get("ok"):
            return {"ok": False, "step": "quote", "detail": quote_resp}

        # 3. Build swap request body. Sign permit if ERC20 input.
        body: Dict[str, Any] = {"quote": quote_resp["quote"]}
        if quote_resp.get("permitData"):
            body["permitData"] = quote_resp["permitData"]
            body["signature"]  = self._sign_permit(quote_resp["permitData"])

        async with aiohttp.ClientSession() as s:
            async with s.post(f"{API_BASE}/swap", json=body, headers=self._headers_full) as r:
                swap_data = await r.json()
                if r.status != 200:
                    return {"ok": False, "step": "swap_api", "detail": swap_data}

        # 4. Broadcast via web3
        tx = swap_data.get("swap") or swap_data
        unsigned = {
            "to":    Web3.to_checksum_address(tx["to"]),
            "data":  tx["data"],
            "value": int(tx["value"], 16) if isinstance(tx["value"], str) else int(tx["value"]),
            "gas":   int(tx["gasLimit"], 16) if isinstance(tx.get("gasLimit"), str) else int(tx.get("gasLimit", 350_000)),
            "maxFeePerGas":         int(tx["maxFeePerGas"], 16)         if isinstance(tx["maxFeePerGas"], str)         else int(tx["maxFeePerGas"]),
            "maxPriorityFeePerGas": int(tx["maxPriorityFeePerGas"], 16) if isinstance(tx["maxPriorityFeePerGas"], str) else int(tx["maxPriorityFeePerGas"]),
            "nonce":   self.w3.eth.get_transaction_count(self.account.address),
            "chainId": chain_id,
            "type":    2,
        }
        if p.get("dry_run"):
            return {
                "ok": True, "dry_run": True,
                "tx": unsigned,
                "quote_amount_out": quote_resp["quote"]["output"]["amount"],
                "request_id": swap_data.get("requestId"),
            }
        signed = self.account.sign_transaction(unsigned)
        h = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        rcpt = self.w3.eth.wait_for_transaction_receipt(h, timeout=120)

        return {
            "ok": rcpt.status == 1,
            "tx_hash": h.hex(),
            "block": rcpt.blockNumber,
            "gas_used": rcpt.gasUsed,
            "amount_out_quoted": quote_resp["quote"]["output"]["amount"],
            "amount_out_min": quote_resp["quote"]["aggregatedOutputs"][0]["minAmount"],
            "request_id": swap_data.get("requestId"),
        }


# ─── CLI smoke harness ─────────────────────────────────────────────────
def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="UniswapAPITool smoke test")
    parser.add_argument("--action", required=True, choices=["info", "quote", "approval", "swap"])
    parser.add_argument("--token-in",  default=NATIVE_ETH)
    parser.add_argument("--token-out", default="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
    parser.add_argument("--amount",    default=str(10**18), help="wei amount")
    parser.add_argument("--swapper",   default="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
    parser.add_argument("--chain-id",  type=int, default=1)
    parser.add_argument("--rpc",       default="https://eth.drpc.org")
    parser.add_argument("--pk",        default=os.environ.get("UNISWAP_SWAPPER_PK"))
    parser.add_argument("--dry-run",   action="store_true")
    args = parser.parse_args()

    cfg = UniswapAPIConfig(chain_id=args.chain_id, rpc_url=args.rpc)
    tool = UniswapAPITool(swapper_pk=args.pk, config=cfg)

    payload: Dict[str, Any] = {
        "token_in": args.token_in,
        "token_out": args.token_out,
        "amount_in": int(args.amount),
        "swapper": args.swapper,
        "chain_id": args.chain_id,
    }
    if args.action == "approval":
        payload = {"token": args.token_in, "amount": int(args.amount), "chain_id": args.chain_id}
        if args.pk is None:
            payload["wallet_address"] = args.swapper
    if args.dry_run:
        payload["dry_run"] = True

    out = asyncio.run(tool.execute(args.action, payload))
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    _cli()
