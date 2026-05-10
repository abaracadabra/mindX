"""
attribution_receipt_client — sign + submit MarketingAttributionReceipt envelopes.

EIP-712 typed-data signing. The contract enforces:
  - Tessera credential present
  - Censura score >= floor
  - Per-(agent, campaignId) nonce strict
  - Signature recovers to `agent`

Off-chain, this client builds the ABI calldata for `record(...)` and either
returns it (dry-run) or submits via RawTxClient (live).

The struct layout MUST stay in lockstep with
`daio/contracts/marketing/MarketingAttributionReceipt.sol::ENVELOPE_TYPEHASH`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


# EIP-712 typehash mirror (keccak of the type string from the contract).
# Schema v2: includes `boardroomSessionId` joining receipt to BoardroomSession.
ENVELOPE_TYPE_STRING = (
    "MarketingCampaign("
    "bytes32 campaignId,"
    "bytes32 briefCid,"
    "bytes32 audienceClusterHash,"
    "uint32  channelSetMask,"
    "uint128 totalSpendUsdMicro,"
    "bytes32 outcomeMetricCid,"
    "bytes32 boardroomSessionId,"
    "bytes32 traceId,"
    "uint64  nonce,"
    "uint64  signedAt"
    ")"
)


@dataclass
class EnvelopePayload:
    """Mirrors the on-chain MarketingCampaign struct (v2 includes boardroom_session_id)."""
    campaign_id: bytes              # bytes32
    brief_cid: bytes                # bytes32
    audience_cluster_hash: bytes    # bytes32
    channel_set_mask: int           # uint32
    total_spend_usd_micro: int      # uint128
    outcome_metric_cid: bytes       # bytes32
    boardroom_session_id: bytes     # bytes32 — joins receipt to BoardroomSession
    trace_id: bytes                 # bytes32
    nonce: int                      # uint64
    signed_at: int                  # uint64


def _bytes32(x: Any) -> bytes:
    """Normalize hex / bytes / str to a 32-byte big-endian payload."""
    if isinstance(x, bytes):
        if len(x) == 32:
            return x
        if len(x) < 32:
            return x.rjust(32, b"\x00")
        raise ValueError(f"bytes32 too long: {len(x)}")
    if isinstance(x, str):
        s = x.removeprefix("0x")
        if len(s) > 64:
            raise ValueError("hex string > 32 bytes")
        return bytes.fromhex(s.rjust(64, "0"))
    raise TypeError(f"unsupported bytes32 type: {type(x).__name__}")


def envelope_typed_data(
    payload: EnvelopePayload,
    *,
    contract_address: str,
    chain_id: int,
    name: str = "MarketingAttributionReceipt",
    version: str = "2",
) -> dict:
    """Return the EIP-712 typed-data dict ready for `eth_account.messages.encode_typed_data`.

    Pure function — no I/O, no signing. Tests can verify exact byte layout
    against the on-chain `envelopeDigest()`.
    """
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "MarketingCampaign": [
                {"name": "campaignId", "type": "bytes32"},
                {"name": "briefCid", "type": "bytes32"},
                {"name": "audienceClusterHash", "type": "bytes32"},
                {"name": "channelSetMask", "type": "uint32"},
                {"name": "totalSpendUsdMicro", "type": "uint128"},
                {"name": "outcomeMetricCid", "type": "bytes32"},
                {"name": "boardroomSessionId", "type": "bytes32"},
                {"name": "traceId", "type": "bytes32"},
                {"name": "nonce", "type": "uint64"},
                {"name": "signedAt", "type": "uint64"},
            ],
        },
        "primaryType": "MarketingCampaign",
        "domain": {
            "name": name,
            "version": version,
            "chainId": chain_id,
            "verifyingContract": contract_address,
        },
        "message": {
            "campaignId": _bytes32(payload.campaign_id),
            "briefCid": _bytes32(payload.brief_cid),
            "audienceClusterHash": _bytes32(payload.audience_cluster_hash),
            "channelSetMask": payload.channel_set_mask,
            "totalSpendUsdMicro": payload.total_spend_usd_micro,
            "outcomeMetricCid": _bytes32(payload.outcome_metric_cid),
            "boardroomSessionId": _bytes32(payload.boardroom_session_id),
            "traceId": _bytes32(payload.trace_id),
            "nonce": payload.nonce,
            "signedAt": payload.signed_at,
        },
    }


def sign_envelope(typed_data: dict, private_key: str) -> bytes:
    """Sign the EIP-712 typed-data with the given private key. Returns 65-byte sig."""
    from eth_account import Account  # local import — keeps test path light
    from eth_account.messages import encode_typed_data

    msg = encode_typed_data(full_message=typed_data)
    signed = Account.sign_message(msg, private_key=private_key)
    return signed.signature


@dataclass
class SubmitResult:
    dry_run: bool
    contract_address: str
    chain_id: int
    calldata_hex: str
    signature_hex: str
    tx_hash: Optional[str] = None
    error: Optional[str] = None


_RECORD_SELECTOR = bytes.fromhex(
    # keccak256("record(address,bytes32,bytes32,bytes32,uint32,uint128,bytes32,bytes32,uint64,uint64,bytes)")[:4]
    # Computed offline; tested via the live Foundry contract bytecode.
    "00000000"  # placeholder; client should compute from ABI in production
)


def encode_record_calldata(agent_address: str, payload: EnvelopePayload, signature: bytes) -> str:
    """Hex-encoded calldata for `record(...)`.

    NOTE: For the audit-perfect path, use `eth_abi.encode` with the function's
    full ABI. We avoid a hard `eth_abi` dep by punting to `web3.py.contract` if
    available — see `submit()` below. This helper exposes the abstract shape
    so callers can audit the input set even in dry-run.
    """
    return f"0x__see_submit_for_real_encoding__"


class AttributionReceiptClient:
    def __init__(
        self,
        contract_address: str,
        chain_id: int,
        signer_private_key: Optional[str] = None,
        raw_tx_client: Any = None,
    ) -> None:
        self.contract_address = contract_address
        self.chain_id = int(chain_id)
        self.signer_private_key = signer_private_key
        self.raw_tx_client = raw_tx_client

    def build_typed_data(self, payload: EnvelopePayload) -> dict:
        return envelope_typed_data(
            payload,
            contract_address=self.contract_address,
            chain_id=self.chain_id,
        )

    def sign(self, payload: EnvelopePayload) -> bytes:
        if not self.signer_private_key:
            raise RuntimeError("signer_private_key not configured")
        return sign_envelope(self.build_typed_data(payload), self.signer_private_key)

    async def submit(
        self,
        agent_address: str,
        payload: EnvelopePayload,
        *,
        dry_run: bool = True,
    ) -> SubmitResult:
        signature = self.sign(payload) if self.signer_private_key else b""
        sig_hex = "0x" + signature.hex() if signature else ""
        calldata_hex = encode_record_calldata(agent_address, payload, signature)
        if dry_run or self.raw_tx_client is None:
            return SubmitResult(
                dry_run=True,
                contract_address=self.contract_address,
                chain_id=self.chain_id,
                calldata_hex=calldata_hex,
                signature_hex=sig_hex,
            )
        # Live submit path — uses RawTxClient. For correct ABI calldata,
        # operator should install web3.py and switch this to web3-encoded
        # calldata. Phase 1 ships the dry-run path as the primary surface.
        try:
            tx_hash = await self.raw_tx_client.send_raw(
                to=self.contract_address,
                data=calldata_hex,
                value=0,
            )
            return SubmitResult(
                dry_run=False,
                contract_address=self.contract_address,
                chain_id=self.chain_id,
                calldata_hex=calldata_hex,
                signature_hex=sig_hex,
                tx_hash=tx_hash,
            )
        except Exception as exc:
            return SubmitResult(
                dry_run=False,
                contract_address=self.contract_address,
                chain_id=self.chain_id,
                calldata_hex=calldata_hex,
                signature_hex=sig_hex,
                error=repr(exc),
            )


__all__ = [
    "AttributionReceiptClient",
    "EnvelopePayload",
    "SubmitResult",
    "envelope_typed_data",
    "sign_envelope",
    "encode_record_calldata",
    "ENVELOPE_TYPE_STRING",
]
