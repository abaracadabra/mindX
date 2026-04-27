# agents/storage/agent_workspace_pruner.py
"""
Orphan-tier pruner — handles `data/memory/agent_workspaces/{agent}/process_traces/process_trace.jsonl`.

Per the audit at `docs/MEMORY_AUDIT_2026_04_27.md` (gap 1): this path is
written by `memory_agent.log_process` and read by **nobody** in the codebase.
On the production VPS it holds 20+ GB, almost all in one agent (mastermind).

Per the policy at `docs/memory_tiers.md`:
    rotate_at_bytes:    100 MB    → freeze the file as .{N}.jsonl, start fresh
    archive_after_days: 30        → gzip + move rotated file to memory/archive/
    delete_after_days:  90        → delete archived file IFF it's been
                                    offloaded to IPFS (CID present)

All defaults are conservative: dry_run=True, MINDX_WORKSPACE_PRUNE_DISABLE=1
env disables the whole module, archive-not-delete unless the IPFS confirmation
exists.
"""

from __future__ import annotations

import gzip
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

try:
    from utils.logging_config import get_logger
    from utils.config import PROJECT_ROOT
except ImportError:
    import logging
    def get_logger(name): return logging.getLogger(name)
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

logger = get_logger(__name__)

DEFAULT_ROTATE_AT_BYTES   = 100 * 1024 * 1024     # 100 MB
DEFAULT_ARCHIVE_AFTER_DAYS = 30
DEFAULT_DELETE_AFTER_DAYS  = 90


def _file_size(p: Path) -> int:
    try:
        return p.stat().st_size if p.is_file() else 0
    except OSError:
        return 0


def _file_age_days(p: Path) -> float:
    try:
        return (time.time() - p.stat().st_mtime) / 86400.0
    except OSError:
        return 0.0


def _next_rotation_index(traces_dir: Path) -> int:
    """Find the highest .{N}.jsonl suffix and return N+1."""
    n = 0
    try:
        for f in traces_dir.iterdir():
            if not f.is_file():
                continue
            name = f.name
            if name.startswith("process_trace.") and name.endswith(".jsonl"):
                # process_trace.{N}.jsonl or process_trace.{N}.jsonl.gz
                middle = name[len("process_trace."):-len(".jsonl")]
                if middle.isdigit():
                    n = max(n, int(middle))
    except OSError:
        pass
    return n + 1


