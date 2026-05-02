"""
X402AvmClient — consume Algorand x402-AVM paid endpoints from Python.

Mirrors the structure of `tools/keeperhub_x402_client.py` 1:1 — same
challenge parser, same retry-after-402 loop, same budget gate — but the
signing primitive is an Algorand `AssetTransferTxn` (Ed25519 over USDC ASA)
instead of EIP-3009 typed-data. Pure Python via `py-algorand-sdk`; no Node
shell-out, so the BANKON Vault mnemonic stays inside the Python process.

Wire format (per the @x402-avm/core envelope, ISC, 2026-05-02):

    X-PAYMENT: base64(JSON({
        "x402Version": 1,
        "scheme":  "exact",
        "network": "algorand-testnet",
        "payload": {
            "txn": "<base64-msgpack-encoded AssetTransferTxn>",
            "sig": "<base64 Ed25519 signature>",
        },
    }))

The recipient address (`payTo` in the 402 challenge) must already be opted
into the USDC ASA on TestNet — opt-in is operator-side, not client-side.

Configuration via environment / vault keys (see `docs/X402.md`):
    algorand_mnemonic              — 25-word buyer wallet mnemonic
    algorand_recipient_address     — fallback if challenge omits payTo
    algorand_usdc_asa_id           — TestNet USDC ASA ID
    x402_avm_facilitator_url       — defaults to https://mindx.pythai.net:4022
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import Any, Dict, Optional

import httpx

from utils.logging_config import get_logger

logger = get_logger(__name__)


_DEFAULT_FACILITATOR = "https://mindx.pythai.net:4022"
_DEFAULT_NETWORK = "algorand-testnet"
_AVM_SCHEME = "exact"


class X402AvmError(RuntimeError):
    pass


class X402AvmClient:
    """Consume x402-AVM paid endpoints by signing AVM `AssetTransferTxn` payments."""

    def __init__(
        self,
        buyer_mnemonic: Optional[str] = None,
        recipient_address: Optional[str] = None,
        usdc_asa_id: Optional[int] = None,
        facilitator_url: Optional[str] = None,
        preferred_network: str = _DEFAULT_NETWORK,
        timeout_s: float = 60.0,
    ):
        self.buyer_mnemonic = (
            buyer_mnemonic
            or os.environ.get("algorand_mnemonic")
            or os.environ.get("ALGORAND_MNEMONIC")
        )
        self.recipient_address = (
            recipient_address
            or os.environ.get("algorand_recipient_address")
            or os.environ.get("ALGORAND_RECIPIENT_ADDRESS")
        )
        env_asa = os.environ.get("algorand_usdc_asa_id") or os.environ.get(
            "ALGORAND_USDC_ASA_ID"
        )
        self.usdc_asa_id = (
            int(usdc_asa_id) if usdc_asa_id is not None
            else (int(env_asa) if env_asa else None)
        )
        self.facilitator_url = (
            facilitator_url
            or os.environ.get("x402_avm_facilitator_url")
            or os.environ.get("X402_AVM_FACILITATOR_URL")
            or _DEFAULT_FACILITATOR
        )
        self.preferred_network = preferred_network
        self.timeout_s = timeout_s

        if not self.buyer_mnemonic:
            logger.warning(
                "x402-AVM client: no buyer mnemonic set (algorand_mnemonic) — "
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
          - upstream returns non-402 non-success → raises X402AvmError
          - selected challenge exceeds max_pay_usdc → raises
          - signing fails (missing mnemonic, missing asset id, etc.) → raises
        """
        async with httpx.AsyncClient(timeout=self.timeout_s, follow_redirects=False) as client:
            resp = await client.request(method, url, json=json_body)

            if resp.status_code != 402:
                resp.raise_for_status()
                return self._decode(resp)

            challenge = resp.json()
            picked = self._pick_challenge(challenge, max_pay_usdc=max_pay_usdc)
            payment_header = await asyncio.to_thread(self._sign_payment, picked)

            resp2 = await client.request(
                method, url,
                json=json_body,
                headers={"X-PAYMENT": payment_header},
            )
            if resp2.status_code == 402:
                raise X402AvmError(
                    f"Upstream still 402 after AVM payment attempt: {resp2.text[:300]}"
                )
            resp2.raise_for_status()
            return {
                "ok": True,
                "selected_scheme": picked.get("scheme", _AVM_SCHEME),
                "selected_network": picked.get("network", self.preferred_network),
                "amount_usdc_units": picked.get("maxAmountRequired"),
                "x_payment_response": resp2.headers.get("X-PAYMENT-RESPONSE"),
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
            raise X402AvmError(f"402 envelope had no accepts: {envelope}")

        # Filter to AVM rail; fall back to anything that looks AVM-shaped.
        avm = [
            a for a in accepts
            if a.get("network") == self.preferred_network
            or str(a.get("network", "")).startswith("algorand")
        ]
        if not avm:
            raise X402AvmError(
                f"No AVM-compatible rail in 402 envelope (got networks "
                f"{[a.get('network') for a in accepts]})"
            )

        candidates = sorted(avm, key=lambda a: int(a.get("maxAmountRequired", "0")))
        picked = candidates[0]

        usdc = int(picked.get("maxAmountRequired", "0")) / 1_000_000
        if usdc > max_pay_usdc:
            raise X402AvmError(
                f"Cheapest AVM challenge ${usdc:.4f} exceeds budget ${max_pay_usdc:.4f}"
            )
        return picked

    def _sign_payment(self, accepted: Dict[str, Any]) -> str:
        """Return the X-PAYMENT header value: base64(JSON({scheme, network, payload}))."""
        if not self.buyer_mnemonic:
            raise X402AvmError("No buyer mnemonic configured (algorand_mnemonic)")

        try:
            from algosdk import account, mnemonic, transaction, encoding  # type: ignore
        except ImportError as e:
            raise X402AvmError(
                "py-algorand-sdk is required (pip install py-algorand-sdk>=2.6.0)"
            ) from e

        scheme = accepted.get("scheme", _AVM_SCHEME)
        network = accepted.get("network", self.preferred_network)
        recipient = accepted.get("payTo") or self.recipient_address
        if not recipient:
            raise X402AvmError("AVM challenge had no payTo and no fallback recipient")

        amount = int(accepted.get("maxAmountRequired", "0"))
        if amount <= 0:
            raise X402AvmError("AVM challenge had non-positive maxAmountRequired")

        extra = accepted.get("extra") or {}
        asa_id_raw = extra.get("assetId") or accepted.get("asset") or self.usdc_asa_id
        try:
            asa_id = int(asa_id_raw)
        except (TypeError, ValueError) as e:
            raise X402AvmError(f"AVM challenge had unparsable asset id: {asa_id_raw!r}") from e

        sk = mnemonic.to_private_key(self.buyer_mnemonic)
        sender = account.address_from_private_key(sk)

        # Suggested params come from the facilitator's `/info` (or algod). We
        # use min-fee defaults and a short validity window; the facilitator
        # rejects stale/expired txns at submit time.
        sp = transaction.SuggestedParams(
            fee=1000,
            flat_fee=True,
            first=0,
            last=0,
            gh="",
            gen=None,
            min_fee=1000,
        )

        # Best-effort: pull live params from the facilitator. If unavailable,
        # leave the placeholder values above and let the facilitator's pre-sign
        # handler reject — the demo facilitator reconstructs sp on its side.
        try:
            sp = self._fetch_suggested_params() or sp
        except Exception as e:
            logger.debug(f"x402-AVM suggested-params lookup failed (non-fatal): {e}")

        txn = transaction.AssetTransferTxn(
            sender=sender,
            sp=sp,
            receiver=recipient,
            amt=amount,
            index=asa_id,
        )
        signed_txn = txn.sign(sk)

        # Encode the signed txn as base64-msgpack; signature is already inside
        # the SignedTransaction structure but x402-avm expects the split form
        # {txn, sig} so consumers can verify without reconstructing msgpack.
        # `encoding.msgpack_encode(txn)` returns a base64 string of msgpack bytes.
        txn_msgpack = encoding.msgpack_encode(txn)
        raw_sig = getattr(signed_txn, "signature", b"")
        if isinstance(raw_sig, str):
            # py-algorand-sdk returns hex on some versions, bytes on others.
            try:
                raw_sig = bytes.fromhex(raw_sig)
            except ValueError:
                raw_sig = raw_sig.encode()
        sig_b64 = base64.b64encode(raw_sig).decode()

        envelope = {
            "x402Version": 1,
            "scheme": scheme,
            "network": network,
            "payload": {
                "txn": txn_msgpack,
                "sig": sig_b64,
            },
        }
        return base64.b64encode(json.dumps(envelope).encode()).decode()

    def _fetch_suggested_params(self):
        """Pull live SuggestedParams from the facilitator's /info if exposed.

        The hosted GoPlausible facilitator returns algod-equivalent params on
        `/info`; the demo facilitator does not. Failure is non-fatal — the
        facilitator's pre-sign handler can fill in fresh params on its side.
        """
        try:
            from algosdk import transaction  # type: ignore
        except ImportError:
            return None
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.facilitator_url.rstrip('/')}/info")
                if resp.status_code != 200:
                    return None
                info = resp.json()
                node = info.get("suggestedParams") or info.get("algod")
                if not node:
                    return None
                return transaction.SuggestedParams(
                    fee=int(node.get("fee", 1000)),
                    flat_fee=bool(node.get("flat_fee", True)),
                    first=int(node.get("first", 0)),
                    last=int(node.get("last", 0)),
                    gh=node.get("genesis_hash") or node.get("gh", ""),
                    gen=node.get("genesis_id") or node.get("gen"),
                    min_fee=int(node.get("min_fee", 1000)),
                )
        except Exception:
            return None
