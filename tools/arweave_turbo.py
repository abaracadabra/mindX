# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved
"""Arweave/Turbo fulfillment desk — the x402 third rail (permaweb leg).

x402 gates the *payment* (USDC on an EVM/AVM rail); this desk holds Turbo Credits
and performs the permanent ANS-104 upload (reference §4 fulfillment-desk pattern).
THOT/THLNK permaweb writes become a paid endpoint: collect USDC, then upload.

Ported from the production reference `bankon_arweave_payment.py`
(`docs/operations/shipping_pay2store.md` §1C). There is no maintained Python Turbo
SDK, so this calls the Turbo HTTP API directly and signs ANS-104 DataItems itself
(deepHash, RSA-PSS-SHA256). Turbo facts (pinned): pay in USDC-on-Base, payment
service `payment.ardrive.io`, upload `upload.ardrive.io`, uploads ≤100 KiB are free.

Heavy deps (`cryptography`, `web3`) are imported lazily so this module imports on a
box without them — the gated endpoint degrades to a clear error, never an
ImportError at load (consistent with mindX's torch-free-style guarded pattern).
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import httpx

log = logging.getLogger("bankon.arweave")

PAYMENT_BASE = "https://payment.ardrive.io"
UPLOAD_BASE = "https://upload.ardrive.io"
GATEWAY = "https://arweave.net"
FREE_UPLOAD_BYTES = 102_400  # ≤100 KiB DataItems require no signature/balance
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base mainnet


class ArweaveTurboError(RuntimeError):
    pass


class InsufficientCreditsError(ArweaveTurboError):
    pass


# ── base64url helpers ────────────────────────────────────────────────────────
def b64u_enc(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def b64u_dec(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


# ── JWK / wallet ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ArweaveWallet:
    jwk: dict
    address: str

    @property
    def public_key_n(self) -> bytes:
        return b64u_dec(self.jwk["n"])


def _rsa_priv_from_jwk(jwk: dict):
    from cryptography.hazmat.primitives.asymmetric.rsa import (
        RSAPrivateNumbers,
        RSAPublicNumbers,
    )

    g = lambda k: int.from_bytes(b64u_dec(jwk[k]), "big")  # noqa: E731
    pub = RSAPublicNumbers(g("e"), g("n"))
    return RSAPrivateNumbers(
        g("p"), g("q"), g("d"), g("dp"), g("dq"), g("qi"), pub
    ).private_key()


def wallet_from_jwk(jwk: dict) -> ArweaveWallet:
    addr = b64u_enc(hashlib.sha256(b64u_dec(jwk["n"])).digest())
    return ArweaveWallet(jwk=jwk, address=addr)


def load_or_create_wallet(path: Path) -> ArweaveWallet:
    """Load an Arweave JWK from disk, or generate a new RSA-4096 one if absent."""
    if path.exists():
        return wallet_from_jwk(json.loads(path.read_text()))
    from cryptography.hazmat.primitives.asymmetric import rsa

    priv = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    nums = priv.private_numbers()
    pub = nums.public_numbers
    jwk = {
        "kty": "RSA",
        "n": b64u_enc(pub.n.to_bytes((pub.n.bit_length() + 7) // 8, "big")),
        "e": b64u_enc(pub.e.to_bytes((pub.e.bit_length() + 7) // 8, "big")),
        "d": b64u_enc(nums.d.to_bytes(512, "big")),
        "p": b64u_enc(nums.p.to_bytes(256, "big")),
        "q": b64u_enc(nums.q.to_bytes(256, "big")),
        "dp": b64u_enc(nums.dmp1.to_bytes(256, "big")),
        "dq": b64u_enc(nums.dmq1.to_bytes(256, "big")),
        "qi": b64u_enc(nums.iqmp.to_bytes(256, "big")),
    }
    path.write_text(json.dumps(jwk))
    path.chmod(0o600)
    return wallet_from_jwk(jwk)


def resolve_wallet() -> ArweaveWallet:
    """Resolve the desk JWK: env JSON, vault deposit, or a key-file path."""
    raw = os.environ.get("ARWEAVE_JWK")
    if raw:
        return wallet_from_jwk(json.loads(raw))
    try:  # BANKON vault deposit (vault-as-oracle), never hard-imports
        from mindx_backend_service.bankon_vault import get_credential

        dep = get_credential("arweave_jwk")
        if dep:
            return wallet_from_jwk(json.loads(dep))
    except Exception:
        pass
    path = os.environ.get("ARWEAVE_JWK_PATH")
    if path:
        return load_or_create_wallet(Path(path))
    raise ArweaveTurboError("no Arweave JWK configured (ARWEAVE_JWK / vault / ARWEAVE_JWK_PATH)")


# ── ANS-104 deepHash + DataItem ──────────────────────────────────────────────
def _deep_hash(parts: object) -> bytes:
    """ANS-104 deepHash: SHA-384 over 'list'/'blob' tagged structures."""
    if isinstance(parts, (bytes, bytearray)):
        tag = b"blob" + str(len(parts)).encode()
        return hashlib.sha384(hashlib.sha384(tag).digest() + hashlib.sha384(bytes(parts)).digest()).digest()
    tag = b"list" + str(len(parts)).encode()
    acc = hashlib.sha384(tag).digest()
    for p in parts:
        acc = hashlib.sha384(acc + _deep_hash(p)).digest()
    return acc


def _avro_long(n: int) -> bytes:
    z = (n << 1) ^ (n >> 63)
    out = bytearray()
    while z & ~0x7F:
        out.append((z & 0x7F) | 0x80)
        z >>= 7
    out.append(z & 0x7F)
    return bytes(out)


def _avro_tags(tags: Sequence[Tuple[str, str]]) -> bytes:
    """Encode tags using Avro array-of-record-of-strings (ANS-104)."""
    if not tags:
        return b"\x00"
    out = bytearray()
    out += _avro_long(len(tags))
    for k, v in tags:
        kb, vb = k.encode("utf-8"), v.encode("utf-8")
        out += _avro_long(len(kb)) + kb + _avro_long(len(vb)) + vb
    out += b"\x00"
    return bytes(out)


def build_and_sign_dataitem(
    wallet: ArweaveWallet,
    data: bytes,
    tags: Sequence[Tuple[str, str]],
    target: str = "",
    anchor: Optional[bytes] = None,
) -> Tuple[bytes, bytes]:
    """Build an ANS-104 DataItem, deepHash-sign with RSA-PSS-SHA256.

    Returns ``(item_bytes, item_id)``.
    """
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    sig_type = (1).to_bytes(2, "little")  # 1 = arweave RSA
    owner = b64u_dec(wallet.jwk["n"])  # 512 bytes
    target_b = b64u_dec(target) if target else b""
    anchor_b = anchor if anchor is not None else secrets.token_bytes(32)
    tag_bytes = _avro_tags(tags)

    deep = _deep_hash([
        b"dataitem", b"1", str(int.from_bytes(sig_type, "little")).encode(),
        owner, target_b, anchor_b, tag_bytes, data,
    ])
    priv = _rsa_priv_from_jwk(wallet.jwk)
    signature = priv.sign(
        deep, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256()
    )
    item_id = hashlib.sha256(signature).digest()

    out = bytearray()
    out += sig_type
    out += signature  # 512 bytes
    out += owner  # 512 bytes
    out += (b"\x01" + target_b) if target_b else b"\x00"
    out += (b"\x01" + anchor_b) if anchor_b else b"\x00"
    out += len(tags).to_bytes(8, "little")
    out += len(tag_bytes).to_bytes(8, "little")
    out += tag_bytes
    out += data
    return bytes(out), item_id


# ── Turbo HTTP client ────────────────────────────────────────────────────────
class TurboClient:
    def __init__(self, wallet: ArweaveWallet, *, timeout: float = 30.0):
        self.wallet = wallet
        self.http = httpx.Client(timeout=timeout, headers={"User-Agent": "bankon-turbo/1.0"})

    def balance_winc(self) -> int:
        r = self.http.get(f"{PAYMENT_BASE}/v1/balance/{self.wallet.address}")
        if r.status_code == 404:
            return 0
        r.raise_for_status()
        return int(r.json()["winc"])

    def price_for_bytes(self, n_bytes: int) -> int:
        r = self.http.get(f"{PAYMENT_BASE}/v1/price/bytes/{n_bytes}")
        r.raise_for_status()
        return int(r.json()["winc"])

    def upload_signed(self, item_bytes: bytes) -> dict:
        r = self.http.post(
            f"{UPLOAD_BASE}/tx", content=item_bytes,
            headers={"content-type": "application/octet-stream"},
        )
        if r.status_code == 402:
            raise InsufficientCreditsError(r.text)
        r.raise_for_status()
        return r.json()


# ── high-level fulfillment desk ──────────────────────────────────────────────
class ArweaveTurboDesk:
    """The fulfillment desk: holds Turbo Credits, performs the permanent upload.

    The x402 layer has already collected payment; this just builds, signs, and
    uploads the ANS-104 DataItem and returns its Arweave id + gateway url.
    """

    def __init__(self, wallet: Optional[ArweaveWallet] = None):
        self.wallet = wallet or resolve_wallet()
        self.turbo = TurboClient(self.wallet)

    def upload(self, data: bytes, *, app_name: str = "THOT", content_type: str = "application/octet-stream",
               extra_tags: Optional[Sequence[Tuple[str, str]]] = None) -> Dict[str, Any]:
        tags = [("Content-Type", content_type), ("App-Name", app_name)] + list(extra_tags or [])
        item_bytes, item_id = build_and_sign_dataitem(self.wallet, data, tags)
        result = self.turbo.upload_signed(item_bytes)
        arweave_id = result.get("id") or b64u_enc(item_id)
        return {
            "arweaveId": arweave_id,
            "url": f"{GATEWAY}/{arweave_id}",
            "bytes": len(data),
            "free": len(data) <= FREE_UPLOAD_BYTES,
            "owner": self.wallet.address,
        }


def wait_for_indexing(tx_id_b64u: str, *, timeout: float = 180.0, gw: str = GATEWAY) -> dict:
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        r = httpx.get(f"{gw}/tx/{tx_id_b64u}/status", timeout=10.0)
        if r.status_code == 200:
            last = r.json()
            if last.get("number_of_confirmations", 0) >= 1:
                return last
        time.sleep(5.0)
    raise TimeoutError(f"not confirmed within {timeout}s, last={last!r}")


__all__ = [
    "ArweaveTurboError", "InsufficientCreditsError", "ArweaveWallet",
    "ArweaveTurboDesk", "TurboClient", "build_and_sign_dataitem",
    "load_or_create_wallet", "resolve_wallet", "wallet_from_jwk",
    "b64u_enc", "b64u_dec", "FREE_UPLOAD_BYTES",
]
