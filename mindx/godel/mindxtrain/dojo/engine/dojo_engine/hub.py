"""Model hub: search HuggingFace, list repo files, and download — stdlib only.

Used by the Rust host for the in-app model manager. Search and file listing
print a single JSON object on stdout. Download streams newline-delimited JSON
progress events (same protocol family as ``events.py``) so the UI can show a
live progress bar, and is resumable via HTTP Range.

  python -m dojo_engine.hub --search "qwen2.5 0.5b" --limit 20 [--gguf]
  python -m dojo_engine.hub --files Qwen/Qwen2.5-0.5B-Instruct-GGUF
  python -m dojo_engine.hub --download REPO --file path.gguf --dest DIR
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

HF = "https://huggingface.co"
UA = {"User-Agent": "the-dojo/0.1 (+https://github.com/the-dojo)"}

# Force UTF-8 stdout (Windows pipes default to cp1252 → crashes on non-ASCII).
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass


def _get_json(url: str):
    with urlopen(Request(url, headers=UA), timeout=30) as resp:
        return json.load(resp)


def search(query: str, limit: int, gguf: bool) -> dict:
    params = {
        "search": query,
        "sort": "downloads",
        "direction": -1,
        "limit": limit,
    }
    if gguf:
        params["filter"] = "gguf"
    url = f"{HF}/api/models?{urlencode(params)}"
    data = _get_json(url)
    results = [
        {
            "id": m.get("id"),
            "downloads": m.get("downloads", 0),
            "likes": m.get("likes", 0),
            "pipeline_tag": m.get("pipeline_tag"),
            "library_name": m.get("library_name"),
            "gguf": "gguf" in (m.get("tags") or []),
            "tags": [t for t in (m.get("tags") or []) if not t.startswith(("base_model", "region:", "arxiv:"))][:6],
        }
        for m in data
    ]
    return {"results": results}


def list_files(repo: str, revision: str = "main") -> dict:
    url = f"{HF}/api/models/{repo}/tree/{revision}?recursive=true"
    arr = _get_json(url)
    files = []
    for e in arr:
        if e.get("type") != "file":
            continue
        size = (e.get("lfs") or {}).get("size") or e.get("size", 0)
        path = e.get("path", "")
        files.append({"path": path, "size": size, "gguf": path.lower().endswith(".gguf")})
    files.sort(key=lambda f: (not f["gguf"], f["path"]))
    return {"files": files}


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def download(repo: str, file: str, dest: str, revision: str = "main") -> int:
    url = f"{HF}/{repo}/resolve/{revision}/{quote(file)}?download=true"
    os.makedirs(dest, exist_ok=True)
    out = os.path.join(dest, os.path.basename(file))
    part = out + ".part"

    existing = os.path.getsize(part) if os.path.exists(part) else 0
    req = Request(url, headers=dict(UA))
    if existing:
        req.add_header("Range", f"bytes={existing}-")

    _emit({"type": "log", "level": "info", "message": f"GET {url}"})
    try:
        with urlopen(req, timeout=60) as resp:
            resuming = existing > 0 and resp.getcode() == 206
            downloaded = existing if resuming else 0
            length = int(resp.headers.get("Content-Length", 0) or 0)
            total = length + (existing if resuming else 0)
            mode = "ab" if resuming else "wb"

            start = time.time()
            last = 0.0
            with open(part, mode) as fh:
                while True:
                    chunk = resp.read(1 << 20)  # 1 MiB
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if now - last > 0.25:
                        elapsed = max(1e-6, now - start)
                        speed = (downloaded - (existing if resuming else 0)) / elapsed
                        _emit({
                            "type": "download_progress",
                            "downloaded": downloaded,
                            "total": total,
                            "speed": round(speed),
                            "pct": round(downloaded / total * 100, 1) if total else None,
                        })
                        last = now
    except Exception as exc:  # noqa: BLE001
        _emit({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
        return 1

    os.replace(part, out)
    _emit({"type": "done", "artifact": out, "summary": {"bytes": os.path.getsize(out)}})
    return 0


def download_all(repo: str, dest: str, revision: str = "main") -> int:
    """Download every file in a repo into `dest/<repo-leaf>/`, preserving paths.

    Streams a single aggregate progress (cumulative bytes across all files), so a
    sharded `.safetensors` model or a diffusers-layout repo downloads as one job.
    """
    try:
        files = list_files(repo, revision)["files"]
    except Exception as exc:  # noqa: BLE001
        _emit({"type": "error", "message": f"Could not list {repo}: {exc}"})
        return 1
    if not files:
        _emit({"type": "error", "message": f"No files found in {repo}"})
        return 1

    leaf = repo.split("/")[-1]
    target = os.path.join(dest, leaf)
    total = sum(int(f.get("size") or 0) for f in files)
    done_bytes = 0      # cumulative incl. already-present files (drives pct)
    session_bytes = 0   # bytes actually pulled this run (drives speed)
    start = time.time()
    last = 0.0

    def progress(current: str):
        elapsed = max(1e-6, time.time() - start)
        _emit({
            "type": "download_progress",
            "downloaded": done_bytes,
            "total": total,
            "speed": round(session_bytes / elapsed),
            "pct": round(done_bytes / total * 100, 1) if total else None,
            "file": current,
        })

    _emit({"type": "log", "level": "info", "message": f"Downloading {len(files)} files from {repo} -> {target}"})
    for f in files:
        rel = f["path"]
        size = int(f.get("size") or 0)
        out = os.path.join(target, *rel.split("/"))
        os.makedirs(os.path.dirname(out) or target, exist_ok=True)
        # Skip files already present at the right size.
        if size and os.path.exists(out) and os.path.getsize(out) == size:
            done_bytes += size
            progress(rel)
            continue
        url = f"{HF}/{repo}/resolve/{revision}/{quote(rel)}?download=true"
        part = out + ".part"
        try:
            # Resume a partial .part from a prior interrupted run.
            have = os.path.getsize(part) if os.path.exists(part) else 0
            req = Request(url, headers=dict(UA))
            if have:
                req.add_header("Range", f"bytes={have}-")
            with urlopen(req, timeout=120) as resp:
                resuming = have > 0 and resp.getcode() == 206
                mode = "ab" if resuming else "wb"
                if resuming:
                    done_bytes += have
                with open(part, mode) as fh:
                    while True:
                        chunk = resp.read(1 << 20)
                        if not chunk:
                            break
                        fh.write(chunk)
                        done_bytes += len(chunk)
                        session_bytes += len(chunk)
                        if time.time() - last > 0.25:
                            progress(rel)
                            last = time.time()
            os.replace(part, out)
            last = 0.0  # force a progress emit at the start of the next file
        except Exception as exc:  # noqa: BLE001
            _emit({"type": "error", "message": f"Failed on {rel}: {type(exc).__name__}: {exc}"})
            return 1

    _emit({"type": "done", "artifact": target, "summary": {"files": len(files), "bytes": total}})
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dojo_engine.hub")
    p.add_argument("--search")
    p.add_argument("--files")
    p.add_argument("--download")
    p.add_argument("--download-all", dest="download_all")
    p.add_argument("--file")
    p.add_argument("--dest")
    p.add_argument("--revision", default="main")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--gguf", action="store_true")
    args = p.parse_args(argv)

    try:
        if args.search is not None:
            print(json.dumps(search(args.search, args.limit, args.gguf)))
            return 0
        if args.files is not None:
            print(json.dumps(list_files(args.files, args.revision)))
            return 0
        if args.download is not None:
            if not args.file or not args.dest:
                _emit({"type": "error", "message": "--download requires --file and --dest"})
                return 1
            return download(args.download, args.file, args.dest, args.revision)
        if args.download_all is not None:
            if not args.dest:
                _emit({"type": "error", "message": "--download-all requires --dest"})
                return 1
            return download_all(args.download_all, args.dest, args.revision)
    except Exception as exc:  # noqa: BLE001
        # For search/files (non-streaming) emit a JSON error object.
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        return 1

    p.error("one of --search / --files / --download / --download-all is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
