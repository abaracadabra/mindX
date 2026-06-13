# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""ephermaleth.votingbooth — an append-only, tamper-evident ledger of council decisions.

Where the board (and other councils — a war council, a DAIO, a conclave) records
its decisions so they survive, stay ordered, and can be re-verified by anyone.
Built on the same principles as the BANKON Vault's overseer audit log: an
**append-only, fsync'd, hash-linked** file outside any secret store — each record
carries the previous record's hash, so the whole sequence is a tamper-evident
chain. Each decision may embed an ``ephermaleth`` attestation chain (who signed
what), and the booth itself is content-addressed per record.

A record is:
    {
      "seq", "ts", "council", "subject",
      "decision",            # the outcome (e.g. "passed" / "rejected" / free text)
      "tally":  {...},       # optional vote tally / quorum detail
      "votes":  [...],       # optional per-member votes (id, vote, weight, signature)
      "chain":  {...},       # optional ephermaleth attestation chain (provenance)
      "prev",                # previous record's record_hash (hash-linked ledger)
      "record_hash"          # sha256 of the canonical record body (content address)
    }

The booth is storage-agnostic about *what* a council is — it just namespaces by
``council`` — so the same booth holds the boardroom's votes, a war council's
rulings, and a throne's proclamations side by side, each independently verifiable.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .verify import verify_chain

logger = logging.getLogger("ephermaleth.votingbooth")


def _sha(s: str) -> str:
    return "0x" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def _canonical(d: Dict[str, Any]) -> str:
    return json.dumps(d, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


class VotingBooth:
    """An append-only, hash-linked ledger of council decisions."""

    def __init__(self, path: "str | Path") -> None:
        self.path = Path(path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:  # pragma: no cover
            logger.warning(f"VotingBooth: cannot create dir: {e}")

    # ── read ──────────────────────────────────────────────────────────
    def _all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out: List[Dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out

    def head(self) -> str:
        rows = self._all()
        return rows[-1].get("record_hash", "0x0") if rows else "0x0"

    def list(self, *, council: Optional[str] = None, limit: int = 0) -> List[Dict[str, Any]]:
        rows = self._all()
        if council:
            rows = [r for r in rows if r.get("council") == council]
        return rows[-limit:] if limit and limit > 0 else rows

    def get(self, record_hash: str) -> Optional[Dict[str, Any]]:
        for r in self._all():
            if r.get("record_hash") == record_hash:
                return r
        return None

    # ── write ─────────────────────────────────────────────────────────
    def record(self, *, council: str, subject: str, decision: str, ts: int,
               tally: Optional[Dict[str, Any]] = None,
               votes: Optional[List[Dict[str, Any]]] = None,
               chain: Optional[Dict[str, Any]] = None,
               extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Append a council decision. The record is hash-linked to the previous
        one (``prev`` = last ``record_hash``) and content-addressed
        (``record_hash`` = sha256 of the canonical body). Append is fsync'd."""
        # Take an exclusive advisory lock for the read-tail → append critical
        # section, so concurrent writers can't interleave or compute the same
        # seq/prev (POSIX fcntl; a no-op fallback where unavailable).
        lock = self._lock()
        try:
            seq = len(self._all())
            prev = self.head()
            body: Dict[str, Any] = {
                "seq": seq, "ts": int(ts), "council": str(council),
                "subject": str(subject), "decision": str(decision),
                "tally": tally or {}, "votes": votes or [],
                "chain": chain or None, "prev": prev,
            }
            if extra:
                body["extra"] = extra
            body["record_hash"] = _sha(_canonical(body))
            line = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
            try:
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
                    f.flush()
                    os.fsync(f.fileno())
            except Exception as e:
                logger.warning(f"VotingBooth.record append failed: {e}")
            return body
        finally:
            self._unlock(lock)

    def _lock(self):
        """Best-effort exclusive lock on a sidecar file (POSIX fcntl)."""
        try:
            import fcntl
            lf = self.path.with_suffix(self.path.suffix + ".lock").open("w")
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            return lf
        except Exception:
            return None

    @staticmethod
    def _unlock(lf) -> None:
        if lf is None:
            return
        try:
            import fcntl
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            lf.close()
        except Exception:
            pass

    # ── verify ────────────────────────────────────────────────────────
    def verify_record(self, record: Dict[str, Any],
                      registry: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Verify one record: recompute its content hash and verify any embedded
        attestation chain."""
        claimed = record.get("record_hash")
        body = {k: v for k, v in record.items() if k != "record_hash"}
        content_ok = (_sha(_canonical(body)) == claimed)
        chain = record.get("chain")
        chain_report = verify_chain(chain, registry) if isinstance(chain, dict) and chain.get("links") else None
        return {
            "record_hash": claimed, "content_ok": content_ok,
            "chain": chain_report,
            "valid": content_ok and (chain_report is None or chain_report["valid"]),
        }

    def verify_ledger(self, registry: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Verify the whole booth: every record's content hash, the prev/hash
        linkage across the sequence, and every embedded attestation chain."""
        rows = self._all()
        prev = "0x0"
        linkage_ok = True
        records_ok = True
        chains_ok = True
        per: List[Dict[str, Any]] = []
        for r in rows:
            rep = self.verify_record(r, registry)
            link_ok = (r.get("prev") == prev)
            if not link_ok:
                linkage_ok = False
            if not rep["content_ok"]:
                records_ok = False
            if rep["chain"] is not None and not rep["chain"]["valid"]:
                chains_ok = False
            per.append({"seq": r.get("seq"), "council": r.get("council"),
                        "linkage_ok": link_ok, **rep})
            prev = r.get("record_hash", "")
        return {
            "records": len(rows), "linkage_ok": linkage_ok,
            "records_ok": records_ok, "chains_ok": chains_ok,
            "valid": linkage_ok and records_ok and chains_ok, "per_record": per,
        }


__all__ = ["VotingBooth"]
