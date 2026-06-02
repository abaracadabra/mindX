# SPDX-License-Identifier: Apache-2.0
"""SkillManifest — content-addressable registry of every SKILL.md.

Phase A absorption from the post-Day-6 backlog. Each SKILL.md is already
content-addressable as a file (sha256 over its UTF-8 bytes); this module
turns the SkillStore into a **deterministic manifest** — a single JSON
document that lists every active skill keyed by ``<category>/<slug>`` with
its sha256, byte size, scanner verdict, and (optionally) its 0G Storage
merkle root.

The manifest is byte-stable: identical store contents → identical manifest
bytes → identical manifest sha256 → identical 0G merkle root. This is the
foundation for the Phase B chain anchor (a tiny ``SkillRegistry`` contract
that records ``(manifest_root, skill_count, generated_at)`` per revision)
— Phase B ships in a follow-up commit when the contract is deployed and
the chain credentials are vaulted.

What this iteration does:

  1. ``build_manifest(store)`` walks the SkillStore, sha256s each SKILL.md,
     and returns a ``SkillManifest`` (a frozen dataclass + ``.to_json()``).
     Pinned + archived skills are excluded; ``created_by`` is recorded.
  2. ``manifest.canonical_bytes()`` is the byte-stable JSON encoding (sorted
     keys, no whitespace, UTF-8). ``manifest.sha256()`` derives from those
     bytes — anyone re-running ``build_manifest`` against an identical
     store gets the same hash without coordination.
  3. ``await upload_manifest(manifest, provider=ZeroGProvider())`` ships
     the canonical bytes to 0G Storage and returns the resulting 0G merkle
     root. With no provider it is a no-op that just returns ``None``.
  4. ``verify_skill(manifest, category, slug, store)`` re-sha256s the
     on-disk SKILL.md and compares against the manifest entry — catches
     local tampering between revisions.
  5. ``persist(manifest, dest)`` writes the canonical JSON + a tiny
     ``<dest>.meta.json`` (root, generated_at, skill_count) for the
     ``/insight`` endpoint to discover.

Authority: read-only against the SkillStore. The manifest is a derived
artifact — replaying ``build_manifest`` against the same store always
produces the same bytes; no source of truth is the manifest itself.

Phase B (deferred): ``anchor_manifest(root)`` — submit a transaction to
the (yet-to-be-deployed) ``SkillRegistry`` contract on 0G Chain via
``agents/storage/raw_tx.py``. Today this method exists as a stub that
returns ``("not_anchored", None)`` so callers don't need to special-case
its absence later.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from agents.skills.scanner import scan_skill
from agents.skills.skill_schema import parse_skill_md

logger = logging.getLogger("agents.skills.manifest")

MANIFEST_VERSION = "1.0"
DEFAULT_MANIFEST_PATH = Path.home() / ".mindx" / "skills" / ".manifest" / "current.json"


@dataclass(frozen=True)
class ManifestEntry:
    """One row of the manifest — everything a verifier needs to confirm a
    given SKILL.md is the same byte-for-byte as the registered copy."""
    category: str
    slug: str
    name: str
    sha256: str
    size_bytes: int
    created_by: str
    scanner: str           # "ok" | "blocked" | "skipped"
    pinned: bool

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "slug": self.slug,
            "name": self.name,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "created_by": self.created_by,
            "scanner": self.scanner,
            "pinned": self.pinned,
        }


@dataclass
class SkillManifest:
    """Deterministic snapshot of a SkillStore at one point in time."""
    manifest_version: str = MANIFEST_VERSION
    generated_at: float = field(default_factory=time.time)
    skill_count: int = 0
    entries: list[ManifestEntry] = field(default_factory=list)
    previous_manifest_root: Optional[str] = None   # 0G root of the prior manifest, if any

    def to_dict(self) -> dict:
        # Sorted by (category, slug) so equivalent stores produce equivalent JSON.
        rows = sorted([e.to_dict() for e in self.entries],
                      key=lambda r: (r["category"], r["slug"]))
        return {
            "manifest_version": self.manifest_version,
            "generated_at": round(self.generated_at, 3),
            "skill_count": self.skill_count,
            "previous_manifest_root": self.previous_manifest_root,
            "entries": rows,
        }

    def canonical_bytes(self) -> bytes:
        """Byte-stable JSON encoding — same content always yields the same bytes."""
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def entry_for(self, category: str, slug: str) -> Optional[ManifestEntry]:
        for e in self.entries:
            if e.category == category and e.slug == slug:
                return e
        return None


# ─── builders ─────────────────────────────────────────────────────────


def _sha256_path(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def build_manifest(
    store,
    *,
    previous_manifest_root: Optional[str] = None,
    include_pinned: bool = True,
) -> SkillManifest:
    """Walk the SkillStore and build a deterministic manifest.

    ``previous_manifest_root`` is recorded but not validated — the caller
    knows whether they want a chain of revisions or a one-off snapshot.
    """
    entries: list[ManifestEntry] = []
    for ref in store.list():
        if not include_pinned and ref.pinned:
            continue
        try:
            sha, size = _sha256_path(ref.path)
            sk = parse_skill_md(ref.path)
            scan_res = scan_skill(sk)
            scanner_state = "ok" if scan_res.safe else "blocked"
        except Exception as e:
            logger.warning(f"manifest: skip {ref.category}/{ref.slug}: {e}")
            continue
        entries.append(ManifestEntry(
            category=ref.category,
            slug=ref.slug,
            name=ref.name,
            sha256=sha,
            size_bytes=size,
            created_by=ref.created_by,
            scanner=scanner_state,
            pinned=ref.pinned,
        ))

    return SkillManifest(
        skill_count=len(entries),
        entries=entries,
        previous_manifest_root=previous_manifest_root,
    )


# ─── persistence ──────────────────────────────────────────────────────


def persist(
    manifest: SkillManifest,
    *,
    dest: Optional[Path | str] = None,
    zg_root: Optional[str] = None,
) -> Path:
    """Write ``manifest.canonical_bytes()`` to disk + a sidecar metadata
    file with the sha256, 0G root, and counters. Returns the manifest path.

    The sidecar lives at ``<dest>.meta.json`` so ``/insight`` can read it
    without parsing the full manifest each time.
    """
    if dest is None:
        dest = DEFAULT_MANIFEST_PATH
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    body = manifest.canonical_bytes()
    dest.write_bytes(body)
    try:
        dest.chmod(0o600)
    except Exception:
        pass

    meta = {
        "manifest_version": manifest.manifest_version,
        "generated_at": round(manifest.generated_at, 3),
        "skill_count": manifest.skill_count,
        "sha256": manifest.sha256(),
        "size_bytes": len(body),
        "zg_root": zg_root,
        "previous_manifest_root": manifest.previous_manifest_root,
        "manifest_path": str(dest),
    }
    meta_path = dest.with_suffix(dest.suffix + ".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    return dest


def load_meta(dest: Optional[Path | str] = None) -> Optional[dict]:
    """Read the sidecar metadata for the most recent persisted manifest.

    Returns ``None`` if no manifest has been built yet.
    """
    if dest is None:
        dest = DEFAULT_MANIFEST_PATH
    dest = Path(dest)
    meta_path = dest.with_suffix(dest.suffix + ".meta.json")
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ─── upload to 0G Storage ─────────────────────────────────────────────


async def upload_manifest(manifest: SkillManifest, provider=None) -> Optional[str]:
    """Ship the canonical manifest bytes to 0G Storage. Returns the merkle
    root as a 0x-prefixed hex string, or ``None`` if no provider was given
    or the upload failed (caller decides what to do — manifest still on disk).

    The provider must expose ``async upload(bytes, name) -> (root, tx_hash)``
    matching :class:`agents.storage.zerog_provider.ZeroGProvider`.
    """
    if provider is None:
        return None
    try:
        body = manifest.canonical_bytes()
        root, _tx = await provider.upload(body, name="skill_manifest.json")
        return str(root)
    except Exception as e:
        logger.warning(f"manifest: 0G upload failed: {e}")
        return None


# ─── verification ─────────────────────────────────────────────────────


@dataclass
class VerificationResult:
    category: str
    slug: str
    expected_sha256: Optional[str]
    actual_sha256: Optional[str]
    matched: bool
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "slug": self.slug,
            "expected_sha256": self.expected_sha256,
            "actual_sha256": self.actual_sha256,
            "matched": self.matched,
            "reason": self.reason,
        }


def verify_skill(manifest: SkillManifest, category: str, slug: str, store) -> VerificationResult:
    """Compare the on-disk SKILL.md's sha256 against the manifest entry.

    Catches local tampering, partial writes, and "skill missing from disk".
    """
    entry = manifest.entry_for(category, slug)
    expected = entry.sha256 if entry else None

    path = store._path_for(category, slug)
    if not path.exists():
        return VerificationResult(
            category=category, slug=slug,
            expected_sha256=expected, actual_sha256=None,
            matched=False, reason="skill file missing on disk",
        )

    try:
        actual, _size = _sha256_path(path)
    except Exception as e:
        return VerificationResult(
            category=category, slug=slug,
            expected_sha256=expected, actual_sha256=None,
            matched=False, reason=f"could not hash skill: {e}",
        )

    if entry is None:
        return VerificationResult(
            category=category, slug=slug,
            expected_sha256=None, actual_sha256=actual,
            matched=False, reason="skill not present in manifest",
        )
    if actual != expected:
        return VerificationResult(
            category=category, slug=slug,
            expected_sha256=expected, actual_sha256=actual,
            matched=False, reason="sha256 mismatch — local copy diverges from registered",
        )
    return VerificationResult(
        category=category, slug=slug,
        expected_sha256=expected, actual_sha256=actual,
        matched=True,
    )


def verify_all(manifest: SkillManifest, store) -> list[VerificationResult]:
    """Run :func:`verify_skill` against every entry in the manifest."""
    return [verify_skill(manifest, e.category, e.slug, store) for e in manifest.entries]


# ─── chain anchor stub (Phase B) ──────────────────────────────────────


def anchor_manifest(root: str, *, rpc_url: Optional[str] = None) -> tuple[str, Optional[str]]:
    """Phase B placeholder — submit ``root`` to the SkillRegistry on 0G Chain.

    Returns ``(status, tx_hash)``. Today this is a stub that returns
    ``("not_anchored", None)`` so callers compose against the final shape.
    Mirrors ``agents/storage/anchor.py:anchor_thot`` — the same staging
    pattern noted in ``CLAUDE.md`` for ARC vs THOT permissions.
    """
    return ("not_anchored", None)


__all__ = [
    "MANIFEST_VERSION",
    "ManifestEntry",
    "SkillManifest",
    "VerificationResult",
    "build_manifest",
    "persist",
    "load_meta",
    "upload_manifest",
    "verify_skill",
    "verify_all",
    "anchor_manifest",
    "DEFAULT_MANIFEST_PATH",
]
