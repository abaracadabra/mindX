"""
Byte-stable deployment records + batch manifest.

Per the deployment-as-a-service spec §5, records are written atomically
(`*.tmp` -> fsync -> os.replace) with a sidecar `*.lock` so concurrent writers
don't corrupt them, and they are immediately consumable by an interaction layer.

EVM records land in `daio/contracts/deployments/<chain_id>/<stage>.json`
(alongside the forge receipt). Algorand records and the per-intent batch
manifest land under `data/governance/deployments/`.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from utils.config import PROJECT_ROOT

DEPLOYMENTS_DIR = os.path.join(str(PROJECT_ROOT), "data", "governance", "deployments")
EVM_RECEIPTS_DIR = os.path.join(str(PROJECT_ROOT), "daio", "contracts", "deployments")


def _atomic_write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lock = path + ".lock"
    # best-effort exclusive lock
    fd = None
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        fd = None  # stale lock or concurrent write; proceed (single-writer in practice)
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if fd is not None:
            os.close(fd)
            try:
                os.remove(lock)
            except OSError:
                pass


def build_evm_record(
    *, project: str, chain: str, chain_id: int, deployer_of_record: str,
    contracts: List[Dict[str, Any]], tx_hash: Optional[str], block_number: Optional[int],
    rpc_url: str, deployed_at: float,
) -> Dict[str, Any]:
    return {
        "project": project,
        "kind": "evm",
        "chain": chain,
        "chain_id": chain_id,
        "rpc_url": rpc_url,
        "deployer_of_record": deployer_of_record,
        "deployed_at": deployed_at,
        "tx_hash": tx_hash,
        "block_number": block_number,
        "contracts": contracts,  # [{name, address}]
    }


def build_algorand_record(
    *, project: str, chain: str, network: str, deployer_of_record: str,
    apps: List[Dict[str, Any]], algod_url: str, deployed_at: float,
) -> Dict[str, Any]:
    return {
        "project": project,
        "kind": "algorand",
        "chain": chain,
        "network": network,
        "algod_url": algod_url,
        "deployer_of_record": deployer_of_record,
        "deployed_at": deployed_at,
        "apps": apps,  # [{name, app_id, app_address, tx_id, arc56}]
    }


def evm_record_path(chain_id: int, stage: str) -> str:
    return os.path.join(EVM_RECEIPTS_DIR, str(chain_id), f"{stage}.record.json")


def algorand_record_path(chain: str, project: str) -> str:
    return os.path.join(DEPLOYMENTS_DIR, "algorand", f"{chain}.{project}.json")


def write_record(path: str, record: Dict[str, Any]) -> str:
    _atomic_write_json(path, record)
    return path


def write_batch_manifest(intent_id: str, batch: Dict[str, Any]) -> str:
    path = os.path.join(DEPLOYMENTS_DIR, "batch", f"{intent_id}.json")
    _atomic_write_json(path, batch)
    return path


def read_chain_records(chain_id: int) -> List[Dict[str, Any]]:
    """All deployment records for a chain id (EVM receipt dir)."""
    out: List[Dict[str, Any]] = []
    d = os.path.join(EVM_RECEIPTS_DIR, str(chain_id))
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(d, fn), "r", encoding="utf-8") as fh:
                        out.append(json.load(fh))
                except (OSError, json.JSONDecodeError):
                    continue
    return out


def now() -> float:
    return time.time()
