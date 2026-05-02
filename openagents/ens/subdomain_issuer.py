"""
SubdomainIssuer — Python client for BANKON v1 ENS subname registrar.

Talks to `daio/contracts/ens/v1/BankonSubnameRegistrar.sol`. Three paths:

  1. **paid registration** via `register(...)` — caller is the gateway
     relayer; the voucher is an EIP-712 signature from a wallet that holds
     `GATEWAY_SIGNER_ROLE` on the registrar.
  2. **free registration** via `registerFree(...)` — for agents the
     reputation gate considers eligible (BONAFIDE score, PYTHAI stake, or
     ERC-8004 attestation). Labels must be 7+ characters.
  3. **renewal** via `renew(...)` — same voucher pattern as paid register,
     keyed by a different EIP-712 typehash.

This is an **agnostic client**: it doesn't import mindX. Any framework
that wants BANKON subnames can use the same SubdomainIssuer; mindX wires
it up via `agents/core/id_manager_agent.py` (best-effort, fire-and-forget,
non-blocking).

Requires `web3 >= 7.0` and `eth-account >= 0.13`.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from utils.logging_config import get_logger

logger = get_logger(__name__)


# ───── ABI fragments ─────────────────────────────────────────────────── #

AGENT_METADATA_TUPLE = {
    "type": "tuple",
    "name": "meta",
    "components": [
        {"name": "agentURI",      "type": "string"},
        {"name": "mindxEndpoint", "type": "string"},
        {"name": "x402Endpoint",  "type": "string"},
        {"name": "algoIDNftDID",  "type": "string"},
        {"name": "contenthash",   "type": "bytes"},
        {"name": "baseAddress",   "type": "address"},
        {"name": "algoAddr",      "type": "bytes"},
    ],
}

REGISTRAR_V1_ABI = [
    # register (paid)
    {
        "inputs": [
            {"name": "label",              "type": "string"},
            {"name": "owner",              "type": "address"},
            {"name": "expiry",             "type": "uint64"},
            {"name": "paymentReceiptHash", "type": "bytes32"},
            {"name": "deadline",           "type": "uint256"},
            {"name": "gatewaySig",         "type": "bytes"},
            AGENT_METADATA_TUPLE,
        ],
        "name": "register",
        "outputs": [
            {"name": "node",    "type": "bytes32"},
            {"name": "agentId", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # registerFree
    {
        "inputs": [
            {"name": "label",  "type": "string"},
            {"name": "owner",  "type": "address"},
            {"name": "expiry", "type": "uint64"},
            AGENT_METADATA_TUPLE,
        ],
        "name": "registerFree",
        "outputs": [
            {"name": "node",    "type": "bytes32"},
            {"name": "agentId", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # renew
    {
        "inputs": [
            {"name": "label",              "type": "string"},
            {"name": "newExpiry",          "type": "uint64"},
            {"name": "paymentReceiptHash", "type": "bytes32"},
            {"name": "deadline",           "type": "uint256"},
            {"name": "gatewaySig",         "type": "bytes"},
        ],
        "name": "renew",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # quoteUSD (read)
    {
        "inputs": [
            {"name": "label",  "type": "string"},
            {"name": "expiry", "type": "uint64"},
        ],
        "name": "quoteUSD",
        "outputs": [{"name": "usd6", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    # ownerOfLabel (read)
    {
        "inputs": [{"name": "node", "type": "bytes32"}],
        "name": "ownerOfLabel",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    # labelOf (read)
    {
        "inputs": [{"name": "node", "type": "bytes32"}],
        "name": "labelOf",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    # usedReceipts (read)
    {
        "inputs": [{"name": "h", "type": "bytes32"}],
        "name": "usedReceipts",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    # parentNode (immutable)
    {
        "inputs": [], "name": "parentNode",
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "view", "type": "function",
    },
    # SubnameRegistered event
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "name": "node",                "type": "bytes32"},
            {"indexed": False, "name": "label",               "type": "string"},
            {"indexed": True,  "name": "owner",               "type": "address"},
            {"indexed": False, "name": "expiry",              "type": "uint64"},
            {"indexed": False, "name": "priceUSD6",           "type": "uint256"},
            {"indexed": False, "name": "paymentReceiptHash",  "type": "bytes32"},
            {"indexed": False, "name": "erc8004AgentId",      "type": "uint256"},
            {"indexed": False, "name": "free",                "type": "bool"},
        ],
        "name": "SubnameRegistered",
        "type": "event",
    },
]


# ───── EIP-712 typehashes (must match contract verbatim) ─────────────── #

REGISTRATION_TYPE_NAME = "Registration"
REGISTRATION_TYPES = {
    "Registration": [
        {"name": "label",              "type": "string"},
        {"name": "owner",              "type": "address"},
        {"name": "expiry",             "type": "uint64"},
        {"name": "paymentReceiptHash", "type": "bytes32"},
        {"name": "deadline",           "type": "uint256"},
    ],
}
RENEWAL_TYPE_NAME = "Renewal"
RENEWAL_TYPES = {
    "Renewal": [
        {"name": "label",              "type": "string"},
        {"name": "newExpiry",          "type": "uint64"},
        {"name": "paymentReceiptHash", "type": "bytes32"},
        {"name": "deadline",           "type": "uint256"},
    ],
}
EIP712_DOMAIN_NAME    = "BankonSubnameRegistrar"
EIP712_DOMAIN_VERSION = "1"


DEFAULT_DEPLOYMENTS_PATH = Path(__file__).resolve().parents[1] / "deployments" / "sepolia.json"


# ───── AgentMetadata helper ──────────────────────────────────────────── #

@dataclass
class AgentMetadata:
    """Mirror of the on-chain AgentMetadata struct (7 fields)."""
    agentURI:      str = ""
    mindxEndpoint: str = ""
    x402Endpoint:  str = ""
    algoIDNftDID:  str = ""
    contenthash:   bytes = b""
    baseAddress:   str = "0x0000000000000000000000000000000000000000"
    algoAddr:      bytes = b""

    def to_tuple(self):
        """Order MUST match the Solidity struct field order."""
        return (
            self.agentURI,
            self.mindxEndpoint,
            self.x402Endpoint,
            self.algoIDNftDID,
            self.contenthash,
            self.baseAddress,
            self.algoAddr,
        )


# ───── Issuer ────────────────────────────────────────────────────────── #

class SubdomainIssuer:
    """Issue & renew BANKON v1 subnames (paid + free) via the on-chain registrar."""

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        registrar_address: Optional[str] = None,
        controller_pk: Optional[str] = None,
        gateway_signer_pk: Optional[str] = None,
        deployments_path: Optional[Path] = None,
        default_expiry_years: int = 1,
    ):
        try:
            from web3 import Web3
            from eth_account import Account
            from eth_account.messages import encode_typed_data
        except ImportError as e:
            raise ImportError(
                "web3>=7 and eth-account>=0.13 are required for SubdomainIssuer"
            ) from e

        self._Web3 = Web3
        self._Account = Account
        self._encode_typed_data = encode_typed_data

        deploy = self._load_deployments(deployments_path)

        self.rpc_url = rpc_url or os.environ.get("ENS_RPC_URL") or deploy.get("rpc")
        self.registrar_address = registrar_address or (
            deploy.get("contracts", {}).get("BankonSubnameRegistrar", {}).get("address")
            or deploy.get("contracts", {}).get("BankonAgentRegistrar", {}).get("address")  # v0 fallback
        )
        self.controller_pk    = controller_pk    or os.environ.get("ENS_CONTROLLER_PK")
        self.gateway_signer_pk = gateway_signer_pk or os.environ.get("ENS_GATEWAY_SIGNER_PK")
        self.default_expiry_years = default_expiry_years
        self.parent_name = deploy.get("parent_name", "bankon.eth")
        self.network     = deploy.get("network", "sepolia")
        self.explorer    = deploy.get("explorer", "")

        if not self.rpc_url:
            raise RuntimeError("ENS RPC URL missing (ENS_RPC_URL or deployments file)")
        if not self.registrar_address:
            raise RuntimeError("BankonSubnameRegistrar address missing — deploy first")
        if not self.controller_pk:
            logger.warning("ENS_CONTROLLER_PK not set — SubdomainIssuer in dry-run mode")
        if not self.gateway_signer_pk:
            logger.info("ENS_GATEWAY_SIGNER_PK not set — paid register() unavailable; "
                        "registerFree() still usable for reputation-gated agents")

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 30}))
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.registrar_address),
            abi=REGISTRAR_V1_ABI,
        )
        self.controller = (
            Account.from_key(self.controller_pk).address if self.controller_pk else None
        )
        self.gateway_signer = (
            Account.from_key(self.gateway_signer_pk).address if self.gateway_signer_pk else None
        )

    @staticmethod
    def _load_deployments(path: Optional[Path]) -> dict:
        p = path or DEFAULT_DEPLOYMENTS_PATH
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text())
        except Exception as e:
            logger.warning(f"Could not parse deployments file {p}: {e}")
            return {}

    # ────────── Reads ───────────────────────────────────────────────── #

    def parent_node(self) -> bytes:
        return self.contract.functions.parentNode().call()

    def subname(self, label: str) -> str:
        return f"{label}.{self.parent_name}"

    def label_node(self, label: str) -> bytes:
        """Compute the namehash of <label>.bankon.eth WITHOUT touching chain."""
        from eth_utils import keccak
        parent = self.parent_node()
        return keccak(parent + keccak(text=label))

    def owner_of_label(self, label: str) -> str:
        node = self.label_node(label)
        return self.contract.functions.ownerOfLabel(node).call()

    def label_of_node(self, node: bytes) -> str:
        return self.contract.functions.labelOf(node).call()

    def is_label_taken(self, label: str) -> bool:
        owner = self.owner_of_label(label)
        return owner != "0x0000000000000000000000000000000000000000"

    def is_receipt_used(self, receipt_hash: bytes) -> bool:
        return bool(self.contract.functions.usedReceipts(receipt_hash).call())

    def quote_usd(self, label: str, expiry_seconds: Optional[int] = None) -> int:
        expiry = expiry_seconds or int(time.time() + self.default_expiry_years * 365 * 24 * 3600)
        return int(self.contract.functions.quoteUSD(label, expiry).call())

    # ────────── EIP-712 voucher signing ─────────────────────────────── #

    def _domain(self) -> dict:
        return {
            "name":              EIP712_DOMAIN_NAME,
            "version":           EIP712_DOMAIN_VERSION,
            "chainId":           self.w3.eth.chain_id,
            "verifyingContract": self._Web3.to_checksum_address(self.registrar_address),
        }

    def compute_registration_voucher(
        self,
        label: str,
        owner: str,
        expiry: int,
        payment_receipt_hash: bytes,
        deadline: int,
    ) -> bytes:
        """Sign an EIP-712 Registration voucher with the gateway signer key."""
        if not self.gateway_signer_pk:
            raise RuntimeError("ENS_GATEWAY_SIGNER_PK not configured")
        message = {
            "label":              label,
            "owner":              self._Web3.to_checksum_address(owner),
            "expiry":             expiry,
            "paymentReceiptHash": payment_receipt_hash,
            "deadline":           deadline,
        }
        signable = self._encode_typed_data(
            domain_data=self._domain(),
            message_types=REGISTRATION_TYPES,
            message_data=message,
        )
        signed = self._Account.from_key(self.gateway_signer_pk).sign_message(signable)
        return signed.signature

    def compute_renewal_voucher(
        self,
        label: str,
        new_expiry: int,
        payment_receipt_hash: bytes,
        deadline: int,
    ) -> bytes:
        if not self.gateway_signer_pk:
            raise RuntimeError("ENS_GATEWAY_SIGNER_PK not configured")
        message = {
            "label":              label,
            "newExpiry":          new_expiry,
            "paymentReceiptHash": payment_receipt_hash,
            "deadline":           deadline,
        }
        signable = self._encode_typed_data(
            domain_data=self._domain(),
            message_types=RENEWAL_TYPES,
            message_data=message,
        )
        signed = self._Account.from_key(self.gateway_signer_pk).sign_message(signable)
        return signed.signature

    @staticmethod
    def fresh_receipt_hash() -> bytes:
        """A random 32-byte hash for off-chain payment correlation. Replace
        with the actual hash returned by your x402 facilitator on real txs."""
        return secrets.token_bytes(32)

    # ────────── Write paths ─────────────────────────────────────────── #

    async def register_paid(
        self,
        label: str,
        owner: str,
        meta: Optional[AgentMetadata] = None,
        expiry_seconds: Optional[int] = None,
        deadline_seconds: int = 600,
        payment_receipt_hash: Optional[bytes] = None,
    ) -> dict:
        """Paid registration via EIP-712 voucher.

        The gateway signer (ENS_GATEWAY_SIGNER_PK) signs the voucher binding
        (label, owner, expiry, paymentReceiptHash, deadline). The controller
        (ENS_CONTROLLER_PK) submits the tx.
        """
        if not self.controller_pk or not self.gateway_signer_pk:
            return self._dry_run("paid", label, owner)
        return await asyncio.to_thread(
            self._submit_paid_blocking,
            label, owner,
            meta or AgentMetadata(),
            expiry_seconds, deadline_seconds, payment_receipt_hash,
        )

    async def register_free(
        self,
        label: str,
        owner: str,
        meta: Optional[AgentMetadata] = None,
        expiry_seconds: Optional[int] = None,
    ) -> dict:
        """Free registration for reputation-eligible agents (label ≥ 7 chars)."""
        if not self.controller_pk:
            return self._dry_run("free", label, owner)
        if len(label) < 7:
            return {
                "ok": False, "reason": "label_too_short_for_free_tier",
                "agent_id": label, "subname": self.subname(label),
            }
        return await asyncio.to_thread(
            self._submit_free_blocking,
            label, owner, meta or AgentMetadata(), expiry_seconds,
        )

    async def renew(
        self,
        label: str,
        new_expiry_seconds: Optional[int] = None,
        deadline_seconds: int = 600,
        payment_receipt_hash: Optional[bytes] = None,
    ) -> dict:
        if not self.controller_pk or not self.gateway_signer_pk:
            return self._dry_run("renew", label, "")
        return await asyncio.to_thread(
            self._submit_renew_blocking,
            label, new_expiry_seconds, deadline_seconds, payment_receipt_hash,
        )

    # ────────── Blocking submitters (run in thread) ─────────────────── #

    def _build_tx(self, fn_call) -> dict:
        nonce = self.w3.eth.get_transaction_count(self.controller)
        tx = fn_call.build_transaction({
            "from":                self.controller,
            "nonce":               nonce,
            "chainId":             self.w3.eth.chain_id,
            "maxFeePerGas":        self.w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": self.w3.to_wei(2, "gwei"),
        })
        try:
            tx["gas"] = int(self.w3.eth.estimate_gas(tx) * 1.25)
        except Exception:
            tx["gas"] = 800_000
        return tx

    def _send_and_wait(self, tx: dict) -> Any:
        signed = self._Account.sign_transaction(tx, self.controller_pk)
        h = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(h, timeout=300)
        return h, receipt

    def _submit_paid_blocking(
        self, label, owner, meta: AgentMetadata,
        expiry_seconds, deadline_seconds, payment_receipt_hash,
    ) -> dict:
        try:
            owner_cs = self._Web3.to_checksum_address(owner)
            expiry = expiry_seconds or int(time.time() + self.default_expiry_years * 365 * 24 * 3600)
            deadline = int(time.time()) + max(60, deadline_seconds)
            receipt_hash = payment_receipt_hash or self.fresh_receipt_hash()
            sig = self.compute_registration_voucher(label, owner_cs, expiry, receipt_hash, deadline)

            fn = self.contract.functions.register(
                label, owner_cs, expiry, receipt_hash, deadline, sig, meta.to_tuple(),
            )
            tx = self._build_tx(fn)
            tx_hash, rcpt = self._send_and_wait(tx)

            return self._receipt_envelope(label, owner_cs, tx_hash, rcpt, paid=True,
                                          receipt_hash=receipt_hash)
        except Exception as e:
            logger.exception(f"register_paid({label}) failed")
            return {"ok": False, "reason": "exception", "error": str(e),
                    "agent_id": label, "subname": self.subname(label)}

    def _submit_free_blocking(self, label, owner, meta: AgentMetadata, expiry_seconds) -> dict:
        try:
            owner_cs = self._Web3.to_checksum_address(owner)
            expiry = expiry_seconds or int(time.time() + self.default_expiry_years * 365 * 24 * 3600)

            fn = self.contract.functions.registerFree(label, owner_cs, expiry, meta.to_tuple())
            tx = self._build_tx(fn)
            tx_hash, rcpt = self._send_and_wait(tx)
            return self._receipt_envelope(label, owner_cs, tx_hash, rcpt, paid=False)
        except Exception as e:
            logger.exception(f"register_free({label}) failed")
            return {"ok": False, "reason": "exception", "error": str(e),
                    "agent_id": label, "subname": self.subname(label)}

    def _submit_renew_blocking(self, label, new_expiry_seconds, deadline_seconds, payment_receipt_hash) -> dict:
        try:
            new_expiry = new_expiry_seconds or int(time.time() + self.default_expiry_years * 365 * 24 * 3600)
            deadline = int(time.time()) + max(60, deadline_seconds)
            receipt_hash = payment_receipt_hash or self.fresh_receipt_hash()
            sig = self.compute_renewal_voucher(label, new_expiry, receipt_hash, deadline)

            fn = self.contract.functions.renew(label, new_expiry, receipt_hash, deadline, sig)
            tx = self._build_tx(fn)
            tx_hash, rcpt = self._send_and_wait(tx)

            return {
                "ok": rcpt.status == 1,
                "action": "renew",
                "agent_id": label,
                "subname": self.subname(label),
                "tx_hash": tx_hash.hex(),
                "block_number": rcpt.blockNumber,
                "gas_used": rcpt.gasUsed,
                "explorer": f"{self.explorer}/tx/{tx_hash.hex()}" if self.explorer else None,
                "network": self.network,
            }
        except Exception as e:
            logger.exception(f"renew({label}) failed")
            return {"ok": False, "reason": "exception", "error": str(e),
                    "agent_id": label, "subname": self.subname(label)}

    # ────────── Envelopes ───────────────────────────────────────────── #

    def _receipt_envelope(self, label, owner_cs, tx_hash, rcpt, paid: bool,
                          receipt_hash: Optional[bytes] = None) -> dict:
        # Decode the SubnameRegistered event for the agentTokenId, if present.
        agent_token_id = None
        try:
            for ev in self.contract.events.SubnameRegistered().process_receipt(rcpt):
                agent_token_id = int(ev["args"]["erc8004AgentId"])
                break
        except Exception:
            pass
        return {
            "ok": rcpt.status == 1,
            "action": "register_paid" if paid else "register_free",
            "agent_id": label,
            "subname": self.subname(label),
            "wallet": owner_cs,
            "tx_hash": tx_hash.hex(),
            "block_number": rcpt.blockNumber,
            "gas_used": rcpt.gasUsed,
            "explorer": f"{self.explorer}/tx/{tx_hash.hex()}" if self.explorer else None,
            "network": self.network,
            "erc8004_agent_id": agent_token_id,
            "payment_receipt_hash": receipt_hash.hex() if receipt_hash else None,
        }

    def _dry_run(self, mode: str, label: str, owner: str) -> dict:
        return {
            "ok": False,
            "reason": "dry_run_no_pk",
            "mode": mode,
            "agent_id": label,
            "subname": self.subname(label),
            "wallet": owner or None,
            "note": "set ENS_CONTROLLER_PK (and ENS_GATEWAY_SIGNER_PK for paid) to live-fire",
        }


# ───── Module-level convenience for IDManagerAgent integration ───────── #

_default_issuer: Optional[SubdomainIssuer] = None
_issuer_lock = asyncio.Lock()


async def get_default_issuer() -> Optional[SubdomainIssuer]:
    global _default_issuer
    async with _issuer_lock:
        if _default_issuer is not None:
            return _default_issuer
        try:
            _default_issuer = SubdomainIssuer()
            return _default_issuer
        except Exception as e:
            logger.info(f"SubdomainIssuer not initialized: {e}")
            return None


async def issue_for_agent_async(
    agent_id: str,
    wallet: str,
    persona_url: str = "",
    summary: str = "",
    free: bool = True,
) -> dict:
    """Fire-and-forget helper. Defaults to free path; falls back to paid if
    free fails (label too short or reputation-gate denies).

    Always returns a dict envelope; never raises.
    """
    issuer = await get_default_issuer()
    if issuer is None:
        return {"ok": False, "reason": "issuer_not_configured", "agent_id": agent_id}
    meta = AgentMetadata(
        agentURI=persona_url,
        mindxEndpoint=persona_url,
        x402Endpoint="",
        algoIDNftDID="",
        contenthash=b"",
        baseAddress="0x0000000000000000000000000000000000000000",
        algoAddr=b"",
    )
    try:
        if free and len(agent_id) >= 7:
            res = await issuer.register_free(agent_id, wallet, meta=meta)
            if res.get("ok"):
                return res
        return await issuer.register_paid(agent_id, wallet, meta=meta)
    except Exception as e:
        logger.exception(f"issue_for_agent_async({agent_id}) failed")
        return {"ok": False, "reason": "exception", "error": str(e), "agent_id": agent_id}
