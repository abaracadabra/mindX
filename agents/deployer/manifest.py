"""
`.deploy` manifest — the declarative, project-agnostic deploy descriptor.

A `<project>.deploy` file is JSON (the consumer is this module; the data is
nested per-chain stages). One manifest can target many chains; each stage is an
isolated unit with its own driver, RPC/algod, deployer key, and receipt.

Schema (see agents/deployer/templates/template.deploy for a filled example):

    project              str   (required)
    version              str   (required)
    required_min_tier    str   tier0..tier4 (required)
    required_approvers   [str] entity ids that must co-authorize mainnet
    mainnet_two_step     bool  force the intent/confirm gate even off-mainnet
    stages: [
      { chain, chain_id, driver: foundry|algorand, is_mainnet, rpc_env,
        deployer_entity, gas_budget_usd,
        foundry:  { contracts_root, script, profile, receipt_stage, verify, env{} }
        algorand: { artifacts_root, contracts[], network, algod_env,
                    deployer_mnemonic_env, app_args[] } }
    ]

Exactly one of `foundry`/`algorand` is present per stage, matching `driver`.
`$VAR` values inside `foundry.env` are resolved from process env at run time —
the manifest never stores secrets.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

VALID_TIERS = ("tier0", "tier1", "tier2", "tier3", "tier4")
VALID_DRIVERS = ("foundry", "algorand")


class ManifestError(ValueError):
    """Raised when a `.deploy` manifest is missing fields or malformed."""


@dataclass
class Stage:
    chain: str
    chain_id: int
    driver: str
    rpc_env: str
    deployer_entity: str
    is_mainnet: bool = False
    gas_budget_usd: float = 0.0
    foundry: Optional[Dict[str, Any]] = None
    algorand: Optional[Dict[str, Any]] = None

    @property
    def config(self) -> Dict[str, Any]:
        """The driver-specific config block."""
        return (self.foundry if self.driver == "foundry" else self.algorand) or {}


@dataclass
class DeployManifest:
    project: str
    version: str
    required_min_tier: str
    path: str
    required_approvers: List[str] = field(default_factory=list)
    mainnet_two_step: bool = True
    stages: List[Stage] = field(default_factory=list)

    def stage_for(self, chain: str) -> Optional[Stage]:
        for s in self.stages:
            if s.chain == chain:
                return s
        return None

    def selected_stages(self, chain: Optional[str]) -> List[Stage]:
        """All stages, or just the one matching `chain`."""
        if chain is None:
            return list(self.stages)
        s = self.stage_for(chain)
        if s is None:
            raise ManifestError(f"manifest '{self.project}' has no stage for chain '{chain}'")
        return [s]

    def manifest_hash(self) -> str:
        """Stable hash of the manifest content (for challenge messages)."""
        import hashlib

        try:
            with open(self.path, "rb") as fh:
                return hashlib.sha256(fh.read()).hexdigest()
        except OSError:
            return hashlib.sha256(self.project.encode()).hexdigest()


def _require(d: Dict[str, Any], key: str, ctx: str) -> Any:
    if key not in d or d[key] in (None, ""):
        raise ManifestError(f"{ctx}: missing required field '{key}'")
    return d[key]


def load_manifest(path: str) -> DeployManifest:
    """Load + validate a `.deploy` manifest from disk."""
    if not os.path.isabs(path):
        from utils.config import PROJECT_ROOT

        path = os.path.join(str(PROJECT_ROOT), path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError as e:
        raise ManifestError(f"manifest not found: {path}") from e
    except json.JSONDecodeError as e:
        raise ManifestError(f"manifest is not valid JSON: {e}") from e

    project = _require(raw, "project", "manifest")
    version = _require(raw, "version", "manifest")
    min_tier = _require(raw, "required_min_tier", "manifest")
    if min_tier not in VALID_TIERS:
        raise ManifestError(f"required_min_tier must be one of {VALID_TIERS}, got '{min_tier}'")

    stages_raw = raw.get("stages") or []
    if not stages_raw:
        raise ManifestError("manifest has no stages")

    stages: List[Stage] = []
    seen_chains = set()
    for i, sr in enumerate(stages_raw):
        ctx = f"stage[{i}]"
        chain = _require(sr, "chain", ctx)
        if chain in seen_chains:
            raise ManifestError(f"duplicate chain '{chain}' in stages")
        seen_chains.add(chain)
        driver = _require(sr, "driver", ctx)
        if driver not in VALID_DRIVERS:
            raise ManifestError(f"{ctx}: driver must be one of {VALID_DRIVERS}, got '{driver}'")
        # exactly-one driver block
        has_f, has_a = bool(sr.get("foundry")), bool(sr.get("algorand"))
        if driver == "foundry" and not has_f:
            raise ManifestError(f"{ctx}: driver=foundry but no 'foundry' block")
        if driver == "algorand" and not has_a:
            raise ManifestError(f"{ctx}: driver=algorand but no 'algorand' block")
        if has_f and has_a:
            raise ManifestError(f"{ctx}: stage must have exactly one of foundry/algorand")

        stages.append(Stage(
            chain=chain,
            chain_id=int(_require(sr, "chain_id", ctx)),
            driver=driver,
            rpc_env=_require(sr, "rpc_env", ctx),
            deployer_entity=_require(sr, "deployer_entity", ctx),
            is_mainnet=bool(sr.get("is_mainnet", False)),
            gas_budget_usd=float(sr.get("gas_budget_usd", 0.0)),
            foundry=sr.get("foundry"),
            algorand=sr.get("algorand"),
        ))

    return DeployManifest(
        project=project,
        version=version,
        required_min_tier=min_tier,
        path=path,
        required_approvers=list(raw.get("required_approvers", [])),
        mainnet_two_step=bool(raw.get("mainnet_two_step", True)),
        stages=stages,
    )


def resolve_env_map(env: Dict[str, Any]) -> Dict[str, str]:
    """Resolve `$VAR` references in a manifest env block from process env.

    Non-`$` values pass through verbatim. A `$VAR` with no env value resolves to
    empty string (the driver/preflight surfaces the consequence).
    """
    out: Dict[str, str] = {}
    for k, v in (env or {}).items():
        sv = str(v)
        if sv.startswith("$"):
            out[k] = os.environ.get(sv[1:], "")
        else:
            out[k] = sv
    return out
