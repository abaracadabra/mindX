# Copyright (c) 2026 mindX / BANKON
"""
Independent verification of mindX's Algorand identity, through Algorandscout.

mindX recognizes an OVERSEER by checking an Ed25519 signature against the public
key embedded in a configured Algorand address (``mindx_backend_service/overseer_auth.py``).
That check is cryptographically sound and answers exactly one question: *did the
holder of this address's key sign this message?*

It cannot answer a second question that Algorand allows to be true:

    **Is that key still the account's signing authority?**

Algorand accounts can be **rekeyed**. After a rekey, on-chain authority belongs to
the account's ``auth-addr``, not to the key embedded in the address. A signature
check like mindX's would keep accepting the *original* key — which, after a
rekey, is precisely the key that is no longer in charge. Off-chain signature
verification is structurally blind to this; only a chain read reveals it.

So this module reads the account through
`Algorandscout <https://github.com/openbdk/algorandscout>`_ and compares what the
chain says against what mindX assumes. It is the Algorand half of the discipline
already applied to memory anchors: *a receipt mindX printed for itself is not
evidence.*

**No fallback by design.** If Algorandscout is unreachable, this reports
``unavailable`` and says so. It does not quietly reach for another source, because
an unavailable verifier that looks like a passing one is worse than an outage.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import aiohttp

from utils.logging_config import get_logger

logger = get_logger(__name__)

#: Where Algorandscout is listening. Loopback by default: the verifier and the
#: service it queries are colocated, so this never crosses the network.
ALGORANDSCOUT_URL = os.environ.get("MINDX_ALGORANDSCOUT_URL", "http://127.0.0.1:8100")
REQUEST_TIMEOUT_S = float(os.environ.get("MINDX_ALGORANDSCOUT_TIMEOUT_S", "20"))

#: Verdicts, worst-first. `attention` means the chain disagrees with an assumption
#: mindX is making; `unavailable` means nothing was checked and nothing is claimed.
VERDICT_ATTENTION = "attention"
VERDICT_VERIFIED = "verified"
VERDICT_UNAVAILABLE = "unavailable"


class AlgorandVerifier:
    """Reads mindX's own Algorand identity back from the chain and reports honestly."""

    def __init__(self, base_url: Optional[str] = None, timeout_s: Optional[float] = None):
        self.base_url = (base_url or ALGORANDSCOUT_URL).rstrip("/")
        self.timeout_s = timeout_s or REQUEST_TIMEOUT_S

    # ------------------------------------------------------------------ transport

    async def _get(self, path: str) -> tuple[Optional[dict], Optional[str]]:
        """Returns (payload, error). Never raises — an outage is data, not an exception."""
        url = f"{self.base_url}{path}"
        timeout = aiohttp.ClientTimeout(total=self.timeout_s)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers={"Accept": "application/json"}) as resp:
                    if resp.status == 404:
                        return None, "not_found"
                    if resp.status >= 400:
                        body = (await resp.text())[:200]
                        return None, f"http_{resp.status}: {body}"
                    return await resp.json(content_type=None), None
        except (aiohttp.ClientError, TimeoutError, OSError) as exc:
            return None, f"unreachable: {type(exc).__name__}: {exc}"

    async def available(self) -> tuple[bool, dict[str, Any]]:
        payload, error = await self._get("/readyz")
        if error:
            return False, {"error": error, "url": self.base_url}
        return bool(payload and payload.get("ready")), (payload or {})

    # ------------------------------------------------------------- verification

    async def verify_address(self, address: str, *, role: str = "overseer") -> dict[str, Any]:
        """
        Verify one address against the chain.

        Findings are graded. `critical` means an assumption mindX actively relies
        on is contradicted by the chain.
        """
        result: dict[str, Any] = {
            "address": address,
            "role": role,
            "verdict": VERDICT_UNAVAILABLE,
            "findings": [],
            "chain": None,
        }

        payload, error = await self._get(f"/api/v2/addresses/{address}")

        if error == "not_found":
            result["verdict"] = VERDICT_ATTENTION
            result["findings"].append(
                {
                    "severity": "critical",
                    "code": "account_absent",
                    "detail": (
                        "This address is recognized as OVERSEER but does not exist on the "
                        "configured network. Either the address is wrong or mindX is pointed "
                        "at the wrong chain."
                    ),
                }
            )
            return result

        if error:
            result["findings"].append(
                {
                    "severity": "info",
                    "code": "verifier_unavailable",
                    "detail": f"Algorandscout did not answer ({error}). Nothing was verified.",
                }
            )
            return result

        account = payload or {}
        result["chain"] = {
            "balance": account.get("coin_balance_decimal"),
            "balance_micro": account.get("coin_balance"),
            "status": account.get("status"),
            "signature_type": account.get("signature_type"),
            "rekeyed_to": account.get("rekeyed_to"),
            "min_balance": account.get("min_balance"),
            "created_at_round": account.get("created_at_round"),
            "as_of_round": account.get("as_of_round"),
            "counters": account.get("counters"),
            "deleted": account.get("deleted"),
        }

        findings = result["findings"]

        # The finding this module exists for.
        rekeyed_to = account.get("rekeyed_to")
        if rekeyed_to:
            findings.append(
                {
                    "severity": "critical",
                    "code": "account_rekeyed",
                    "detail": (
                        f"On-chain signing authority has been rekeyed to {rekeyed_to}. mindX's "
                        "OVERSEER check verifies signatures against the key embedded in the "
                        "address, so it would still accept the original key — which is no longer "
                        "the account's authority. Rotate MINDX_ALGO_ADDRESS or investigate."
                    ),
                }
            )

        if account.get("deleted"):
            findings.append(
                {
                    "severity": "critical",
                    "code": "account_deleted",
                    "detail": "The indexer reports this account as deleted.",
                }
            )

        # Below the minimum balance an account cannot transact; it is not a
        # signature problem, but an OVERSEER that cannot act is worth surfacing.
        try:
            balance = int(account.get("coin_balance") or 0)
            minimum = int(account.get("min_balance") or 0)
            if minimum and balance < minimum:
                findings.append(
                    {
                        "severity": "warning",
                        "code": "below_min_balance",
                        "detail": f"Balance {balance} is under the {minimum} microAlgo minimum; the account cannot transact.",
                    }
                )
        except (TypeError, ValueError):
            pass

        if account.get("signature_type") == "msig":
            findings.append(
                {
                    "severity": "info",
                    "code": "multisig_account",
                    "detail": (
                        "This is a multisig account. mindX's single-signature OVERSEER check "
                        "does not model an m-of-n threshold."
                    ),
                }
            )

        result["verdict"] = (
            VERDICT_ATTENTION if any(f["severity"] == "critical" for f in findings) else VERDICT_VERIFIED
        )
        return result

    async def verify_overseer(self) -> dict[str, Any]:
        """
        Verify every address mindX recognizes as OVERSEER.

        The verdict is the worst across addresses: one rekeyed identity is a
        problem regardless of how many healthy ones sit beside it.
        """
        try:
            from mindx_backend_service.overseer_auth import overseer_addresses

            addresses = sorted(overseer_addresses())
        except Exception as exc:  # noqa: BLE001 — config shape is not this module's business
            logger.warning("algorand_verifier: could not read OVERSEER config: %s", exc)
            addresses = []

        ready, health = await self.available()

        report: dict[str, Any] = {
            "verifier": "algorandscout",
            "verifier_url": self.base_url,
            "verifier_available": ready,
            "network": (health or {}).get("network"),
            "indexer_lag_rounds": (health or {}).get("indexer_lag_rounds"),
            "configured_addresses": len(addresses),
            "results": [],
            "verdict": VERDICT_UNAVAILABLE,
            # Stated in the payload itself so no consumer can mistake the scope
            # of what a "verified" verdict means.
            "not_verified": [
                "possession of the private key — the chain shows authority, not custody",
                "off-chain compromise of a key that has not been rekeyed",
                "whether the operator, rather than someone else, holds the key",
            ],
        }

        if not addresses:
            report["findings"] = [
                {
                    "severity": "warning",
                    "code": "no_overseer_configured",
                    "detail": "No MINDX_ALGO_ADDRESS / MINDX_OVERSEER_ADDRESSES configured; nothing to verify.",
                }
            ]
            return report

        if not ready:
            report["findings"] = [
                {
                    "severity": "info",
                    "code": "verifier_unavailable",
                    "detail": (
                        f"Algorandscout at {self.base_url} is not ready ({health.get('error', 'not ready')}). "
                        "No verification was performed and none is claimed."
                    ),
                }
            ]
            return report

        for address in addresses:
            report["results"].append(await self.verify_address(address))

        verdicts = {r["verdict"] for r in report["results"]}
        if VERDICT_ATTENTION in verdicts:
            report["verdict"] = VERDICT_ATTENTION
        elif verdicts == {VERDICT_VERIFIED}:
            report["verdict"] = VERDICT_VERIFIED
        else:
            report["verdict"] = VERDICT_UNAVAILABLE

        await _emit_catalogue(report)
        return report


