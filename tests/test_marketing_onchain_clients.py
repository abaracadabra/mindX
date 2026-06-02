"""Smoke tests for the on-chain Python clients (mocked; no live RPC)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.marketing.onchain.agent_registry_client import (
    AgentRegistryClient,
    CAP_ATTEST_CAMPAIGN,
    CAP_GOVERN,
    CAP_ORCHESTRATE,
)
from agents.marketing.onchain.attribution_receipt_client import (
    AttributionReceiptClient,
    EnvelopePayload,
    envelope_typed_data,
)
from agents.marketing.onchain.bankon_subname_client import BankonSubnameClient
from agents.marketing.onchain.censura_client import CensuraClient
from agents.marketing.onchain.conclave_client import derive_session_anchor
from agents.marketing.onchain.inft_mint_client import INFT7857Client, MintPayload
from agents.marketing.onchain.tessera_client import TesseraClient


def test_agent_registry_capability_bitmap_combines():
    async def run():
        c = AgentRegistryClient(contract_address="0xabc", chain_id=8453)
        reg = await c.register(
            agent_address="0xagent",
            ens_subname="marketinga.bankon.eth",
            capabilities=[CAP_ORCHESTRATE, CAP_GOVERN, CAP_ATTEST_CAMPAIGN],
        )
        assert reg.capability_bitmap == (CAP_ORCHESTRATE | CAP_GOVERN | CAP_ATTEST_CAMPAIGN)
        assert reg.dry_run is True
        assert reg.ens_subname == "marketinga.bankon.eth"

    asyncio.run(run())


def test_attribution_typed_data_shape_matches_solidity():
    payload = EnvelopePayload(
        campaign_id=b"\x01" * 32,
        brief_cid=b"\x02" * 32,
        audience_cluster_hash=b"\x03" * 32,
        channel_set_mask=0x07,
        total_spend_usd_micro=250_000_000,
        outcome_metric_cid=b"\x04" * 32,
        boardroom_session_id=b"\x06" * 32,
        trace_id=b"\x05" * 32,
        nonce=0,
        signed_at=1_700_000_000,
    )
    td = envelope_typed_data(
        payload, contract_address="0x" + "ab" * 20, chain_id=8453
    )
    assert td["primaryType"] == "MarketingCampaign"
    assert td["domain"]["name"] == "MarketingAttributionReceipt"
    assert td["domain"]["version"] == "2", "EIP-712 version must be bumped to 2 with boardroomSessionId"
    assert td["domain"]["chainId"] == 8453
    types = td["types"]["MarketingCampaign"]
    expected = [
        ("campaignId", "bytes32"),
        ("briefCid", "bytes32"),
        ("audienceClusterHash", "bytes32"),
        ("channelSetMask", "uint32"),
        ("totalSpendUsdMicro", "uint128"),
        ("outcomeMetricCid", "bytes32"),
        ("boardroomSessionId", "bytes32"),
        ("traceId", "bytes32"),
        ("nonce", "uint64"),
        ("signedAt", "uint64"),
    ]
    actual = [(t["name"], t["type"]) for t in types]
    assert actual == expected, f"struct mismatch: {actual}"
    # boardroomSessionId must reach the message body
    assert td["message"]["boardroomSessionId"] == b"\x06" * 32


def test_attribution_client_dry_run_returns_calldata_handle():
    async def run():
        c = AttributionReceiptClient(
            contract_address="0xdef",
            chain_id=8453,
            signer_private_key=None,
        )
        payload = EnvelopePayload(
            campaign_id=b"\x01" * 32,
            brief_cid=b"\x02" * 32,
            audience_cluster_hash=b"\x03" * 32,
            channel_set_mask=0x07,
            total_spend_usd_micro=0,
            outcome_metric_cid=b"\x04" * 32,
            boardroom_session_id=b"\x06" * 32,
            trace_id=b"\x05" * 32,
            nonce=0,
            signed_at=1,
        )
        res = await c.submit("0xagent", payload, dry_run=True)
        assert res.dry_run is True
        assert res.contract_address == "0xdef"
        assert res.chain_id == 8453
        assert res.tx_hash is None

    asyncio.run(run())


def test_tessera_attest_returns_deterministic_credential_id():
    c = TesseraClient(contract_address="0xt", chain_id=8453)
    a1 = c.attest("0xagent", "trace-1", {"action": "draft"})
    a2 = c.attest("0xagent", "trace-1", {"action": "draft"})
    assert a1.credential_id == a2.credential_id
    a3 = c.attest("0xagent", "trace-2", {"action": "draft"})
    assert a3.credential_id != a1.credential_id


def test_censura_floor_evaluation():
    async def run():
        class _View:
            async def read_uint(self, name, *args):
                return 30  # below default floor 50

        c = CensuraClient(contract_address="0xc", chain_id=8453, floor=50, web3_view=_View())
        v = await c.evaluate("0xagent")
        assert v.faded is True
        assert v.score == 30

    asyncio.run(run())


def test_conclave_session_anchor_is_deterministic():
    a1 = derive_session_anchor("c-1", "approved")
    a2 = derive_session_anchor("c-1", "approved")
    assert a1.conclave_id == a2.conclave_id
    assert a1.session_id == a2.session_id
    assert a1.motion_id == a2.motion_id
    assert a1.resolution_hash == a2.resolution_hash
    a3 = derive_session_anchor("c-1", "rejected")
    assert a3.motion_id != a1.motion_id


def test_inft_mint_dry_run_returns_payload_intact():
    async def run():
        c = INFT7857Client(contract_address="0xi", chain_id=8453)
        p = MintPayload(
            agent_address="0xagent",
            did="did:pythai:marketinga",
            ens_subname="marketinga.bankon.eth",
            metadata_uri="ipfs://x",
        )
        r = await c.mint(p, dry_run=True)
        assert r.dry_run is True
        assert r.tx_hash is None
        assert r.payload.did == "did:pythai:marketinga"

    asyncio.run(run())


def test_bankon_subname_default_plan_includes_all_five_children():
    c = BankonSubnameClient(registrar_address="0xr", chain_id=1)
    plan = c.plan()
    assert plan.parent == "marketinga.bankon.eth"
    expected = {
        "content.marketinga.bankon.eth",
        "experimentation.marketinga.bankon.eth",
        "distribution.marketinga.bankon.eth",
        "reporting.marketinga.bankon.eth",
        "governance.marketinga.bankon.eth",
    }
    assert set(plan.children) == expected
