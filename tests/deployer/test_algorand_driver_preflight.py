"""Algorand driver preflight against AlgoKit LocalNet (skipif node down)."""

import os

import pytest

from agents.deployer.drivers.algorand_driver import AlgorandDriver
from agents.deployer.manifest import load_manifest

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "sample.deploy")
ALGOD = os.environ.get("ALGOD_LOCALNET_URL", "http://localhost:4001")
MNEMONIC = os.environ.get("ALGORAND_DEPLOYER_MNEMONIC_LOCALNET")


def _localnet_up():
    try:
        from algosdk.v2client import algod

        algod.AlgodClient("a" * 64, ALGOD).suggested_params()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (_localnet_up() and MNEMONIC),
    reason="Algorand LocalNet not up or mnemonic unset (source <(bash scripts/deployer/bootstrap_algorand_localnet.sh))",
)


@pytest.mark.asyncio
async def test_algorand_preflight_passes(monkeypatch):
    monkeypatch.setenv("ALGOD_LOCALNET_URL", ALGOD)
    stage = load_manifest(FIX).stage_for("algorand-localnet")
    checks = await AlgorandDriver().preflight(stage, MNEMONIC)
    by = {c.name: c for c in checks}
    assert by["rpc"].passed, by["rpc"].detail
    assert by["compiled"].passed, by["compiled"].detail
    assert by["balance"].passed, by["balance"].detail
