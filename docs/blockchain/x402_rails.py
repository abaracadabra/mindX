# Copyright 2026 BANKON. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""x402 payment rails — credential issuance as a service.

This is the backing implementation for ``x402rails.agent``. It turns the
signature-based ``x402_signer`` into a *service*: a holder of signing wallets
that issues **payment credentials** to other agents on demand, so a consuming
agent can settle an x402-gated request without ever holding the private key.

The unit of exchange is a :class:`PaymentCredential` — a signed, single-use
``X-PAYMENT`` authorization plus the settlement metadata describing it. The
service reads an HTTP ``402`` challenge (or is handed one), enforces a per-call
budget and a per-rail allowlist, signs an EIP-3009 ``transferWithAuthorization``
through the wallet for the named rail, and returns the credential. The wallet
key stays inside the service; what crosses the boundary is the signature.

A *rail* is a (network, wallet) settlement leg. The Base-USDC rail is built in
and live (via :func:`x402_signer.base_usdc_x402_signer`); additional rails —
e.g. an Algorand/Parsec leg via ``tools/x402_avm_client`` — register through
:meth:`X402RailsService.register_rail` without touching call sites, because a
consumer asks for "a credential for this challenge", not for a chain.

mindX is one consumer of this service, not its only home.
"""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

import httpx

from cmc_client import X402_BASE_URL, decode_payment_challenge
from x402_signer import (
    USDC_MINOR_UNITS,
    X402SignerError,
    base_usdc_x402_signer,
)

# A wallet signer maps a decoded challenge to an X-PAYMENT payload string.
wallet_signer = Callable[[Mapping[str, Any]], str]

DEFAULT_PAYMENT_HEADER: str = "X-PAYMENT"


class X402RailsError(RuntimeError):
    """Base error for the rails service."""


class X402BudgetExceeded(X402RailsError):
    """Raised when a challenge's amount exceeds the configured per-call ceiling."""


class X402RailUnavailable(X402RailsError):
    """Raised when no rail is registered for a challenge's network."""


