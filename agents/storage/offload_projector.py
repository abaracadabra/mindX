"""
OffloadProjector — promote eligible STM memories to IPFS.

For each (agent_id, date) tuple older than the cutoff:
  1. Pack files into a gzipped JSONL bundle (deterministic, content-addressed).
  2. Upload to MultiProvider (Lighthouse + nft.storage). Both must agree on CID.
  3. Verify by retrieving and sha256-comparing.
  4. Mark each contained memory in pgvector with content_cid + offload_tier='ipfs'.
  5. Emit `memory.offload` catalogue event with the agent's wallet signature.
  6. Optionally delete the local date-dir (only if dry_run is False AND verify
     succeeded).

Phase B ships dry_run=True by default. The destructive backfill that actually
deletes STM files requires explicit `dry_run=False` from a user-issued
admin call.

Plan: ~/.claude/plans/whispering-floating-merkle.md
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from utils.logging_config import get_logger
from utils.config import PROJECT_ROOT

from .anchor import AnchorClient
from .car_bundle import bundle_iter, manifest, pack_directory
from .eligibility import OffloadCandidate, list_eligible
from .multi_provider import MultiProvider
from .provider import CID, ProviderError

logger = get_logger(__name__)


@dataclass
class OffloadResult:
    agent_id: str
    date_str: str
    file_count: int
    bytes_packed: int
    bytes_uploaded: int
    cid: Optional[str] = None
    cid_mirror: Optional[str] = None
    sha256: Optional[str] = None
    verified: bool = False
    deleted_local: bool = False
    memory_ids_marked: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0
    dry_run: bool = True


@dataclass
class OffloadRun:
    started_at: float
    finished_at: Optional[float] = None
    candidates_total: int = 0
    candidates_processed: int = 0
    bytes_packed_total: int = 0
    bytes_freed_total: int = 0
    results: list[OffloadResult] = field(default_factory=list)


class OffloadProjector:
    """Orchestrates per-(agent,date) offload to IPFS."""

    def __init__(
        self,
        provider: MultiProvider,
        memory_agent=None,
        id_manager=None,
        project_root: Optional[Path] = None,
        anchor: Optional[AnchorClient] = None,
    ):
        self.provider = provider
        self.memory_agent = memory_agent
        self.id_manager = id_manager
        self.project_root = project_root or PROJECT_ROOT
        # Anchor is optional: if unconfigured, offload still succeeds without
        # an on-chain receipt (offload_tx_hash stays NULL).
        self.anchor = anchor or AnchorClient()

    async def run(
        self,
        *,
        agent_id: Optional[str] = None,
        min_age_days: float = 14.0,
        max_batches: int = 50,
        dry_run: bool = True,
    ) -> OffloadRun:
        """
        Run a single pass of the offload projector.

        Args:
            agent_id: restrict to one agent (None = all eligible).
            min_age_days: only offload directories older than this.
            max_batches: cap on (agent, date) tuples processed in this pass.
            dry_run: if True (default), upload+verify+mark-DB but DO NOT delete
                local files. Set to False explicitly to free disk.
        """
        run = OffloadRun(started_at=time.time())
        candidates = list_eligible(
            self.project_root, min_age_days=min_age_days, agent_id=agent_id,
        )
        run.candidates_total = len(candidates)
        for cand in candidates[:max_batches]:
            res = await self._process(cand, dry_run=dry_run)
            run.results.append(res)
            run.candidates_processed += 1
            run.bytes_packed_total += res.bytes_packed
            if res.deleted_local:
                run.bytes_freed_total += res.bytes_packed
            # Yield to the event loop between batches so we don't starve
            # other tasks during a large backfill.
            await asyncio.sleep(0)
        run.finished_at = time.time()
        return run

    async def _process(self, cand: OffloadCandidate, *, dry_run: bool) -> OffloadResult:
        t0 = time.time()
        result = OffloadResult(
            agent_id=cand.agent_id,
            date_str=cand.date_str,
            file_count=0,
            bytes_packed=0,
            bytes_uploaded=0,
            dry_run=dry_run,
        )
        try:
            mani = manifest(cand.path)
            result.file_count = mani["file_count"]
            blob = pack_directory(cand.path)
            result.bytes_packed = len(blob)
            result.sha256 = hashlib.sha256(blob).hexdigest()
            if not blob:
                result.error = "empty bundle"
                return result

            # Upload — MultiProvider may raise if both legs fail
            cid = await self.provider.upload(
                blob, name=f"{cand.agent_id}_{cand.date_str}.jsonl.gz",
            )
            result.cid = cid.value
            result.bytes_uploaded = len(blob)

            # Verify by re-downloading; require sha256 match
            try:
                back = await self.provider.retrieve(cid, timeout=15.0)
                back_sha = hashlib.sha256(back).hexdigest()
                result.verified = back_sha == result.sha256
                if not result.verified:
                    result.error = (
                        f"verify failed: local_sha={result.sha256[:12]} "
                        f"remote_sha={back_sha[:12]}"
                    )
                    logger.warning(
                        "[offload] verify failed for %s/%s — keeping local",
                        cand.agent_id, cand.date_str,
                    )
            except ProviderError as ve:
                result.error = f"verify retrieval failed: {ve}"
                result.verified = False

            # Mark every memory_id in this batch as offloaded (best-effort)
            if result.verified:
                # On-chain anchor (best-effort; skipped if anchor not configured)
                anchor_receipt: dict = {}
                tx_hash: Optional[str] = None
                if self.anchor.configured:
                    try:
                        anchor_receipt = await self.anchor.anchor_dataset_registry(
                            agent_id=cand.agent_id,
                            date_str=cand.date_str,
                            cid=result.cid,
                        )
                        tx_hash = anchor_receipt.get("tx_hash")
                        if tx_hash:
                            logger.info(
                                "[offload] anchored %s/%s -> tx %s",
                                cand.agent_id, cand.date_str, tx_hash,
                            )
                    except Exception as ae:
                        logger.debug("[offload] anchor failed: %s", ae)
                        anchor_receipt = {"error": str(ae)}

                marked = await self._mark_db(
                    blob, cid_value=result.cid, mirror=None,
                    tx_hash=tx_hash,
                    chain="arc" if tx_hash else None,
                )
                result.memory_ids_marked = marked

                # Emit catalogue event so /insight/storage/recent can read it
                await self._emit_offload_event(
                    cand=cand, result=result, anchor_receipt=anchor_receipt,
                )

                # Delete local files only if not in dry_run mode
                if not dry_run:
                    try:
                        shutil.rmtree(cand.path)
                        result.deleted_local = True
                        logger.info(
                            "[offload] deleted %s/%s — %d files, %s freed",
                            cand.agent_id, cand.date_str, result.file_count,
                            _human_bytes(result.bytes_packed),
                        )
                    except OSError as de:
                        result.error = f"delete failed: {de}"
        except ProviderError as pe:
            result.error = f"provider error: {pe}"
            logger.warning("[offload] %s/%s upload failed: %s",
                           cand.agent_id, cand.date_str, pe)
        except Exception as e:
            result.error = f"{type(e).__name__}: {e}"
            logger.exception("[offload] %s/%s unexpected failure",
                             cand.agent_id, cand.date_str)
        finally:
            result.duration_seconds = time.time() - t0
        return result

    async def _mark_db(
        self,
        blob: bytes,
        *,
        cid_value: str,
        mirror: Optional[str],
        tx_hash: Optional[str] = None,
        chain: Optional[str] = None,
    ) -> int:
        """For every memory_id in the bundle, update pgvector row."""
        try:
            from agents import memory_pgvector
        except Exception:
            return 0
        marked = 0
        for entry in bundle_iter(blob):
            rec = entry.get("record") or {}
            memory_id = rec.get("memory_id")
            if not memory_id:
                continue
            try:
                ok = await memory_pgvector.mark_memory_offloaded(
                    memory_id=memory_id,
                    content_cid=cid_value,
                    content_cid_mirror=mirror,
                    offload_tier="ipfs",
                    tx_hash=tx_hash,
                    chain=chain,
                )
                if ok:
                    marked += 1
            except Exception:
                continue
        return marked

    async def _emit_offload_event(self, *, cand: OffloadCandidate, result: OffloadResult, anchor_receipt: Optional[dict] = None) -> None:
        try:
            from agents.catalogue import emit_catalogue_event
        except Exception:
            return
        wallet = None
        if self.id_manager is not None:
            try:
                wallet = self.id_manager.get_public_address(cand.agent_id)
            except Exception:
                wallet = None
        try:
            await emit_catalogue_event(
                kind="memory.offload",
                actor=cand.agent_id,
                payload={
                    "date_str": cand.date_str,
                    "file_count": result.file_count,
                    "bytes_packed": result.bytes_packed,
                    "cid": result.cid,
                    "sha256": result.sha256,
                    "verified": result.verified,
                    "deleted_local": result.deleted_local,
                    "dry_run": result.dry_run,
                    "anchor": anchor_receipt or None,
                },
                source_log="storage/offload_projector",
                source_ref=f"{cand.agent_id}/{cand.date_str}",
                actor_wallet=wallet,
            )
        except Exception:
            pass


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return f"{n:.1f}{unit}"
        n /= 1024.0  # type: ignore[assignment]
    return f"{n:.1f}PB"


def serialize_run(run: OffloadRun) -> dict:
    """Convert OffloadRun to a JSON-serializable dict for API responses."""
    return {
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "duration_seconds": (run.finished_at or time.time()) - run.started_at,
        "candidates_total": run.candidates_total,
        "candidates_processed": run.candidates_processed,
        "bytes_packed_total": run.bytes_packed_total,
        "bytes_freed_total": run.bytes_freed_total,
        "human_freed": _human_bytes(run.bytes_freed_total),
        "results": [asdict(r) for r in run.results],
    }
