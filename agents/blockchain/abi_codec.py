"""
Minimal ABI codec for the blockchain.agents mint pipeline.

Mirrors the selector approach already used by `agents/storage/anchor.py`
(keccak256 over the canonical function signature) but delegates the messy
tuple/dynamic argument packing to `eth_abi.encode` instead of hand-packing
offsets. `eth_abi` (5.x) is present in the venv alongside `eth_account`.

No `web3.py` dependency on the call path — calldata is produced as a hex
string ready for `RawTxClient.send_tx(data=...)`.
"""

from __future__ import annotations

from typing import Any, Sequence


def keccak256(data: bytes) -> bytes:
    """keccak256 digest. Same primitive used by anchor.py (pycryptodome)."""
    from Crypto.Hash import keccak  # type: ignore[import-not-found]

    k = keccak.new(digest_bits=256)
    k.update(data)
    return k.digest()


def selector(signature: str) -> bytes:
    """4-byte function selector for a canonical signature.

    e.g. selector("registerDataset(bytes32,string)") == bytes.fromhex("f1783fb8")
    """
    return keccak256(signature.encode("utf-8"))[:4]


def event_topic(signature: str) -> str:
    """32-byte event topic (topic0) for a canonical event signature, 0x-prefixed."""
    return "0x" + keccak256(signature.encode("utf-8")).hex()


def encode_call(signature: str, types: Sequence[str], args: Sequence[Any]) -> str:
    """ABI-encode a full call: 0x || selector(sig) || encode(types, args).

    `signature` is the canonical function signature (no spaces, e.g.
    "mintAgent(address,bytes32,string,bytes32,uint32,uint8,bytes32,string)").
    `types` is the matching ordered list of solidity types for eth_abi.
    """
    from eth_abi import encode as abi_encode  # type: ignore[import-not-found]

    body = abi_encode(list(types), list(args))
    return "0x" + selector(signature).hex() + body.hex()


def _topics(log: dict) -> list[str]:
    return log.get("topics", []) or []


def parse_event_uint(receipt: dict, event_signature: str, topic_index: int) -> int | None:
    """Return an indexed uint topic from the first matching log in a receipt.

    `topic_index` is 1-based into the indexed topics (topics[0] is the event
    signature hash). For AgentMinted(uint256 indexed tokenId, ...) the tokenId
    is topic_index=1.
    """
    want = event_topic(event_signature).lower()
    for log in receipt.get("logs", []) or []:
        topics = _topics(log)
        if topics and topics[0].lower() == want and len(topics) > topic_index:
            return int(topics[topic_index], 16)
    return None


# AgentMinted(uint256 indexed tokenId, bytes32 indexed contentRoot, uint32 dimensions, address indexed owner)
AGENT_MINTED_SIG = "AgentMinted(uint256,bytes32,uint32,address)"


def parse_minted_token_id(receipt: dict) -> int | None:
    """Extract the minted tokenId from an iNFT_7857 mintAgent receipt."""
    return parse_event_uint(receipt, AGENT_MINTED_SIG, 1)