@dataclass(slots=True)
class PaymentCredential:
    """A single-use, signed x402 payment authorization the service hands out.

    The consumer settles by attaching ``{header_name: header_value}`` to its
    retried request; everything else is metadata describing what was signed, so
    the credential is self-auditing.

    Attributes:
        header_name: HTTP header carrying the payload (``X-PAYMENT``).
        header_value: base64 ``{x402Version, scheme, network, payload}`` envelope.
        rail: Logical rail name that signed it (e.g. ``"base"``).
        network: x402 network id (e.g. ``"eip155:8453"``).
        asset: Token contract the authorization spends.
        amount_minor: Amount in the token's minor units.
        amount_usdc: Amount expressed in whole USDC for convenience.
        payer: Address that signed (the rail wallet).
        recipient: Payee named by the challenge (``payTo``).
        expires_at: UNIX second at which the authorization is no longer valid.
        nonce: 0x-hex authorization nonce (single-use guarantee).
        issued_at: UNIX second the credential was issued.
    """

    header_name: str
    header_value: str
    rail: str
    network: str
    asset: str
    amount_minor: int
    amount_usdc: float
    payer: str
    recipient: str
    expires_at: int
    nonce: str
    issued_at: int

    def as_headers(self) -> dict[str, str]:
        """Return the header mapping a consumer attaches to settle."""
        return {self.header_name: self.header_value}

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view (the wire form an agent receives)."""
        return asdict(self)


@dataclass(slots=True)
class _rail:
    """A registered settlement leg: a signer plus its budget ceiling."""

    name: str
    signer: wallet_signer
    max_amount_usdc: float | None


class X402RailsService:
    """Issues x402 payment credentials from signing wallets, as a service.

    The service holds the wallets and offers credentials; consumers hold no keys.
    The Base-USDC rail is registered by default and built lazily, so the service
    can be constructed (and its capabilities advertised) before a wallet key is
    configured — the key is only required at the first issuance on that rail.

    Args:
        max_amount_usdc: Default per-call ceiling in whole USDC applied to the
            built-in Base rail and used as the default for rails registered
            without their own ceiling.
        payment_header: Header name credentials carry. Defaults to ``X-PAYMENT``.
        logger: Optional ``callable(str)`` for audit lines; defaults to silent.
    """

    def __init__(
        self,
        *,
        max_amount_usdc: float | None = 0.05,
        payment_header: str = DEFAULT_PAYMENT_HEADER,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self._default_budget = max_amount_usdc
        self._payment_header = payment_header
        self._log = logger or (lambda _msg: None)
        self._rails: dict[str, _rail] = {}
        self._ledger: list[PaymentCredential] = []
        # Lazy factory for the built-in Base rail: a missing wallet key must not
        # fail construction, only issuance.
        self._lazy: dict[str, Callable[[], wallet_signer]] = {
            "base": lambda: base_usdc_x402_signer(max_amount_usdc=max_amount_usdc),
        }
        # Networks each rail name can settle.
        self._networks: dict[str, tuple[str, ...]] = {
            "base": ("base", "eip155:8453"),
        }

    # -- rail registration / advertisement ---------------------------------

    def register_rail(
        self,
        name: str,
        signer: wallet_signer,
        *,
        networks: tuple[str, ...],
        max_amount_usdc: float | None = None,
    ) -> None:
        """Register an additional settlement rail.

        Args:
            name: Logical rail name (e.g. ``"algorand"``).
            signer: A ``callable(challenge) -> X-PAYMENT payload`` for this leg.
            networks: x402 network ids this rail settles (challenge ``network``).
            max_amount_usdc: Per-call ceiling; falls back to the service default.
        """
        budget = self._default_budget if max_amount_usdc is None else max_amount_usdc
        self._rails[name] = _rail(name=name, signer=signer, max_amount_usdc=budget)
        self._networks[name] = networks
        self._lazy.pop(name, None)
        self._log(f"rail registered: {name} networks={networks} cap={budget}")

    def offered_rails(self) -> list[str]:
        """Return the rail names this service can settle on."""
        return sorted(set(self._rails) | set(self._lazy))

    def describe(self) -> dict[str, Any]:
        """Return an agent-card-style description of what the service offers."""
        return {
            "service": "x402.rails",
            "offers": "single-use x402 payment credentials signed on demand",
            "payment_header": self._payment_header,
            "rails": [
                {"name": name, "networks": list(self._networks.get(name, ()))}
                for name in self.offered_rails()
            ],
            "default_max_amount_usdc": self._default_budget,
            "issued_count": len(self._ledger),
        }

    # -- credential issuance -----------------------------------------------

    def issue_from_challenge(
        self, challenge: Mapping[str, Any], *, rail: str | None = None
    ) -> PaymentCredential:
        """Issue a signed payment credential for a decoded x402 ``challenge``.

        Args:
            challenge: A decoded ``payment-required`` document (the form
                :func:`cmc_client.decode_payment_challenge` returns).
            rail: Force a specific rail; by default the rail is chosen from the
                challenge's network.

        Raises:
            X402RailUnavailable: No rail settles the challenge's network.
            X402BudgetExceeded: The amount exceeds the rail's ceiling.
            X402RailsError: The challenge is malformed or signing failed.
        """
        term = self._first_term(challenge)
        network = str(term.get("network", ""))
        rail_name = rail or self._rail_for_network(network)
        leg = self._resolve_rail(rail_name)

        amount_minor = int(term.get("maxAmountRequired", term.get("amount", 0)))
        if amount_minor <= 0:
            raise X402RailsError("challenge named a non-positive amount")

        try:
            payload_b64 = leg.signer(challenge)
        except X402SignerError as exc:
            raise X402RailsError(f"signing failed on rail {rail_name}: {exc}") from exc
        if not payload_b64:
            # The signer declined — by convention, over its budget ceiling.
            amount_usdc = amount_minor / USDC_MINOR_UNITS
            raise X402BudgetExceeded(
                f"{amount_usdc:.6f} USDC exceeds the {rail_name} rail ceiling"
            )

        credential = self._credential_from_payload(rail_name, payload_b64, term)
        self._ledger.append(credential)
        self._log(
            f"credential issued: rail={rail_name} network={credential.network} "
            f"amount={credential.amount_usdc:.6f} USDC -> {credential.recipient}"
        )
        return credential

    def issue_for_url(
        self,
        url: str,
        params: Mapping[str, Any] | None = None,
        *,
        rail: str | None = None,
        http: httpx.Client | None = None,
    ) -> PaymentCredential:
        """Probe an x402-gated ``url`` for its challenge and issue a credential.

        Issues the credential but does **not** settle — the caller (or
        :meth:`settle`) attaches it and resends. Returns the credential ready to
        attach via :meth:`PaymentCredential.as_headers`.

        Raises:
            X402RailsError: The URL did not answer with a decodable 402 challenge.
        """
        owns = http is None
        client = http or httpx.Client(
            base_url=X402_BASE_URL, headers={"Accept": "application/json"}, timeout=30.0
        )
        try:
            response = client.get(url, params=dict(params or {}))
            if response.status_code != 402:
                raise X402RailsError(
                    f"{url} did not require payment (http {response.status_code})"
                )
            header = response.headers.get("payment-required", "")
            challenge = decode_payment_challenge(header)
        finally:
            if owns:
                client.close()
        return self.issue_from_challenge(challenge, rail=rail)

    def settle(
        self,
        url: str,
        params: Mapping[str, Any] | None = None,
        *,
        rail: str | None = None,
        http: httpx.Client | None = None,
    ) -> dict[str, Any]:
        """Issue a credential for ``url`` and complete the paid request.

        The full 402 → sign → resend cycle, end to end. Returns the decoded
        ``data`` body of the settled response.

        Raises:
            X402RailsError: On a non-2xx terminal response or an undecodable 402.
        """
        owns = http is None
        client = http or httpx.Client(
            base_url=X402_BASE_URL, headers={"Accept": "application/json"}, timeout=30.0
        )
        try:
            query = dict(params or {})
            first = client.get(url, params=query)
            if first.status_code != 402:
                return self._unwrap(first)
            challenge = decode_payment_challenge(
                first.headers.get("payment-required", "")
            )
            credential = self.issue_from_challenge(challenge, rail=rail)
            second = client.get(url, params=query, headers=credential.as_headers())
            return self._unwrap(second)
        finally:
            if owns:
                client.close()

    # -- ledger ------------------------------------------------------------

    @property
    def ledger(self) -> list[PaymentCredential]:
        """Return the audit trail of credentials issued this session."""
        return list(self._ledger)

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _first_term(challenge: Mapping[str, Any]) -> dict[str, Any]:
        accepts = (
            challenge.get("accepts") or challenge.get("paymentRequirements") or []
        )
        if not accepts or not isinstance(accepts[0], Mapping):
            raise X402RailsError("challenge carried no usable accepted terms")
        return dict(accepts[0])

    def _rail_for_network(self, network: str) -> str:
        for name, nets in self._networks.items():
            if network in nets:
                return name
        raise X402RailUnavailable(
            f"no rail registered for network {network!r}; "
            f"offered rails: {self.offered_rails()}"
        )

    def _resolve_rail(self, name: str) -> _rail:
        leg = self._rails.get(name)
        if leg is not None:
            return leg
        factory = self._lazy.get(name)
        if factory is None:
            raise X402RailUnavailable(f"unknown rail {name!r}")
        # Build the lazy rail (e.g. the Base wallet) on first use.
        leg = _rail(
            name=name, signer=factory(), max_amount_usdc=self._default_budget
        )
        self._rails[name] = leg
        return leg

    def _credential_from_payload(
        self, rail_name: str, payload_b64: str, term: Mapping[str, Any]
    ) -> PaymentCredential:
        """Decode the signed envelope into a full, auditable credential.

        Settlement facts (payer, recipient, amount, nonce, expiry, signature)
        come from the signed envelope; the ``asset`` is taken from the challenge
        ``term``, which names it (the envelope does not echo it).
        """
        try:
            envelope = json.loads(base64.b64decode(payload_b64))
            payload = envelope["payload"]
        except (ValueError, KeyError) as exc:
            raise X402RailsError("rail returned an undecodable payment payload") from exc
        amount_minor = int(payload["value"])
        return PaymentCredential(
            header_name=self._payment_header,
            header_value=payload_b64,
            rail=rail_name,
            network=str(envelope.get("network", term.get("network", ""))),
            asset=str(term.get("asset", "")),
            amount_minor=amount_minor,
            amount_usdc=amount_minor / USDC_MINOR_UNITS,
            payer=str(payload.get("from", "")),
            recipient=str(payload.get("to", "")),
            expires_at=int(payload.get("validBefore", 0)),
            nonce=str(payload.get("nonce", "")),
            issued_at=int(time.time()),
        )

    @staticmethod
    def _unwrap(response: httpx.Response) -> dict[str, Any]:
        if response.status_code != 200:
            raise X402RailsError(f"settled request failed (http {response.status_code})")
        body = response.json()
        return body.get("data", body) if isinstance(body, dict) else {"data": body}
