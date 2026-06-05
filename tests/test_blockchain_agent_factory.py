"""
Unit tests for the blockchain.agents factory (offline, no broadcast).

Covers:
  * ABI selector calibration against anchor.py's known-good value (f1783fb8)
  * a dry-run mint: wallet + persona + IPFS-local-fallback bundling that writes
    all six sidecar facets and never constructs a RawTxClient.
"""

import os
from unittest import mock

import pytest

from agents.blockchain import abi_codec, facets
from agents.blockchain.agent_factory import (
    BlockchainAgentFactory,
    MINT_AGENT_SIG,
    MINT_AGENT_TYPES,
)

TEST_NAME = "pytest-dryrun-agent"
TEST_ADDR = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"


@pytest.fixture
def cleanup_facets():
    yield
    for ext in facets.FACET_EXTS:
        p = facets.facet_path(TEST_NAME, ext)
        if os.path.exists(p):
            os.remove(p)


def test_selector_calibration():
    # Same primitive and value used by agents/storage/anchor.py
    assert abi_codec.selector("registerDataset(bytes32,string)").hex() == "f1783fb8"


def test_encode_call_shape():
    data = abi_codec.encode_call(
        MINT_AGENT_SIG, MINT_AGENT_TYPES,
        [TEST_ADDR, b"\x11" * 32, "ipfs://cid", b"\x22" * 32, 768, 1, b"\x33" * 32, "ipfs://cid"],
    )
    assert data.startswith("0x")
    # selector(4) + 8 head words (32 each) + 2 dynamic strings -> well over 8 words
    assert len(bytes.fromhex(data[2:])) >= 4 + 32 * 8


def test_parse_minted_token_id():
    topic0 = abi_codec.event_topic(abi_codec.AGENT_MINTED_SIG)
    receipt = {"logs": [{"topics": [topic0, "0x" + (42).to_bytes(32, "big").hex(),
                                    "0x" + "0" * 64, "0x" + "0" * 64]}]}
    assert abi_codec.parse_minted_token_id(receipt) == 42


@pytest.mark.asyncio
async def test_dry_run_mint_writes_facets_no_broadcast(cleanup_facets):
    BlockchainAgentFactory._instance = None
    factory = await BlockchainAgentFactory.get_instance()

    # Mock the wallet so no real key/vault is created.
    idm = mock.AsyncMock()
    idm.create_new_wallet = mock.AsyncMock(return_value=(TEST_ADDR, "MINDX_WALLET_TEST"))

    # A RawTxClient that explodes if constructed — proves no broadcast path.
    def _boom(*a, **k):
        raise AssertionError("RawTxClient must not be constructed in dry_run")

    with mock.patch("agents.core.id_manager_agent.IDManagerAgent.get_instance",
                    mock.AsyncMock(return_value=idm)), \
         mock.patch("agents.storage.raw_tx.RawTxClient", _boom):
        result = await factory.mint_agent(TEST_NAME, dry_run=True)

    assert result["status"] == "dry_run"
    assert result["agent_wallet"] == TEST_ADDR
    # storageURI is the local content-address fallback when no IPFS keys present.
    assert result["storageURI"].startswith(("local://", "ipfs://"))

    present = facets.existing_facets(TEST_NAME)
    for ext in facets.FACET_EXTS:
        assert present[ext], f"facet {ext} should have been written"

    # walletpublickey facet holds the address; iNFT facet seeded but unminted.
    assert facets.read_wallet(TEST_NAME) == TEST_ADDR
    inft = facets.read_json_facet(TEST_NAME, "iNFT")
    assert inft["status"] == "dry_run"
    assert inft["tokenId"] is None
    assert inft["contentRoot"].startswith("0x") and inft["contentRoot"] != "0x" + "0" * 64
