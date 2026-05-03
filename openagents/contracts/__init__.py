"""openagents.contracts — generic registry mapping deployed addresses to ABIs.

See `registry.py` for the API. Vendored ABIs live in `abi/`.
"""
from openagents.contracts.registry import OpenAgentsContracts, CATALOG

__all__ = ["OpenAgentsContracts", "CATALOG"]