async def _emit_catalogue(report: dict[str, Any]) -> None:
    """
    Mirror the verdict into the catalogue.

    Telemetry must never break verification, so failures are swallowed — but they
    are logged at warning, not debug. A silently failing emitter looks exactly
    like a working one, which is how the first version of this function shipped
    writing nothing at all.
    """
    try:
        from agents.catalogue.events import emit_catalogue_event

        critical = [
            {"address": r["address"], **f}
            for r in report.get("results", [])
            for f in r.get("findings", [])
            if f.get("severity") == "critical"
        ]
        await emit_catalogue_event(
            kind="identity.verified",
            actor="algorand_verifier",
            payload={
                "verifier": "algorandscout",
                "verifier_url": report.get("verifier_url"),
                "verdict": report.get("verdict"),
                "network": report.get("network"),
                "addresses": report.get("configured_addresses"),
                "critical_findings": critical,
                "results": [
                    {
                        "address": r["address"],
                        "verdict": r["verdict"],
                        "rekeyed_to": (r.get("chain") or {}).get("rekeyed_to"),
                    }
                    for r in report.get("results", [])
                ],
            },
            source_log="insight/identity/algorand",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("algorand_verifier: catalogue emit failed: %s", exc)


_verifier: Optional[AlgorandVerifier] = None


def get_verifier() -> AlgorandVerifier:
    global _verifier
    if _verifier is None:
        _verifier = AlgorandVerifier()
    return _verifier


async def verify_overseer_identity() -> dict[str, Any]:
    """Module-level entry point used by the insight route."""
    return await get_verifier().verify_overseer()