async def prune_workspace_traces(
    project_root: Path = None,
    rotate_at_bytes:    int = DEFAULT_ROTATE_AT_BYTES,
    archive_after_days: int = DEFAULT_ARCHIVE_AFTER_DAYS,
    delete_after_days:  int = DEFAULT_DELETE_AFTER_DAYS,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Apply the three-stage policy to every agent_workspaces/*/process_traces/.

    Returns a per-agent breakdown with three actionable counters:
        rotated   — live .jsonl froze to .{N}.jsonl (live file > rotate_at_bytes)
        archived  — rotated .{N}.jsonl gzipped + moved to archive
        deleted   — archived .gz files removed (only when IPFS CID confirmed
                    via pgvector AND age ≥ delete_after_days)

    Conservative defaults: dry_run=True, MINDX_WORKSPACE_PRUNE_DISABLE=1 env
    disables, deletes only when both the age cliff AND the IPFS confirmation
    are met (offload-then-delete invariant).
    """
    if os.environ.get("MINDX_WORKSPACE_PRUNE_DISABLE", "").lower() in ("1", "true", "yes"):
        return {"status": "disabled", "via": "MINDX_WORKSPACE_PRUNE_DISABLE", "dry_run": dry_run}

    root = project_root or PROJECT_ROOT
    workspaces_root = Path(root) / "data" / "memory" / "agent_workspaces"
    archive_root    = Path(root) / "data" / "memory" / "archive"

    if not workspaces_root.exists():
        return {"status": "no_workspaces_dir", "dry_run": dry_run}

    per_agent: Dict[str, Dict[str, Any]] = {}
    totals = {"rotated": 0, "archived": 0, "deleted": 0,
              "would_rotate_bytes": 0, "would_archive_bytes": 0, "would_delete_bytes": 0,
              "skipped_no_cid": 0}

    for agent_dir in sorted(workspaces_root.iterdir()):
        if not agent_dir.is_dir():
            continue

        # The actual file layout (verified on prod 2026-04-27):
        #   agent_workspaces/{agent}/process_trace.jsonl    ← live file (19.5 GB on mastermind)
        #   agent_workspaces/{agent}/process_traces/        ← empty subdir (legacy)
        # Earlier code assumed process_traces/process_trace.jsonl which was wrong.
        # Use the agent dir itself as the traces dir; rotated and archived
        # files (.{N}.jsonl, .{N}.{date}.jsonl.gz) sit alongside.
        traces_dir = agent_dir

        agent_id = agent_dir.name
        agent_state = {
            "rotated":  [], "archived": [], "deleted": [],
            "live_bytes": 0, "rotated_bytes": 0,
        }

        # Step 1 — rotate the live file if oversized
        live_file = traces_dir / "process_trace.jsonl"
        if live_file.exists():
            sz = _file_size(live_file)
            agent_state["live_bytes"] = sz
            if sz > rotate_at_bytes:
                idx = _next_rotation_index(traces_dir)
                rotated_path = traces_dir / f"process_trace.{idx}.jsonl"
                totals["would_rotate_bytes"] += sz
                if not dry_run:
                    try:
                        live_file.rename(rotated_path)
                        # Touch a fresh empty file for log_process to keep writing
                        live_file.touch()
                        agent_state["rotated"].append(rotated_path.name)
                        totals["rotated"] += 1
                    except OSError as e:
                        logger.debug(f"workspace_pruner: rotate failed {live_file} → {rotated_path}: {e}")
                else:
                    agent_state["rotated"].append(f"WOULD: {rotated_path.name} ({sz} bytes)")
                    totals["rotated"] += 1

        # Step 2 — archive any rotated .{N}.jsonl files older than archive_after_days
        try:
            for f in traces_dir.iterdir():
                if not f.is_file():
                    continue
                name = f.name
                # Match process_trace.{N}.jsonl  (NOT the live process_trace.jsonl)
                if not (name.startswith("process_trace.") and name.endswith(".jsonl") and name != "process_trace.jsonl"):
                    continue
                middle = name[len("process_trace."):-len(".jsonl")]
                if not middle.isdigit():
                    continue
                age = _file_age_days(f)
                if age < archive_after_days:
                    continue

                sz = _file_size(f)
                totals["would_archive_bytes"] += sz
                # Build archive destination: archive/{agent}/workspace_traces/process_trace.{N}.{YYYYMMDD}.jsonl.gz
                date_tag = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y%m%d")
                archive_dest_dir = archive_root / agent_id / "workspace_traces"
                archive_dest = archive_dest_dir / f"{name[:-len('.jsonl')]}.{date_tag}.jsonl.gz"

                if not dry_run:
                    try:
                        archive_dest_dir.mkdir(parents=True, exist_ok=True)
                        with f.open("rb") as src, gzip.open(archive_dest, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        f.unlink()
                        agent_state["archived"].append(archive_dest.name)
                        totals["archived"] += 1
                    except OSError as e:
                        logger.debug(f"workspace_pruner: archive failed {f} → {archive_dest}: {e}")
                else:
                    agent_state["archived"].append(f"WOULD: {archive_dest.name} ({sz} bytes)")
                    totals["archived"] += 1
        except OSError:
            pass

        # Step 3 — delete archived .gz files older than delete_after_days
        # IFF the IPFS CID is confirmed in pgvector. The pgvector check is
        # best-effort; if the module is unreachable we skip deletion (the
        # offload-then-delete invariant protects the data).
        archive_dest_dir = archive_root / agent_id / "workspace_traces"
        if archive_dest_dir.exists():
            try:
                from agents import memory_pgvector as _mpg
                has_cid = getattr(_mpg, "has_offloaded_cid", None)
            except Exception:
                has_cid = None

            for f in archive_dest_dir.iterdir():
                if not f.is_file() or not f.name.endswith(".jsonl.gz"):
                    continue
                age = _file_age_days(f)
                if age < delete_after_days:
                    continue
                # CID confirmation — agent_id + the date tag we embedded in the name
                #   process_trace.{N}.{YYYYMMDD}.jsonl.gz
                parts = f.name.split(".")
                date_tag = parts[2] if len(parts) >= 3 and parts[2].isdigit() and len(parts[2]) == 8 else None

                cid_ok = False
                if has_cid and date_tag:
                    try:
                        cid_ok = await has_cid(agent_id=agent_id, date=date_tag)
                    except Exception:
                        cid_ok = False

                if not cid_ok:
                    totals["skipped_no_cid"] += 1
                    continue

                sz = _file_size(f)
                totals["would_delete_bytes"] += sz
                if not dry_run:
                    try:
                        f.unlink()
                        agent_state["deleted"].append(f.name)
                        totals["deleted"] += 1
                    except OSError as e:
                        logger.debug(f"workspace_pruner: delete failed {f}: {e}")
                else:
                    agent_state["deleted"].append(f"WOULD: {f.name} ({sz} bytes)")
                    totals["deleted"] += 1

        if any(agent_state[k] for k in ("rotated", "archived", "deleted")) or agent_state["live_bytes"]:
            per_agent[agent_id] = agent_state

    return {
        "dry_run": dry_run,
        "policy": {
            "rotate_at_bytes":    rotate_at_bytes,
            "archive_after_days": archive_after_days,
            "delete_after_days":  delete_after_days,
        },
        "totals": totals,
        "per_agent": per_agent,
        "computed_at": time.time(),
    }
