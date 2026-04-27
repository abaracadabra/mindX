"""
Bundle a directory of memory JSON files into a single gzipped JSONL blob.

This is not a true IPFS CAR (Content-Addressed aRchive) — building one
correctly requires a CARv2 encoder. For Phase B we use a simpler portable
format that IPFS still treats as a single file with a deterministic CID:

  bundle.jsonl.gz
    Each line: {"_filename": <relative-path>, "_size": <bytes>, ...record}

Read back with `bundle_iter(bytes)` to reconstruct the original files.
"""

from __future__ import annotations

import gzip
import io
import json
from pathlib import Path
from typing import Iterator


def pack_directory(date_dir: Path) -> bytes:
    """
    Pack every .json file in date_dir into one gzipped JSONL bundle.

    Stable ordering: filenames sorted lexicographically so the same input
    produces the same bytes — and therefore the same CID across uploads.
    """
    if not date_dir.is_dir():
        raise FileNotFoundError(f"not a directory: {date_dir}")
    files = sorted([f for f in date_dir.iterdir() if f.is_file() and f.suffix == ".json"])
    buf = io.BytesIO()
    # mtime=0 ensures gzip header is byte-stable across runs
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        for f in files:
            try:
                raw = f.read_bytes()
                # Validate and re-serialize to canonical JSON for byte-stability
                obj = json.loads(raw)
            except (OSError, json.JSONDecodeError):
                continue
            wrapper = {
                "_filename": f.name,
                "_size": len(raw),
                "record": obj,
            }
            line = json.dumps(wrapper, sort_keys=True, separators=(",", ":")).encode("utf-8")
            gz.write(line)
            gz.write(b"\n")
    return buf.getvalue()


def bundle_iter(blob: bytes) -> Iterator[dict]:
    """Iterate records out of a packed bundle. Reverses pack_directory."""
    buf = io.BytesIO(blob)
    with gzip.GzipFile(fileobj=buf, mode="rb") as gz:
        for raw_line in gz:
            line = raw_line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def manifest(date_dir: Path) -> dict:
    """List the files that would be packed and their sizes — without packing."""
    files = sorted([f for f in date_dir.iterdir() if f.is_file() and f.suffix == ".json"])
    items = []
    total = 0
    for f in files:
        try:
            sz = f.stat().st_size
        except OSError:
            continue
        items.append({"name": f.name, "size": sz})
        total += sz
    return {"file_count": len(items), "total_size": total, "files": items}
