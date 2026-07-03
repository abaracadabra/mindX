"""
blockchain.agents — a modular, agnostic expansion that mints mindX agents as
ERC-7857 iNFTs, lists them on AgenticPlace, and binds them to BANKON.

Each blockchain agent is a *class* of sidecar facet files in this directory:
    <name>.agent  <name>.model  <name>.persona
    <name>.walletpublickey  <name>.bankon  <name>.iNFT

The pipeline lives in `agent_factory.BlockchainAgentFactory`. mindX is one
consumer of this module, not its only home.

Spec: docs/blockchain/BLOCKCHAIN_AGENTS.md
"""

from .agent_factory import BlockchainAgentFactory

__all__ = ["BlockchainAgentFactory"]
