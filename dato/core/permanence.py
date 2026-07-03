# Copyright 2026 BANKON. All rights reserved.
# Licensed under the Apache License, Version 2.0.
"""dato permanence tiers — immortal | immutable | mutable.

One ``write_record`` dispatch turns bytes + a tier into a :class:`DataRecord`:

  IMMORTAL  → permanent ANS-104 Arweave upload via the existing Turbo desk
              (``tools/arweave_turbo.ArweaveTurboDesk``); proof = Arweave tx id.
              This is the ~200-yr data-integrity guarantee. Never changes.
  IMMUTABLE → sha256 content-lock + anchor reference; bytes NOT Arweave-stored.
              Re-committing different bytes to the same name is rejected.
  MUTABLE   → editable bytes kept in dato state (base64); version bumps on update.

Arweave is reused, not reinvented. The Turbo desk is imported lazily so the suite
imports/ runs on a box without ``cryptography``/Turbo creds (immortal then errors
clearly instead of failing at import).
"""
from __future__ import annotations

import base64
import hashlib
from typing import Any, Dict, Optional

from dato.core.model import DataRecord, PermanenceTier


class PermanenceError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_record(
    name: str,
    data: bytes,
    tier: "PermanenceTier | str",
    *,
    content_type: str = "application/octet-stream",
    existing: Optional[DataRecord] = None,
    anchor_fn: Optional[Any] = None,
) -> DataRecord:
    """Commit ``data`` at ``tier`` and return the resulting :class:`DataRecord`.

    ``existing`` is the prior record for this name (for immutable-lock checks and
    mutable version bumps). ``anchor_fn(sha256)->str`` optionally records an
    immutable anchor (e.g. on DatoCore / a ledger) and returns its reference.
    """
    tier = PermanenceTier.coerce(tier)
    digest = _sha256(data)

    if tier is PermanenceTier.IMMORTAL:
        proof = _arweave_upload(name, data, content_type)
        return DataRecord(
            name=name, sha256=digest, tier=tier, proof=proof,
            content_type=content_type, bytes_len=len(data), version=1,
        )

    if tier is PermanenceTier.IMMUTABLE:
        if existing is not None and existing.tier is PermanenceTier.IMMUTABLE and existing.sha256 != digest:
            raise PermanenceError(
                f"immutable record {name!r} is locked to sha256 {existing.sha256[:12]}…; "
                f"refusing to overwrite with different bytes"
            )
        anchor = anchor_fn(digest) if anchor_fn else f"anchor:{digest}"
        return DataRecord(
            name=name, sha256=digest, tier=tier, proof=anchor,
            content_type=content_type, bytes_len=len(data), version=1,
        )

    # MUTABLE — editable, versioned, bytes held in state.
    version = (existing.version + 1) if (existing and existing.tier is PermanenceTier.MUTABLE) else 1
    return DataRecord(
        name=name, sha256=digest, tier=tier, proof=None,
        content_type=content_type, bytes_len=len(data), version=version,
        mutable_value=base64.b64encode(data).decode(),
    )


def read_record(record: DataRecord) -> Dict[str, Any]:
    """Return a retrieval descriptor: where/how to fetch the bytes for a record."""
    if record.tier is PermanenceTier.IMMORTAL:
        return {"tier": "immortal", "arweave_id": record.proof,
                "url": f"https://arweave.net/{record.proof}" if record.proof else None}
    if record.tier is PermanenceTier.IMMUTABLE:
        return {"tier": "immutable", "anchor": record.proof, "sha256": record.sha256}
    return {"tier": "mutable", "sha256": record.sha256, "has_value": record.mutable_value is not None}


def _arweave_upload(name: str, data: bytes, content_type: str) -> str:
    """Permanent ANS-104 upload via the existing Turbo fulfillment desk."""
    try:
        from tools.arweave_turbo import ArweaveTurboDesk
    except Exception as exc:  # pragma: no cover - missing optional deps
        raise PermanenceError(f"immortal tier needs tools.arweave_turbo: {exc}") from exc
    desk = ArweaveTurboDesk()
    result = desk.upload(
        data, app_name="dato", content_type=content_type,
        extra_tags=[("Dato-Tier", "immortal"), ("Dato-Name", name)],
    )
    return result["arweaveId"]


__all__ = ["PermanenceError", "write_record", "read_record"]
