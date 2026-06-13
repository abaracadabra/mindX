"""
Agent Mint Service — free address-as-label `<addr>.bankon.eth` for mindX agents.

Wraps `BankonSubnameRegistrar.registerAgentSubname(agent, expiry, meta)` —
the new role-gated free path added to v1. Only callers holding
`MINDX_AGENT_MINTER_ROLE` on the registrar can mint; the existing free
(reputation-gated) and paid (EIP-712 voucher) paths remain unchanged.

Usage:

    from openagents.ens.agent_mint_service import AgentMintService, AgentMetadata

    svc = AgentMintService(
        registrar_addr="0x...",          # deployed BankonSubnameRegistrar
        rpc_url="https://eth-sepolia...", # or 0G Galileo (after BANKON deploys)
        minter_pk="0x...",                # holds MINDX_AGENT_MINTER_ROLE
    )
    receipt = await svc.mint_agent_subname(
        agent_addr="0xCC5d...eF01",
        meta=AgentMetadata(
            agentURI="ipfs://Qm.../agent.json",
            mindxEndpoint="https://mindx.pythai.net/agent/cfo_finance",
            x402Endpoint="https://mindx.pythai.net/p2p/keeperhub",
            baseAddress=BASE_L2_AGENT_ADDR,
            algoAddr=b"",
        ),
    )
    # receipt = {"node": "0x...", "label": "cc5d...ef01", "tx_hash": "0x..."}
    # The agent's ENS subname is now `<label>.bankon.eth` resolving to agent_addr.

Free for the agent. The role-holder pays gas for the registration tx.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from eth_account import Account
from web3 import Web3

logger = logging.getLogger(__name__)


@dataclass
class AgentMetadata:
    """Mirrors the Solidity AgentMetadata struct."""
    agentURI: str         # IPFS / 0G Storage pointer to the agent manifest
    mindxEndpoint: str    # HTTPS endpoint where the agent answers (optional)
    x402Endpoint: str     # x402 / KeeperHub paid endpoint (optional)
    baseAddress: str      # L2 settlement address (Base / Tempo)
    algoAddr: bytes       # Algorand address bytes (optional, b"" if none)


# Minimal ABI fragments we need
_REGISTRAR_ABI = [
    {
        "type": "function",
        "name": "registerAgentSubname",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "agent", "type": "address"},
            {"name": "expiry", "type": "uint64"},
            {
                "name": "meta",
                "type": "tuple",
                "components": [
                    {"name": "agentURI", "type": "string"},
                    {"name": "mindxEndpoint", "type": "string"},
                    {"name": "x402Endpoint", "type": "string"},
                    {"name": "baseAddress", "type": "address"},
                    {"name": "algoAddr", "type": "bytes"},
                ],
            },
        ],
        "outputs": [
            {"name": "node", "type": "bytes32"},
            {"name": "agentId", "type": "uint256"},
            {"name": "label", "type": "string"},
        ],
    },
    {
        "type": "function",
        "name": "MINDX_AGENT_MINTER_ROLE",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "bytes32"}],
    },
    {
        "type": "function",
        "name": "hasRole",
        "stateMutability": "view",
        "inputs": [
            {"name": "role", "type": "bytes32"},
            {"name": "account", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "type": "function",
        "name": "ownerOfLabel",
        "stateMutability": "view",
        "inputs": [{"name": "node", "type": "bytes32"}],
        "outputs": [{"name": "", "type": "address"}],
    },
]


class AgentMintNotAuthorized(Exception):
    """Raised when the configured minter does not hold MINDX_AGENT_MINTER_ROLE."""


class AgentMintService:
    """Mints `<agent_addr>.bankon.eth` for mindX agents, free.

    The mint service holder is expected to verify off-chain that the agent
    is a real mindX agent (e.g. registered in production_registry.json or
    holding a Cabinet wallet) before calling. The smart contract trusts
    the role-holder to make that judgment.
    """

    DEFAULT_EXPIRY_DAYS = 365  # 1 year, capped by parent expiry on chain

    def __init__(
        self,
        registrar_addr: str,
        rpc_url: str,
        minter_pk: str,
        chain_id: Optional[int] = None,
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise RuntimeError(f"cannot reach RPC at {rpc_url}")
        self.chain_id = chain_id or self.w3.eth.chain_id
        self.minter = Account.from_key(minter_pk)
        self.registrar = self.w3.eth.contract(
            address=Web3.to_checksum_address(registrar_addr),
            abi=_REGISTRAR_ABI,
        )

    def is_authorized(self) -> bool:
        """True iff the configured minter holds MINDX_AGENT_MINTER_ROLE."""
        role = self.registrar.functions.MINDX_AGENT_MINTER_ROLE().call()
        return self.registrar.functions.hasRole(role, self.minter.address).call()

    def assert_authorized(self):
        if not self.is_authorized():
            raise AgentMintNotAuthorized(
                f"minter {self.minter.address} does not hold MINDX_AGENT_MINTER_ROLE "
                f"on {self.registrar.address}. Have the registrar admin grant the role."
            )

    async def mint_agent_subname(
        self,
        agent_addr: str,
        meta: AgentMetadata,
        expiry_days: Optional[int] = None,
    ) -> dict:
        """Mint `<agent_addr>.bankon.eth` for the agent. Returns dict with
        {node, label, tx_hash, agent_id}.

        agent_addr: the wallet address that will own the subname.
        meta:       AgentMetadata struct (records to write on the resolver).
        expiry_days: registration validity in days (default: 365).

        Free for the agent. The minter pays gas (~3.5M).
        """
        self.assert_authorized()
        agent_addr = Web3.to_checksum_address(agent_addr)

        latest = self.w3.eth.get_block("latest")
        expiry = latest["timestamp"] + (expiry_days or self.DEFAULT_EXPIRY_DAYS) * 86400

        meta_tuple = (
            meta.agentURI,
            meta.mindxEndpoint,
            meta.x402Endpoint,
            Web3.to_checksum_address(meta.baseAddress) if meta.baseAddress else "0x0000000000000000000000000000000000000000",
            meta.algoAddr or b"",
        )

        nonce = self.w3.eth.get_transaction_count(self.minter.address)
        gas_price = self.w3.eth.gas_price
        tx = self.registrar.functions.registerAgentSubname(
            agent_addr, expiry, meta_tuple
        ).build_transaction({
            "from": self.minter.address,
            "nonce": nonce,
            "gas": 4_000_000,
            "gasPrice": gas_price,
            "chainId": self.chain_id,
        })
        signed = self.minter.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt["status"] != 1:
            raise RuntimeError(f"registerAgentSubname reverted: tx {tx_hash.hex()}")

        # Extract node + label from the SubnameRegistered event
        # (event signature: event SubnameRegistered(bytes32 indexed node, string label, ...))
        # Or just compute the label deterministically — it's lowercase hex of agent_addr.
        label = agent_addr[2:].lower()  # strip 0x, lowercase
        node_hash = self.w3.solidity_keccak(
            ["bytes32", "bytes32"],
            [
                self.registrar.functions.parentNode().call() if hasattr(self.registrar.functions, "parentNode") else b"\x00" * 32,
                self.w3.solidity_keccak(["string"], [label]),
            ],
        )

        logger.info(
            "minted %s.bankon.eth → %s (tx %s, agent_addr %s)",
            label, agent_addr, tx_hash.hex(), agent_addr,
        )
        return {
            "node": "0x" + node_hash.hex() if not node_hash.hex().startswith("0x") else node_hash.hex(),
            "label": label,
            "subname": f"{label}.bankon.eth",
            "agent_addr": agent_addr,
            "tx_hash": tx_hash.hex(),
            "block": receipt["blockNumber"],
            "gas_used": receipt["gasUsed"],
        }


# ─── CLI for quick mint-from-shell ───────────────────────────────────


def _cli():
    import argparse
    import asyncio
    import os

    parser = argparse.ArgumentParser(description="Mint <addr>.bankon.eth for a mindX agent.")
    parser.add_argument("--agent", required=True, help="Agent wallet address (0x...)")
    parser.add_argument("--registrar", default=os.environ.get("BANKON_REGISTRAR_ADDR"),
                        help="Deployed BankonSubnameRegistrar (env: BANKON_REGISTRAR_ADDR)")
    parser.add_argument("--rpc", default=os.environ.get("ENS_RPC_URL"),
                        help="EVM RPC URL (env: ENS_RPC_URL)")
    parser.add_argument("--minter-pk", default=os.environ.get("BANKON_MINTER_PK"),
                        help="Minter private key (env: BANKON_MINTER_PK)")
    parser.add_argument("--agent-uri", default="", help="ipfs:// or 0g:// URI for the agent manifest")
    parser.add_argument("--mindx-endpoint", default="", help="HTTPS endpoint where agent answers")
    parser.add_argument("--days", type=int, default=365, help="Registration validity (default 365)")
    args = parser.parse_args()

    for name, val in [("registrar", args.registrar), ("rpc", args.rpc), ("minter-pk", args.minter_pk)]:
        if not val:
            raise SystemExit(f"--{name} (or env) is required")

    svc = AgentMintService(args.registrar, args.rpc, args.minter_pk)
    if not svc.is_authorized():
        raise SystemExit(f"minter {svc.minter.address} does not hold MINDX_AGENT_MINTER_ROLE")

    meta = AgentMetadata(
        agentURI=args.agent_uri,
        mindxEndpoint=args.mindx_endpoint,
        x402Endpoint="",
        baseAddress="",
        algoAddr=b"",
    )
    result = asyncio.run(svc.mint_agent_subname(args.agent, meta, args.days))
    print(f"minted: {result['subname']}")
    print(f"  agent: {result['agent_addr']}")
    print(f"  node:  {result['node']}")
    print(f"  tx:    {result['tx_hash']}")
    print(f"  gas:   {result['gas_used']}")


if __name__ == "__main__":
    _cli()
