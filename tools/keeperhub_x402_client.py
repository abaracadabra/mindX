"""
KeeperHubX402Client — consume KeeperHub paid workflows from Python.

KeeperHub doesn't ship a Python SDK; their `@keeperhub/wallet` is TS-only.
This client implements the minimum we need:

1. Hit a paid endpoint, receive a 402 with x402+MPP challenges.
2. Pick the x402 (Base USDC) leg (we hold Base USDC in BANKON Vault).
3. Sign an EIP-3009 `transferWithAuthorization` for USDC.
4. Resubmit with `X-PAYMENT` header carrying the signed authorization.
5. Return the response body + receipt.

Modeled on the on-chain semantics of x402.org/x402-whitepaper.pdf and
mirrors the structure of `tools/pay2play_metered_tool.py` so mindX
agents can swap between AgenticPlace and KeeperHub-routed payments.

Lets a mindX BDI agent *consume* paid workflows published by other
hackathon teams via KeeperHub — closing the bidirectional bridge.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import secrets
import time
from typing import Any, Dict, Optional

import httpx

from utils.logging_config import get_logger

logger = get_logger(__name__)


# EIP-712 domain templates per known network (USDC contract specifics).
_EIP3009_DOMAINS = {
    "base":  {"name": "USD Coin",   "version": "2",  "chainId": 8453},
    # Tempo USDC.e — operator must confirm exact name/version before mainnet use.
    "tempo": {"name": "USDC.e",     "version": "1",  "chainId": 4217},
}


class KeeperHubX402Error(RuntimeError):
    pass


class KeeperHubX402Client:
    """Consume KeeperHub paid workflows by paying their HTTP 402 challenges."""

    def __init__(
        self,
        buyer_private_key: Optional[str] = None,
        preferred_network: str = "base",
        kh_org_key: Optional[str] = None,
        timeout_s: float = 60.0,
    ):
        self.buyer_private_key = buyer_private_key or os.environ.get("KH_BUYER_PRIVATE_KEY") or os.environ.get("BUYER_PRIVATE_KEY")
        self.preferred_network = preferred_network
        self.kh_org_key = kh_org_key or os.environ.get("KEEPERHUB_ORG_KEY")
        self.timeout_s = timeout_s

        if not self.buyer_private_key:
            logger.warning(
                "KH x402 client: no buyer key set (KH_BUYER_PRIVATE_KEY) — "
                "calls will fail at the signing step."
            )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def fetch(
        self,
        method: str,
        url: str,
        json_body: Optional[Dict[str, Any]] = None,
        max_pay_usdc: float = 0.10,
    ) -> Dict[str, Any]:
        """Hit `url`, pay if needed, return decoded JSON envelope.

        Failure modes:
          - upstream returns non-402 non-success → raises KeeperHubX402Error
          - selected x402 challenge exceeds max_pay_usdc → raises
          - signing fails → raises
        """
        async with httpx.AsyncClient(timeout=self.timeout_s, follow_redirects=False) as client:
            # Initial request — expect 402.
            resp = await client.request(method, url, json=json_body)

            if resp.status_code != 402:
                # Either free (200) or upstream error.
                resp.raise_for_status()
                return self._decode(resp)

            challenge = resp.json()
            picked = self._pick_challenge(challenge, max_pay_usdc=max_pay_usdc)
            payment_header = await asyncio.to_thread(self._sign_payment, picked)

            # Retry with X-PAYMENT header.
            resp2 = await client.request(
                method, url,
                json=json_body,
                headers={"X-PAYMENT": payment_header},
            )
            if resp2.status_code == 402:
                # Still wants money — challenge probably stale.
                raise KeeperHubX402Error(
                    f"Upstream still 402 after payment attempt: {resp2.text[:300]}"
                )
            resp2.raise_for_status()
            return {
                "ok": True,
                "selected_scheme": picked["scheme"],
                "selected_network": picked["network"],
                "amount_usdc_units": picked["maxAmountRequired"],
                "response": self._decode(resp2),
            }

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _decode(resp: httpx.Response) -> Any:
        ct = resp.headers.get("content-type", "")
        if "application/json" in ct:
            return resp.json()
        return resp.text

    def _pick_challenge(self, envelope: Dict[str, Any], max_pay_usdc: float) -> Dict[str, Any]:
        accepts = envelope.get("accepts") or envelope.get("paymentRequirements") or []
        if not accepts:
            raise KeeperHubX402Error(f"402 envelope had no accepts: {envelope}")

        # Prefer the configured network; fall back to the cheapest.
        preferred = [a for a in accepts if a.get("network") == self.preferred_network]
        candidates = preferred or accepts

        # Sort by amount asc (USDC base units).
        candidates = sorted(candidates, key=lambda a: int(a.get("maxAmountRequired", "0")))
        picked = candidates[0]

        usdc = int(picked.get("maxAmountRequired", "0")) / 1_000_000
        if usdc > max_pay_usdc:
            raise KeeperHubX402Error(
                f"Cheapest challenge ${usdc:.4f} exceeds budget ${max_pay_usdc:.4f}"
            )
        return picked

    def _sign_payment(self, accepted: Dict[str, Any]) -> str:
        """Return the X-PAYMENT header value: base64(JSON({scheme, network, payload}))."""
        if not self.buyer_private_key:
            raise KeeperHubX402Error("No buyer private key configured")

        try:
            from eth_account import Account
            from eth_account.messages import encode_typed_data
        except ImportError as e:
            raise KeeperHubX402Error("eth-account is required (pip install eth-account)") from e

        scheme  = accepted.get("scheme", "exact")
        network = accepted.get("network", "base")
        domain_template = _EIP3009_DOMAINS.get(network)
        if not domain_template:
            raise KeeperHubX402Error(f"Unknown network for signing: {network}")

        usdc_address  = accepted["asset"]
        recipient     = accepted["payTo"]
        amount        = int(accepted["maxAmountRequired"])
        valid_after   = 0
        valid_before  = int(time.time()) + 3600
        nonce_bytes   = bytes.fromhex(secrets.token_hex(32))

        acct = Account.from_key(self.buyer_private_key)
        from_address = acct.address

        domain = {
            "name": domain_template["name"],
            "version": domain_template["version"],
            "chainId": domain_template["chainId"],
            "verifyingContract": usdc_address,
        }
        types = {
            "TransferWithAuthorization": [
                {"name": "from",        "type": "address"},
                {"name": "to",          "type": "address"},
                {"name": "value",       "type": "uint256"},
                {"name": "validAfter",  "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce",       "type": "bytes32"},
            ],
        }
        message = {
            "from": from_address,
            "to": recipient,
            "value": amount,
            "validAfter": valid_after,
            "validBefore": valid_before,
            "nonce": nonce_bytes,
        }

        signable = encode_typed_data(
            domain_data=domain,
            message_types=types,
            message_data=message,
        )
        signed = acct.sign_message(signable)

        payload = {
            "from":        from_address,
            "to":          recipient,
            "value":       str(amount),
            "validAfter":  str(valid_after),
            "validBefore": str(valid_before),
            "nonce":       "0x" + nonce_bytes.hex(),
            "signature":   signed.signature.to_0x_hex(),
        }
        envelope = {
            "x402Version": 1,
            "scheme": scheme,
            "network": network,
            "payload": payload,
        }
        return base64.b64encode(json.dumps(envelope).encode()).decode()
