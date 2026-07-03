"""
End-to-end local deploy through DeployerService (intent -> confirm), exercising
the wallet-auth gate (mocked), per-chain isolation, drivers, and records.

Skipif Anvil + Algorand LocalNet aren't both up with a funded localnet mnemonic.
"""

import os
import urllib.request

import pytest

from agents.deployer import service as svc_mod
from agents.deployer.service import DeployerService

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "sample.deploy")
RPC = os.environ.get("ANVIL_RPC_URL", "http://127.0.0.1:8545")
ALGOD = os.environ.get("ALGOD_LOCALNET_URL", "http://localhost:4001")
MNEMONIC = os.environ.get("ALGORAND_DEPLOYER_MNEMONIC_LOCALNET")

GUARDIAN = "0x9F730F6873102ee648E39b4543dEf776cD8eA182"


def _anvil_up():
    try:
        import json
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}).encode()
        req = urllib.request.Request(RPC, data=body, headers={"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as r:
            return json.load(r).get("result") is not None
    except Exception:
        return False


def _localnet_up():
    try:
        from algosdk.v2client import algod
        algod.AlgodClient("a" * 64, ALGOD).suggested_params()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (_anvil_up() and _localnet_up() and MNEMONIC),
    reason="need Anvil + Algorand LocalNet + localnet mnemonic",
)


class _Ver:
    is_valid = True
    recovered_address = GUARDIAN


@pytest.mark.asyncio
async def test_intent_then_confirm_deploys_both_chains(monkeypatch):
    monkeypatch.setenv("ANVIL_RPC_URL", RPC)
    monkeypatch.setenv("ALGOD_LOCALNET_URL", ALGOD)
    monkeypatch.setenv("ALGORAND_DEPLOYER_MNEMONIC_LOCALNET", MNEMONIC)

    # Mock wallet-auth: valid signature, signer maps to a high-tier participant.
    monkeypatch.setattr(DeployerService, "_verify_signature", lambda self, a, m, s: _Ver())
    monkeypatch.setattr(svc_mod, "map_signer_to_entity", lambda addr: ("guardian_agent_main", 4))

    async def _tier(entity, static):
        return 4
    monkeypatch.setattr(svc_mod, "live_tier", _tier)

    DeployerService._instance = None
    svc = await DeployerService.get_instance()

    intent = await svc.create_intent(
        wallet_address=GUARDIAN, signature="0xsig", message="deploy sample",
        manifest_path=FIX, chain=None)
    assert intent["deployer_of_record"].lower() == GUARDIAN.lower()
    assert len(intent["stages"]) == 2
    # both stages should pass preflight (no broadcast yet)
    for s in intent["stages"]:
        assert s["preflight_ok"], s["preflight"]

    batch = await svc.execute_intent(intent["intent_id"])
    succeeded = set(batch["summary"]["succeeded"])
    assert "anvil-local" in succeeded, batch
    assert "algorand-localnet" in succeeded, batch

    # records have the expected on-chain artifacts
    for st in batch["stages"]:
        if st["chain"] == "anvil-local":
            assert st["record"]["contracts"] and st["record"]["contracts"][0]["address"].startswith("0x")
        if st["chain"] == "algorand-localnet":
            assert st["record"]["apps"] and st["record"]["apps"][0]["app_id"] > 0
