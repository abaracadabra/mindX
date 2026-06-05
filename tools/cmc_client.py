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

"""cmc_client — x402 challenge decoder and base URL for the rails service.

This is the small surface ``tools/x402_rails.py`` imports to read an HTTP
``402 Payment Required`` challenge. It deliberately holds no wallet and signs
nothing — challenge parsing and credential signing are separate concerns so the
parser can run anywhere (a public gateway, a discovery probe) without a key in
scope. Signing lives in :mod:`tools.x402_signer`.

The wire shape this decodes is the x402 protocol envelope (https://x402.org):
a JSON document carrying an ``accepts`` (a.k.a. ``paymentRequirements``) array,
each element naming one settlement *rail* — its ``network``, ``asset``,
``maxAmountRequired``, ``payTo``, and rail-specific ``extra``. Each EVM rail's
terms describe an ERC-3009 ``transferWithAuthorization`` to be signed under
ERC-20 / EIP-712 / EIP-155 (see ``docs/cypherpunk2048/EIP_REFERENCES.md`` for
the absolute references). The decoder is format-tolerant: a ``402`` challenge
may arrive as a JSON body or as a base64-encoded ``payment-required`` header.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
from collections.abc import Mapping
from typing import Any

# Base URL of the x402-gated service the rails client probes by default. The
# rails service settles challenges from any host; this is only the convenience
# default for relative URLs handed to ``X402RailsService.issue_for_url`` /
# ``settle``. Override per deployment.
X402_BASE_URL: str = os.environ.get(
    "MINDX_X402_BASE_URL", "https://x402.agenticplace.pythai.net"
)


class CMCClientError(RuntimeError):
    """Raised when a 402 challenge cannot be decoded into usable terms."""


def decode_payment_challenge(source: Any) -> dict[str, Any]:
    """Decode an x402 ``402`` challenge into a plain mapping.

    Accepts any of the three forms an x402 challenge travels in:

    * an already-decoded mapping (returned unchanged, as a ``dict``);
    * a JSON string body (``{"accepts": [...]}`` / ``{"paymentRequirements": ...}``);
    * a base64-encoded ``payment-required`` header value wrapping that JSON.

    The returned document always carries an ``accepts`` array of accepted
    terms — the form :meth:`tools.x402_rails.X402RailsService.issue_from_challenge`
    consumes. Each term names an x402 ``network`` and, for EVM rails, the
    ERC-3009 settlement parameters.

    Raises:
        CMCClientError: The source is empty or carries no decodable terms.
    """
    if isinstance(source, Mapping):
        challenge = dict(source)
    elif isinstance(source, (bytes, bytearray)):
        challenge = _loads(bytes(source))
    elif isinstance(source, str):
        challenge = _decode_str(source)
    else:
        raise CMCClientError(f"cannot decode a challenge from {type(source).__name__}")

    accepts = challenge.get("accepts") or challenge.get("paymentRequirements")
    if not accepts:
        raise CMCClientError("402 challenge carried no accepted terms")
    # Normalise to the canonical key the rails service reads first.
    challenge.setdefault("accepts", accepts)
    return challenge


def _decode_str(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        raise CMCClientError("empty 402 challenge")
    # A JSON body starts with '{'; anything else is treated as a base64 header.
    if text[0] != "{":
        try:
            text = base64.b64decode(text).decode("utf-8")
        except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
            raise CMCClientError("challenge was neither JSON nor base64-JSON") from exc
    return _loads(text)


def _loads(payload: str | bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(payload)
    except (ValueError, TypeError) as exc:
        raise CMCClientError("challenge body was not valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise CMCClientError("challenge body was not a JSON object")
    return dict(decoded)


__all__ = ["X402_BASE_URL", "CMCClientError", "decode_payment_challenge"]
