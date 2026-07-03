"""
X402AvmClient — consume Algorand x402-AVM paid endpoints from Python.

Mirrors the structure of `tools/keeperhub_x402_client.py` 1:1 — same
challenge parser, same retry-after-402 loop, same budget gate — but the
signing primitive is an Algorand `AssetTransferTxn` (Ed25519 over USDC ASA)
instead of EIP-3009 typed-data. Pure Python via `py-algorand-sdk`; no Node
shell-out, so the BANKON Vault mnemonic stays inside the Python process.

Wire format — x402 v2 GoPlausible "Parsec" exact AVM scheme (atomic group):

    PAYMENT-SIGNATURE: base64(JSON({
        "x402Version": 2,
        "scheme":  "exact",
        "network": "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=",  # CAIP-2
        "payload": {
            "paymentIndex": 1,
            "paymentGroup": [
                "<base64-msgpack unsigned facilitator pay txn (fee abstraction)>",
                "<base64-msgpack client-signed axfer (the USDC payment)>",
            ],
        },
    }))

Fee abstraction: index 0 is the facilitator's pay txn (pooled fee, signed by the
facilitator at settle); index 1 is the client-signed USDC axfer. The client holds
no ALGO. With no `extra.feePayer`, a single buyer-signed axfer is used
(paymentIndex 0). Servers also accept the v1 `X-PAYMENT` header for back-compat.

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


_DEFAULT_FACILITATOR = "https://facilitator.goplausible.xyz"  # GoPlausible AVM facilitator
_DEFAULT_NETWORK = "algorand-testnet"
_AVM_SCHEME = "exact"

# CAIP-2 genesis-hash suffix per network — the base64 segment after "algorand:"
# IS the chain genesis hash, so we can build valid SuggestedParams offline.
_GENESIS = {
    "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=": ("mainnet-v1.0", "wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8="),
    "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=": ("testnet-v1.0", "SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI="),
}
# USDC ASA per network (6 decimals).
_USDC_ASA = {
    "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=": 31566704,  # mainnet
    "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=": 10458941,  # testnet
}


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
            or self._vault_mnemonic()
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

            # x402 v2: send PAYMENT-SIGNATURE (servers also accept v1 X-PAYMENT).
            resp2 = await client.request(
                method, url,
                json=json_body,
                headers={"PAYMENT-SIGNATURE": payment_header},
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
                "amount_usdc_units": picked.get("amount") or picked.get("maxAmountRequired"),
                "x_payment_response": resp2.headers.get("PAYMENT-RESPONSE") or resp2.headers.get("X-PAYMENT-RESPONSE"),
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

        def _amt(a):
            return int(a.get("amount") or a.get("maxAmountRequired") or "0")
        candidates = sorted(avm, key=_amt)
        picked = candidates[0]

        usdc = _amt(picked) / 1_000_000
        if usdc > max_pay_usdc:
            raise X402AvmError(
                f"Cheapest AVM challenge ${usdc:.4f} exceeds budget ${max_pay_usdc:.4f}"
            )
        return picked

    @staticmethod
    def _vault_mnemonic() -> Optional[str]:
        """Best-effort BANKON vault deposit (vault-as-oracle); never hard-imports."""
        try:  # pragma: no cover - depends on deployment vault wiring
            from mindx_backend_service.bankon_vault import get_credential
            return get_credential("algorand_mnemonic")
        except Exception:
            return None

    def _sign_payment(self, accepted: Dict[str, Any]) -> str:
        """Build + sign the Parsec `exact` AVM payment and return the v2 header value.

        Implements the GoPlausible atomic-group scheme (reference §3): when the
        challenge names a fee payer (``extra.feePayer``), the payment is a 2-txn
        atomic group — index 0 an UNSIGNED facilitator ``pay`` (pooled fee, note
        ``x402-fee-payer``; the facilitator signs it at settle) and index 1 the
        client-signed ``axfer`` (note ``x402-payment-v2``); ``paymentIndex=1``,
        and the client holds no ALGO for fees. With no fee payer it falls back to
        a single buyer-signed ``axfer`` at ``paymentIndex=0``.

        Wire (x402 v2): base64(JSON({x402Version:2, scheme, network,
        payload:{paymentIndex, paymentGroup:[base64-msgpack, ...]}})).
        """
        if not self.buyer_mnemonic:
            raise X402AvmError("No buyer mnemonic configured (algorand_mnemonic / vault)")

        try:
            from algosdk import account, mnemonic, transaction, encoding  # type: ignore
        except ImportError as e:
            raise X402AvmError(
                "py-algorand-sdk is required (pip install py-algorand-sdk>=2.6.0)"
            ) from e

        scheme = accepted.get("scheme", _AVM_SCHEME)
        # Normalize to CAIP-2 so genesis/ASA lookups and the server agree.
        try:
            from mindx_backend_service.x402_protocol import to_caip2
            network = to_caip2(str(accepted.get("network", self.preferred_network)))
        except Exception:
            network = str(accepted.get("network", self.preferred_network))

        recipient = accepted.get("payTo") or self.recipient_address
        if not recipient:
            raise X402AvmError("AVM challenge had no payTo and no fallback recipient")
        amount = int(accepted.get("amount") or accepted.get("maxAmountRequired", "0"))
        if amount <= 0:
            raise X402AvmError("AVM challenge had non-positive amount")

        extra = accepted.get("extra") or {}
        asa_id_raw = extra.get("assetId") or accepted.get("asset") or self.usdc_asa_id or _USDC_ASA.get(network)
        try:
            asa_id = int(asa_id_raw)
        except (TypeError, ValueError) as e:
            raise X402AvmError(f"AVM challenge had unparsable asset id: {asa_id_raw!r}") from e
        fee_payer = extra.get("feePayer")

        sk = mnemonic.to_private_key(self.buyer_mnemonic)
        sender = account.address_from_private_key(sk)

        sp = self._suggested_params(network, transaction)

        if fee_payer:
            # Fee abstraction: facilitator pays the pooled fee (covers both txns).
            fee_sp = transaction.SuggestedParams(
                fee=2 * (sp.min_fee or 1000), flat_fee=True, first=sp.first, last=sp.last,
                gh=sp.gh, gen=sp.gen, min_fee=sp.min_fee,
            )
            zero_sp = transaction.SuggestedParams(
                fee=0, flat_fee=True, first=sp.first, last=sp.last, gh=sp.gh, gen=sp.gen, min_fee=sp.min_fee,
            )
            pay = transaction.PaymentTxn(
                sender=fee_payer, sp=fee_sp, receiver=fee_payer, amt=0, note=b"x402-fee-payer",
            )
            axfer = transaction.AssetTransferTxn(
                sender=sender, sp=zero_sp, receiver=recipient, amt=amount, index=asa_id, note=b"x402-payment-v2",
            )
            transaction.assign_group_id([pay, axfer])
            signed_axfer = axfer.sign(sk)
            group = [encoding.msgpack_encode(pay), encoding.msgpack_encode(signed_axfer)]
            payment_index = 1
        else:
            axfer = transaction.AssetTransferTxn(
                sender=sender, sp=sp, receiver=recipient, amt=amount, index=asa_id, note=b"x402-payment-v2",
            )
            transaction.assign_group_id([axfer])
            signed_axfer = axfer.sign(sk)
            group = [encoding.msgpack_encode(signed_axfer)]
            payment_index = 0

        envelope = {
            "x402Version": 2,
            "scheme": scheme,
            "network": network,
            "payload": {"paymentIndex": payment_index, "paymentGroup": group},
        }
        return base64.b64encode(json.dumps(envelope).encode()).decode()

    def _suggested_params(self, network: str, transaction) -> Any:
        """Live params from the facilitator `/info`, else genesis-hash-from-CAIP-2
        with placeholder rounds (the facilitator validates/refreshes at settle)."""
        try:
            live = self._fetch_suggested_params()
            if live:
                return live
        except Exception as e:
            logger.debug(f"x402-AVM suggested-params lookup failed (non-fatal): {e}")
        gen, gh_b64 = _GENESIS.get(network, ("", ""))
        return transaction.SuggestedParams(
            fee=1000, flat_fee=True, first=0, last=1000, gh=gh_b64, gen=gen, min_fee=1000,
        )

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
