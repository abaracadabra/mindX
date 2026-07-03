"""gitmind — mindX's self-contained git state monitor + multi-source backup/rollback.

Monitors the repo's git state, records rollbacks and self-rollbacks to an
append-only ledger, snapshots the repo as git bundles, and replicates those
bundles across variable backup sources (local filesystem, IPFS via Lighthouse,
Arweave). Self-contained: only the standard library + git + the existing
agents.storage providers (lazy). Never raises into the caller — every op
returns a status dict.
"""
from .gitmind import GitMind, get_gitmind

__all__ = ["GitMind", "get_gitmind"]
