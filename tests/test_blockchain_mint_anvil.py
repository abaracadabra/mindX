"""
Live integration test for the blockchain.agents mint pipeline against Anvil.

Skipped unless:
  * an Ethereum JSON-RPC answers on $BLOCKCHAIN_RPC_URL (default 127.0.0.1:8545), and
  * Tier-1 is deployed for chain 1337 (iNFT_7857 address resolvable via
    data/config/blockchain_addresses.json or the forge tier1.json receipt).

Bring both up with:  bash scripts/blockchain/bootstrap_anvil.sh

Asserts a real mint: receipt status == 1, a positive tokenId, the iNFT facet is
populated, and ownerOf(tokenId) == the minter (custody in v1).
"""

import asyncio
import json
import os
import urllib.request

import pytest

from agents.blockchain import abi_codec, contracts, facets
from agents.blockchain.agent_factory import BlockchainAgentFactory

RPC_URL = os.environ.get("BLOCKCHAIN_RPC_URL", "http://127.0.0.1:8545")
CHAIN_ID = int(os.environ.get("BLOCKCHAIN_CHAIN_ID", "1337"))
TEST_NAME = "pytest-anvil-agent"


def _rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(RPC_URL, data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=2) as resp:
        return json.load(resp).get("result")


def _anvil_up():
    try:
        return _rpc("eth_blockNumber", []) is not None
    except Exception:
        return False


def _tier1_deployed():
    try:
        return contracts.load_contracts(CHAIN_ID, RPC_URL).mintable
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (_anvil_up() and _tier1_deployed()),
    reason="Anvil not up or Tier1 not deployed — run scripts/blockchain/bootstrap_anvil.sh",
)


@pytest.fixture
def cleanup_facets():
    yield
    for ext in facets.FACET_EXTS:
        p = facets.facet_path(TEST_NAME, ext)
        if os.path.exists(p):
            os.remove(p)


@pytest.mark.asyncio
async def test_live_mint(cleanup_facets):
    BlockchainAgentFactory._instance = None
    factory = await BlockchainAgentFactory.get_instance()
    result = await factory.mint_agent(TEST_NAME, dry_run=False, chain_id=CHAIN_ID, rpc_url=RPC_URL)

    assert result["status"] == "minted", result
    token_id = result["tokenId"]
    assert isinstance(token_id, int) and token_id > 0

    inft = facets.read_json_facet(TEST_NAME, "iNFT")
    assert inft["status"] == "minted"
    assert inft["tokenId"] == token_id
    assert inft["tx_hash"]

    # ownerOf(tokenId) == minter custody (v1)
    cc = contracts.load_contracts(CHAIN_ID, RPC_URL)
    calldata = abi_codec.encode_call("ownerOf(uint256)", ["uint256"], [token_id])
    owner_hex = _rpc("eth_call", [{"to": cc.inft7857, "data": calldata}, "latest"])
    owner = "0x" + owner_hex[-40:]
    assert owner.lower() == result["owner_custody"].lower()
