"""
agents.deployer — a governed, multi-chain, manifest-driven contract deployer.

Takes both EVM (`.sol` via Foundry) and Algorand (ARC56 via algosdk) contracts
live, with per-chain isolated stages, a two-step intent/confirm gate, and a
participant-tier authorization model anchored to UI wallet authentication. mindX
is one consumer; the deployer is project-agnostic and driven by a `.deploy`
manifest.

Spec: docs/services/contract_deployment_as_a_service.md
"""

from .manifest import DeployManifest, ManifestError, load_manifest
from .service import DeployerError, DeployerService

__all__ = [
    "DeployerService",
    "DeployerError",
    "DeployManifest",
    "ManifestError",
    "load_manifest",
]
