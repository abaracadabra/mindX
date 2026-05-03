"""SpinTradeTool — standalone Python wrapper around the SPINTRADE pair contract.

Action surface (any BDI trader can adopt this verbatim):
    execute("info")    → reserves + addresses
    execute("balance") → caller's BANKON / PYTHAI / LP balances
    execute("quote")   → off-chain price calc via SpinTradePair.quote()
    execute("swap")    → REAL on-chain swap via SpinTradePair.swap()

Every action here is fully wired — including swap, which actually broadcasts
and updates reserves. No dry-run stubs.

This module has zero dependencies on any caller (mindX, openagents, etc).
Required: web3, eth_account. SPINTRADE is framework-agnostic.

Usage:

    from spintrade_tool import SpinTradeTool
    tool = SpinTradeTool.from_deployments_json("spintrade/deployments/anvil.json")
    info  = await tool.execute("info")
    quote = await tool.execute("quote", {"token_in": "BANKON", "amount_in": 100 * 10**18})
    swap  = await tool.execute("swap",  {"token_in": "BANKON", "amount_in": 100 * 10**18, "min_out": 0})
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from web3 import Web3
from eth_account import Account


_PAIR_ABI = [
    {"type": "function", "name": "token0",  "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
    {"type": "function", "name": "token1",  "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
    {"type": "function", "name": "reserves","inputs": [], "outputs": [{"type": "uint256"},{"type":"uint256"},{"type":"uint32"}], "stateMutability": "view"},
    {"type": "function", "name": "quote",
     "inputs": [{"name":"amountIn","type":"uint256"},{"name":"tokenIn","type":"address"}],
     "outputs": [{"type":"uint256"}], "stateMutability": "view"},
    {"type": "function", "name": "swap",
     "inputs": [{"name":"amountIn","type":"uint256"},{"name":"tokenIn","type":"address"},
                {"name":"minAmountOut","type":"uint256"},{"name":"to","type":"address"}],
     "outputs": [{"type":"uint256"}], "stateMutability": "nonpayable"},
    {"type": "function", "name": "balanceOf",
     "inputs": [{"name":"a","type":"address"}], "outputs": [{"type":"uint256"}], "stateMutability": "view"},
]

_ERC20_ABI = [
    {"type":"function","name":"balanceOf","inputs":[{"name":"a","type":"address"}],"outputs":[{"type":"uint256"}],"stateMutability":"view"},
    {"type":"function","name":"approve",  "inputs":[{"name":"s","type":"address"},{"name":"v","type":"uint256"}],"outputs":[{"type":"bool"}],"stateMutability":"nonpayable"},
    {"type":"function","name":"allowance","inputs":[{"name":"o","type":"address"},{"name":"s","type":"address"}],"outputs":[{"type":"uint256"}],"stateMutability":"view"},
    {"type":"function","name":"symbol",   "inputs":[],"outputs":[{"type":"string"}],"stateMutability":"view"},
    {"type":"function","name":"decimals", "inputs":[],"outputs":[{"type":"uint8"}],"stateMutability":"view"},
]


@dataclass
class SpinTradeAddresses:
    bankon: str
    pythai: str
    factory: str
    pair: str
    rpc: str
    chain_id: int


class SpinTradeTool:
    """Real SPINTRADE pair interaction — quote + swap actually hit the chain."""

    def __init__(self, addrs: SpinTradeAddresses, trader_pk: Optional[str] = None):
        self.w3 = Web3(Web3.HTTPProvider(addrs.rpc))
        if not self.w3.is_connected():
            raise RuntimeError(f"cannot reach RPC at {addrs.rpc}")
        self.addrs = addrs
        self.account = Account.from_key(trader_pk) if trader_pk else None
        self.pair = self.w3.eth.contract(address=Web3.to_checksum_address(addrs.pair), abi=_PAIR_ABI)
        self.bankon = self.w3.eth.contract(address=Web3.to_checksum_address(addrs.bankon), abi=_ERC20_ABI)
        self.pythai = self.w3.eth.contract(address=Web3.to_checksum_address(addrs.pythai), abi=_ERC20_ABI)

    @classmethod
    def from_deployments_json(cls, path: str | Path, trader_pk: Optional[str] = None) -> "SpinTradeTool":
        data = json.loads(Path(path).read_text())
        c = data["contracts"]
        # If trader_pk not provided, fall back to the deployer key written by start.sh
        # (anvil-only — never pulls a key in production).
        pk = trader_pk or data.get("deployer_pk")
        addrs = SpinTradeAddresses(
            bankon=c["BankonToken"],
            pythai=c["PythaiToken"],
            factory=c["SpinTradeFactory"],
            pair=c["BankonPythaiPair"],
            rpc=data["rpc"],
            chain_id=int(data["chain_id"]),
        )
        return cls(addrs, trader_pk=pk)

    def _resolve_token_addr(self, name_or_addr: str) -> str:
        s = name_or_addr.lower()
        if s in ("bankon", "bnk"): return self.addrs.bankon
        if s in ("pythai", "pyt"): return self.addrs.pythai
        return Web3.to_checksum_address(name_or_addr)

    def _token_contract(self, addr: str):
        return self.bankon if addr.lower() == self.addrs.bankon.lower() else self.pythai

    async def execute(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        if action == "info":     return self._info()
        if action == "balance":  return self._balance(payload)
        if action == "quote":    return self._quote(payload)
        if action == "swap":     return self._swap(payload)
        return {"ok": False, "error": f"unknown action: {action}",
                "supported": ["info", "balance", "quote", "swap"]}

    # ─── reads ──────────────────────────────────────────────────────
    def _info(self) -> Dict[str, Any]:
        r0, r1, ts = self.pair.functions.reserves().call()
        t0 = self.pair.functions.token0().call()
        t1 = self.pair.functions.token1().call()
        # Map back to symbol order
        sym0 = "BANKON" if t0.lower() == self.addrs.bankon.lower() else "PYTHAI"
        sym1 = "BANKON" if t1.lower() == self.addrs.bankon.lower() else "PYTHAI"
        return {
            "ok": True,
            "chain_id": self.addrs.chain_id,
            "pair": self.addrs.pair,
            "token0": {"address": t0, "symbol": sym0, "reserve": str(r0)},
            "token1": {"address": t1, "symbol": sym1, "reserve": str(r1)},
            "last_update_ts": ts,
            "spot_price_t0_per_t1": (r0 / r1) if r1 else None,
            "spot_price_t1_per_t0": (r1 / r0) if r0 else None,
        }

    def _balance(self, p: Dict[str, Any]) -> Dict[str, Any]:
        addr = Web3.to_checksum_address(p.get("address") or (self.account.address if self.account else None) or "0x0")
        return {
            "ok": True,
            "address": addr,
            "bankon": str(self.bankon.functions.balanceOf(addr).call()),
            "pythai": str(self.pythai.functions.balanceOf(addr).call()),
            "lp":     str(self.pair.functions.balanceOf(addr).call()),
        }

    def _quote(self, p: Dict[str, Any]) -> Dict[str, Any]:
        token_in = self._resolve_token_addr(p["token_in"])
        amount_in = int(p["amount_in"])
        out = self.pair.functions.quote(amount_in, Web3.to_checksum_address(token_in)).call()
        return {
            "ok": True,
            "token_in": token_in, "amount_in": str(amount_in),
            "amount_out": str(out),
            "implied_rate": (out / amount_in) if amount_in else None,
        }

    # ─── writes ─────────────────────────────────────────────────────
    def _swap(self, p: Dict[str, Any]) -> Dict[str, Any]:
        if not self.account:
            return {"ok": False, "error": "no signer key configured"}
        token_in = self._resolve_token_addr(p["token_in"])
        amount_in = int(p["amount_in"])
        min_out = int(p.get("min_out", 0))
        to = Web3.to_checksum_address(p.get("to", self.account.address))

        # 1. ensure approval
        tok = self._token_contract(token_in)
        allowance = tok.functions.allowance(self.account.address, self.addrs.pair).call()
        if allowance < amount_in:
            ap_tx = tok.functions.approve(self.addrs.pair, 2**256 - 1).build_transaction({
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "chainId": self.addrs.chain_id,
            })
            signed = self.account.sign_transaction(ap_tx)
            self.w3.eth.wait_for_transaction_receipt(self.w3.eth.send_raw_transaction(signed.raw_transaction))

        # 2. swap
        tx = self.pair.functions.swap(amount_in, Web3.to_checksum_address(token_in), min_out, to).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "chainId": self.addrs.chain_id,
            "gas": 300_000,
        })
        signed = self.account.sign_transaction(tx)
        h = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        rcpt = self.w3.eth.wait_for_transaction_receipt(h, timeout=30)

        # parse Swap event amount_out from log data (web3.py-version-agnostic)
        # Swap signature: address indexed trader, address indexed tokenIn,
        #                 uint256 amountIn, uint256 amountOut, address indexed to
        # 3 indexed → topics[0..3] = [sig, trader, tokenIn, to]
        # data (non-indexed) = abi.encode(uint256 amountIn, uint256 amountOut) → 64 bytes
        amount_out = None
        for lg in rcpt.logs:
            if lg.address.lower() != self.addrs.pair.lower():
                continue
            data = lg.data
            if hasattr(data, "hex"):
                data = data.hex()
            if isinstance(data, str) and data.startswith("0x"):
                data = data[2:]
            if isinstance(data, str) and len(data) >= 128:
                # second uint256 = amountOut
                amount_out = str(int(data[64:128], 16))
                break

        return {
            "ok": rcpt.status == 1,
            "tx_hash": h.hex(),
            "block": rcpt.blockNumber,
            "gas_used": rcpt.gasUsed,
            "token_in": token_in,
            "amount_in": str(amount_in),
            "amount_out": amount_out,
            "to": to,
        }


# ─── CLI smoke harness ─────────────────────────────────────────────
def _cli():
    import argparse, asyncio, os
    p = argparse.ArgumentParser(description="SPINTRADE tool smoke test")
    p.add_argument("--deployments", default=str(Path(__file__).parent.parent / "deployments" / "anvil.json"))
    p.add_argument("--action", required=True, choices=["info", "balance", "quote", "swap"])
    p.add_argument("--token-in", default="BANKON")
    p.add_argument("--amount-in", type=str, default=str(10 * 10**18))
    p.add_argument("--min-out", type=str, default="0")
    p.add_argument("--pk", default=os.environ.get("TRADER_PK"))
    args = p.parse_args()

    tool = SpinTradeTool.from_deployments_json(args.deployments, trader_pk=args.pk)
    payload = {}
    if args.action in ("quote", "swap"):
        payload = {"token_in": args.token_in, "amount_in": int(args.amount_in)}
        if args.action == "swap":
            payload["min_out"] = int(args.min_out)
    out = asyncio.run(tool.execute(args.action, payload))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    _cli()
