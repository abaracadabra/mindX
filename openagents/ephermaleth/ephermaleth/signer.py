# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""ephermaleth.signer — pluggable signing oracles (keys never held by the chain).

Borrowed straight from the BANKON Vault design: the *root of trust is a
Protocol*, swappable without touching the data. A ``Signer`` is any callable

    signer(agent_id: str, message: str) -> (signature_hex, address) | None

that returns an EIP-191 signature + the recovered address, or ``None`` when that
identity has no key it can sign with. The chain asks the signer for a signature
and stores only the signature + public address — the private key never enters
ephermaleth's address space, exactly as the vault's ``/vault/sign`` oracle never
returns a key.

Adapters provided:
  • ``NullSigner``        — never signs (attest-only chains).
  • ``KeymapSigner``      — an in-memory ``{agent_id: private_key}`` map (tests, airgap).
  • ``EnvKeystoreSigner`` — resolves ``{PREFIX}{AGENT_ID_UPPER}`` from an env-style
                            keymap (e.g. ``MINDX_WALLET_PK_CEO_AGENT_MAIN``), the
                            ``data/identity/.wallet_keys.env`` convention.
  • ``OracleSigner``      — delegates to an external sign function (a vault, an HSM,
                            a remote /vault/sign call) — the production path.

eth_account/web3 are imported lazily; without them signers return ``None`` and
chains degrade to attest-only (still hash-linked and verifiable for linkage).
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, Optional, Tuple

logger = logging.getLogger("ephermaleth.signer")

Signature = Tuple[str, str]              # (signature_hex, checksum_address)
Signer = Callable[[str, str], Optional[Signature]]


def _eip191_sign(private_key: str, message: str) -> Optional[Signature]:
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
        from web3 import Web3
    except Exception:  # pragma: no cover - optional dep
        logger.debug("eth_account/web3 unavailable; cannot sign")
        return None
    try:
        acct = Account.from_key(private_key)
        signed = acct.sign_message(encode_defunct(text=message))
        sig = signed.signature.hex()
        if not sig.startswith("0x"):
            sig = "0x" + sig
        return sig, Web3.to_checksum_address(acct.address)
    except Exception as e:
        logger.warning(f"sign failed: {e}")
        return None
    finally:
        private_key = None  # GC hint; do not retain the key


def recover_signer(message: str, signature: str) -> Optional[str]:
    """Recover the EIP-191 signer address of ``(message, signature)``."""
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
        from web3 import Web3
    except Exception:  # pragma: no cover
        return None
    try:
        addr = Account.recover_message(encode_defunct(text=message), signature=signature)
        return Web3.to_checksum_address(addr)
    except Exception as e:
        logger.debug(f"recover_signer failed: {e}")
        return None


def NullSigner() -> Signer:
    """A signer that never signs — produces attest-only (unsigned) links."""
    def _s(agent_id: str, message: str) -> Optional[Signature]:
        return None
    return _s


def KeymapSigner(keymap: Dict[str, str]) -> Signer:
    """Sign from an in-memory ``{agent_id: private_key_hex}`` map."""
    def _s(agent_id: str, message: str) -> Optional[Signature]:
        pk = keymap.get(agent_id)
        return _eip191_sign(pk, message) if pk else None
    return _s


def EnvKeystoreSigner(keymap: Dict[str, str], *, prefix: str = "MINDX_WALLET_PK_") -> Signer:
    """Sign from an env-style keystore: ``{prefix}{AGENT_ID.upper()}`` (dots and
    dashes folded to underscores) → private key. ``keymap`` is the parsed env
    (e.g. ``dict(os.environ)`` or a parsed ``.wallet_keys.env``)."""
    def _var(agent_id: str) -> str:
        return prefix + agent_id.upper().replace(".", "_").replace("-", "_")

    def _s(agent_id: str, message: str) -> Optional[Signature]:
        pk = keymap.get(_var(agent_id))
        return _eip191_sign(pk, message) if pk else None
    return _s


def OracleSigner(sign_fn: Callable[[str, str], Optional[Signature]]) -> Signer:
    """Wrap an external oracle ``sign_fn(agent_id, message) -> (sig, address)|None``
    — a BANKON vault, an HSM, or a remote ``/vault/sign/{agent_id}`` call. The
    production path: the key stays in the vault, ephermaleth only sees the result."""
    def _s(agent_id: str, message: str) -> Optional[Signature]:
        try:
            return sign_fn(agent_id, message)
        except Exception as e:  # pragma: no cover - oracle is best-effort
            logger.warning(f"oracle sign for {agent_id} failed: {e}")
            return None
    return _s


def parse_keys_env(text: str) -> Dict[str, str]:
    """Parse a ``KEY=VALUE`` keystore env file (``#`` comments, blank lines
    skipped). Returns the raw map for :func:`EnvKeystoreSigner`."""
    out: Dict[str, str] = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


__all__ = [
    "Signer", "Signature", "recover_signer",
    "NullSigner", "KeymapSigner", "EnvKeystoreSigner", "OracleSigner",
    "parse_keys_env",
]
