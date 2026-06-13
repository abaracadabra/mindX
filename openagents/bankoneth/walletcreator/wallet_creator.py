"""
walletcreator — wallet-creation services for the BANKON allchain.

Creates wallets and stores their private keys in the always-open-source
{BankonVault}. One call can mint an identity across **every chain on
allchain.html**: a single EVM keypair is valid on every EVM chain (Ethereum, 0G,
Base, Polygon, Arbitrum, Optimism, Circle ARC, …), and a separate ed25519 keypair
covers Algorand. The vault never yields a key except to sign.

Wallet creation is a **pay-to-play service**: gate it behind the pay2play
`wallet.create` / `vault.create` services (fee set in the bankon contracts) — pay,
then the service mints + vaults the wallet. This module is the off-chain minter;
pay2play is the on-chain rail.

allchain.html is the public, viewable surface (source: /home/hacker/chainmarketcap;
UI: /home/hacker/live). The frontend is open source — see the BANKON delivery
doctrine — so the community can audit exactly what touches their keys.

© BANKON — all rights preserved.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Any, Dict, List, Optional

from eth_account import Account
from eth_account.messages import encode_defunct

from bankon_vault import BankonVault

# ── allchain registry: every chain a wallet can be minted for. EVM chains share
#    one address (one secp256k1 key); non-EVM kinds get their own keypair. ──────
CHAINS: Dict[str, Dict[str, Any]] = {
    "ethereum": {"kind": "evm", "chainId": 1,        "symbol": "ETH"},
    "base":     {"kind": "evm", "chainId": 8453,     "symbol": "ETH"},
    "optimism": {"kind": "evm", "chainId": 10,       "symbol": "ETH"},
    "arbitrum": {"kind": "evm", "chainId": 42161,    "symbol": "ETH"},
    "polygon":  {"kind": "evm", "chainId": 137,      "symbol": "POL"},
    "zerog":    {"kind": "evm", "chainId": 16601,    "symbol": "0G"},
    "arc":      {"kind": "evm", "chainId": 0,        "symbol": "USDC"},   # Circle ARC (id set when finalised)
    "anvil":    {"kind": "evm", "chainId": 31337,    "symbol": "ETH"},    # local test
    "algorand": {"kind": "algorand", "chainId": 0,   "symbol": "ALGO"},   # ed25519
}

EVM_CHAINS = [c for c, m in CHAINS.items() if m["kind"] == "evm"]

# Well-known Anvil dev keys (deterministic; for LOCAL TESTING ONLY — never fund).
ANVIL_KEYS: List[str] = [
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # acct 0
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",  # acct 1
    "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cddfb9b2",  # acct 2
]


def _algorand_address(pubkey: bytes) -> str:
    """Standard Algorand address: base32(pubkey || checksum), checksum =
    last 4 bytes of SHA512/256(pubkey), padding stripped."""
    chk = hashlib.new("sha512_256", pubkey).digest()[-4:]
    return base64.b32encode(pubkey + chk).decode("ascii").rstrip("=")


class WalletCreator:
    """Mints wallets and vaults their keys. Vault ids are `wallet:<chainkind>:<address>`."""

    def __init__(self, vault: BankonVault):
        self.vault = vault

    # ── EVM (covers every EVM chain on allchain) ────────────────────────
    def create_evm_wallet(self, label: str = "") -> Dict[str, Any]:
        acct = Account.create(secrets.token_bytes(32))
        vault_id = f"wallet:evm:{acct.address}"
        self.vault.put(
            vault_id,
            acct.key,  # 32-byte private key
            meta={"label": label, "kind": "evm", "address": acct.address},
        )
        return {
            "vault_id": vault_id,
            "kind": "evm",
            "address": acct.address,
            "label": label,
            "chains": {c: acct.address for c in EVM_CHAINS},  # same address everywhere
        }

    def import_anvil(self, index: int = 0, label: str = "anvil") -> Dict[str, Any]:
        """Vault a deterministic Anvil dev key for local testing."""
        acct = Account.from_key(ANVIL_KEYS[index])
        vault_id = f"wallet:evm:{acct.address}"
        self.vault.put(vault_id, acct.key, meta={"label": label, "kind": "evm", "anvil": index, "address": acct.address})
        return {"vault_id": vault_id, "kind": "evm", "address": acct.address, "chains": {c: acct.address for c in EVM_CHAINS}}

    # ── Algorand (ed25519) ──────────────────────────────────────────────
    def create_algorand_wallet(self, label: str = "") -> Dict[str, Any]:
        from nacl.signing import SigningKey

        sk = SigningKey.generate()
        pub = bytes(sk.verify_key)
        addr = _algorand_address(pub)
        vault_id = f"wallet:algorand:{addr}"
        self.vault.put(vault_id, bytes(sk), meta={"label": label, "kind": "algorand", "address": addr})
        return {"vault_id": vault_id, "kind": "algorand", "address": addr, "label": label, "chains": {"algorand": addr}}

    # ── allchain: a wallet on every chain ───────────────────────────────
    def create_allchain_wallet(self, label: str = "") -> Dict[str, Any]:
        """Mint a full allchain identity: one EVM keypair for every EVM chain +
        an Algorand keypair. Returns a {chain: address} map for the whole set."""
        evm = self.create_evm_wallet(label)
        alg = self.create_algorand_wallet(label)
        chains = dict(evm["chains"])
        chains.update(alg["chains"])
        return {
            "label": label,
            "evm": {"vault_id": evm["vault_id"], "address": evm["address"]},
            "algorand": {"vault_id": alg["vault_id"], "address": alg["address"]},
            "chains": chains,
        }

    # ── signing (proof of identity) ─────────────────────────────────────
    def account(self, vault_id: str) -> "Account":
        """Load the EVM account for `vault_id` (decrypts the key in memory)."""
        if ":evm:" not in vault_id:
            raise ValueError("account() is for EVM wallets")
        return Account.from_key(self.vault.get(vault_id))

    def sign_message(self, vault_id: str, message: str) -> str:
        """EIP-191 personal_sign by the vaulted key — the signature IS the proof
        of private-key ownership = proof of identity (pay2play `playWithSig`)."""
        acct = self.account(vault_id)
        sig = acct.sign_message(encode_defunct(text=message))
        return sig.signature.hex()

    def address_of(self, vault_id: str) -> str:
        return self.vault.meta(vault_id).get("address", "")

    def list_wallets(self) -> List[Dict[str, Any]]:
        return [row for row in self.vault.list() if row["id"].startswith("wallet:")]


__all__ = ["WalletCreator", "CHAINS", "EVM_CHAINS"]
