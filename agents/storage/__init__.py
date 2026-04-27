"""
mindx.storage — IPFS offload + chain anchoring for the memory tier.

The local archive directory was a dead-letter queue. This package promotes
old/low-importance memories to IPFS (Lighthouse + nft.storage) with on-chain
anchoring via the ARC DatasetRegistry (everyday tier) and THOT mint
(curated tier), implementing the "distribute, don't delete" doctrine for
real.

Plan: ~/.claude/plans/whispering-floating-merkle.md
Design contract: docs/KNOWLEDGE_CATALOGUE.md (Phase 1+ catalogue)
"""

from .provider import CID, IPFSProvider, ProviderError

__all__ = ["CID", "IPFSProvider", "ProviderError"]
