"""Foundry driver preflight against Anvil (skipif node down). No broadcast."""

import os
import urllib.request

import pytest

from agents.deployer.drivers.foundry_driver import FoundryDriver
from agents.deployer.manifest import load_manifest

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "sample.deploy")
RPC = os.environ.get("ANVIL_RPC_URL", "http://127.0.0.1:8545")
ANVIL_PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def _anvil_up():
    try:
        import json
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}).encode()
        req = urllib.request.Request(RPC, data=body, headers={"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as r:
            return json.load(r).get("result") is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _anvil_up(), reason="Anvil not up (bash scripts/deployer/bootstrap_evm.sh)")


@pytest.mark.asyncio
async def test_foundry_preflight_passes(monkeypatch):
    monkeypatch.setenv("ANVIL_RPC_URL", RPC)
    stage = load_manifest(FIX).stage_for("anvil-local")
    checks = await FoundryDriver().preflight(stage, ANVIL_PK)
    by = {c.name: c for c in checks}
    assert by["rpc"].passed, by["rpc"].detail
    assert by["compiled"].passed, by["compiled"].detail
    assert by["balance"].passed, by["balance"].detail
