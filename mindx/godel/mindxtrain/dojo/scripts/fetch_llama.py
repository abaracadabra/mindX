#!/usr/bin/env python3
"""Fetch a llama.cpp `llama-server` build into src-tauri/binaries/ as a Tauri
sidecar, named with the Rust target triple so `externalBin` picks it up.

Cross-platform (Windows / Linux / macOS), stdlib only. Picks the right release
asset for this machine and acceleration backend, downloads + extracts it, and
places `llama-server[-<triple>][.exe]` where Tauri expects it.

  python scripts/fetch_llama.py            # auto-detect OS + accel
  python scripts/fetch_llama.py --accel rocm   # cpu | cuda | rocm | vulkan
  python scripts/fetch_llama.py --triple x86_64-unknown-linux-gnu

After running, ensure tauri.conf.json has:  "externalBin": ["binaries/llama-server"]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
import time
import zipfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = "ggml-org/llama.cpp"
UA = {"User-Agent": "the-dojo-fetch/0.1"}

# Avoid UnicodeEncodeError on Windows' cp1252 console (we print a ✓).
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

# Rust target triple for the current host.
def host_triple() -> str:
    sysname = platform.system()
    machine = platform.machine().lower()
    arch = "aarch64" if machine in ("arm64", "aarch64") else "x86_64"
    if sysname == "Windows":
        return f"{arch}-pc-windows-msvc"
    if sysname == "Darwin":
        return f"{arch}-apple-darwin"
    return f"{arch}-unknown-linux-gnu"


def _gpu_names() -> str:
    """Best-effort lowercase GPU-name string across OSes."""
    import subprocess

    try:
        if platform.system() == "Windows":
            # wmic is removed on Win11 24H2+; try it then PowerShell CIM.
            for cmd in (
                ["wmic", "path", "win32_VideoController", "get", "name"],
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_VideoController).Name"],
            ):
                try:
                    out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if out.stdout.strip():
                        return out.stdout.lower()
                except Exception:
                    continue
        elif platform.system() == "Linux":
            if shutil.which("lspci"):
                return subprocess.run(["lspci"], capture_output=True, text=True, timeout=10).stdout.lower()
            # Fallback: GPU vendor/device names exposed by DRM.
            try:
                import glob

                names = []
                for p in glob.glob("/sys/class/drm/card*/device/uevent"):
                    with open(p) as fh:
                        names.append(fh.read())
                return "\n".join(names).lower()
            except Exception:
                return ""
    except Exception:
        return ""
    return ""


def default_accel() -> str:
    # Inference accel for the *binary build* — independent of torch.
    if shutil.which("nvidia-smi"):
        return "cuda"
    if shutil.which("rocminfo") or shutil.which("rocm-smi"):
        return "rocm"
    names = _gpu_names()
    if "nvidia" in names or "geforce" in names:
        return "cuda"
    if "radeon" in names or "amd" in names or "advanced micro devices" in names:
        # Vulkan is the widest AMD compatibility; pass --accel rocm for a HIP build.
        return "vulkan"
    return "cpu"


def _get(url: str):
    return urlopen(Request(url, headers=UA), timeout=60)


def _fmt_mb(n: int) -> str:
    return f"{n / 1024 / 1024:.1f}"


def _pacman_bar(done: int, total: int, speed: float, width: int = 24, frame: int = 0) -> str:
    """A diagnostic Pac-Man progress bar: ᗧ chomps the dots as bytes land.

    Eaten track is blank, Pac-Man sits at the wavefront, pellets ('·' with the
    occasional power pellet '•') lie ahead. Trails pct, size, speed and ETA.
    """
    frac = (done / total) if total else 0.0
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else frac
    eaten = int(frac * width)
    pac = "ᗤ" if frame % 2 else "ᗧ"  # closed / open mouth → "waka waka"
    if eaten >= width:
        track = " " * width
    else:
        ahead = width - eaten - 1
        pellets = "".join("•" if (i % 4 == 3) else "·" for i in range(ahead))
        track = (" " * eaten) + pac + pellets
    pct = f"{frac * 100:4.0f}%"
    size = f"{_fmt_mb(done)}/{_fmt_mb(total)} MB" if total else f"{_fmt_mb(done)} MB"
    rate = f"{speed / 1024 / 1024:.1f} MB/s" if speed > 0 else "—"
    if speed > 0 and total:
        eta = max(0, int((total - done) / speed))
        tail = f"eta {eta // 60}m{eta % 60:02d}s" if eta >= 60 else f"eta {eta}s"
    else:
        tail = ""
    return f"道 [{track}] {pct}  {size}  {rate}  {tail}".rstrip()


def _download(url: str, dest: str, expected: int = 0, *, retries: int = 6) -> None:
    """Download ``url`` → ``dest`` with a live Pac-Man bar, resuming a ``.part``
    file via HTTP Range and retrying through stalls (the read-timeout that made
    step 4 look hung). Raises the last error if every attempt is exhausted."""
    part = dest + ".part"
    tty = sys.stdout.isatty()
    start = time.time()
    last_draw = 0.0
    frame = 0

    for attempt in range(1, retries + 1):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        req = Request(url, headers=dict(UA))
        if have:
            req.add_header("Range", f"bytes={have}-")
        try:
            with urlopen(req, timeout=30) as resp:
                resuming = have > 0 and resp.getcode() == 206
                total = (int(resp.headers.get("Content-Length", 0) or 0)
                         + (have if resuming else 0)) or expected
                done = have if resuming else 0
                mode = "ab" if resuming else "wb"
                if not resuming:
                    done = 0
                with open(part, mode) as fh:
                    while True:
                        chunk = resp.read(1 << 20)  # 1 MiB
                        if not chunk:
                            break
                        fh.write(chunk)
                        done += len(chunk)
                        now = time.time()
                        # Animate briskly on a TTY; on a pipe/log emit a line
                        # only every couple seconds so logs don't flood.
                        if now - last_draw > (0.12 if tty else 2.0):
                            frame += 1
                            speed = done / max(1e-6, now - start)
                            line = _pacman_bar(done, total, speed, frame=frame)
                            if tty:
                                sys.stdout.write("\r\033[K" + line)
                            else:
                                sys.stdout.write(line + "\n")
                            sys.stdout.flush()
                            last_draw = now
            # Completed the stream.
            if tty:
                sys.stdout.write("\r\033[K" + _pacman_bar(
                    os.path.getsize(part), total or os.path.getsize(part), 0, frame=0) + "\n")
                sys.stdout.flush()
            os.replace(part, dest)
            return
        except (URLError, TimeoutError, ConnectionError, OSError) as exc:
            # HTTP errors other than transient ones shouldn't be retried blindly.
            if isinstance(exc, HTTPError) and exc.code not in (408, 429, 500, 502, 503, 504):
                raise
            if attempt == retries:
                raise
            wait = min(30, 2 ** attempt)
            done_now = os.path.getsize(part) if os.path.exists(part) else 0
            print(f"\n  ⚠ {type(exc).__name__}: {exc} — retry {attempt}/{retries - 1} "
                  f"in {wait}s (resuming at {_fmt_mb(done_now)} MB)", file=sys.stderr)
            time.sleep(wait)
            start = time.time()  # reset rate window for the fresh attempt


BACKEND_KEYWORDS = ("cuda", "hip", "rocm", "vulkan", "sycl", "openvino", "opencl", "openblas")


def pick_asset(assets: list[dict], osname: str, accel: str, arch: str = "x86_64") -> dict | None:
    """Choose the best release asset for (os, accel, arch).

    Notes from the real asset list: Linux/macOS ship `.tar.gz`, Windows `.zip`;
    the CUDA runtime is a separate `cudart-*` package (skip it); the vanilla CPU
    Linux build carries no backend keyword (e.g. `…-bin-ubuntu-x64.tar.gz`).
    """
    os_keys = {
        "Windows": ("win", "windows"),
        "Linux": ("ubuntu", "linux"),
        "Darwin": ("macos", "darwin"),
    }[osname]
    accel_keys = {
        "cpu": ("cpu",),
        "cuda": ("cuda",),
        "rocm": ("hip", "rocm"),
        "vulkan": ("vulkan",),
    }[accel]
    arch_keys = ("arm64", "aarch64") if arch == "aarch64" else ("x64", "amd64", "x86_64")
    bad_arch = ("x64", "amd64", "x86_64") if arch == "aarch64" else ("arm64", "aarch64")

    def score(name: str) -> int:
        n = name.lower()
        if not (n.endswith(".zip") or n.endswith(".tar.gz")):
            return -1
        if not n.startswith("llama"):  # excludes cudart-* runtime packages
            return -1
        if any(b in n for b in ("xcframework", "-ui.", "android", "s390x", "adreno")):
            return -1
        if not any(k in n for k in os_keys):
            return -1
        if not any(k in n for k in arch_keys) or any(b in n for b in bad_arch):
            return -1
        if accel == "cpu":
            # Vanilla build only — reject specialized backends.
            if any(b in n for b in BACKEND_KEYWORDS if b != "cpu"):
                return -1
            return 5 + (2 if "cpu" in n else 0)
        return 10 if any(k in n for k in accel_keys) else -1

    best, best_score = None, 0
    for a in assets:
        sc = score(a.get("name", ""))
        if sc > best_score:
            best, best_score = a, sc
    if best is None and accel != "cpu":  # fall back to a CPU build
        return pick_asset(assets, osname, "cpu", arch)
    return best


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--accel", default=None, help="cpu | cuda | rocm | vulkan (default: auto)")
    p.add_argument("--triple", default=None, help="override Rust target triple")
    p.add_argument("--out", default=None, help="binaries dir (default: ../src-tauri/binaries)")
    args = p.parse_args(argv)

    osname = platform.system()
    accel = args.accel or default_accel()
    triple = args.triple or host_triple()
    machine = platform.machine().lower()
    arch = "aarch64" if machine in ("arm64", "aarch64") else "x86_64"
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = args.out or os.path.join(repo_root, "src-tauri", "binaries")
    os.makedirs(out_dir, exist_ok=True)

    print(f"Host: {osname} {platform.machine()} | accel={accel} | triple={triple}")
    print("Querying latest llama.cpp release…")
    rel = json.load(_get(f"https://api.github.com/repos/{REPO}/releases/latest"))
    tag = rel.get("tag_name", "?")
    asset = pick_asset(rel.get("assets", []), osname, accel, arch)
    if not asset:
        print(f"No matching asset for {osname}/{accel} in release {tag}.", file=sys.stderr)
        print("Available:", file=sys.stderr)
        for a in rel.get("assets", []):
            print("  -", a.get("name"), file=sys.stderr)
        return 1

    name, url = asset["name"], asset["browser_download_url"]
    size = asset.get("size", 0)
    print(f"Release {tag}: downloading {name} ({size // 1024 // 1024} MB)…")

    with tempfile.TemporaryDirectory() as tmp:
        arc_path = os.path.join(tmp, name)
        _download(url, arc_path, size)
        extract_dir = os.path.join(tmp, "x")
        if name.endswith(".tar.gz"):
            import tarfile

            with tarfile.open(arc_path, "r:gz") as tf:
                tf.extractall(extract_dir)
        else:
            with zipfile.ZipFile(arc_path) as zf:
                zf.extractall(extract_dir)

        # Find llama-server(.exe) anywhere in the archive.
        exe_name = "llama-server.exe" if osname == "Windows" else "llama-server"
        found = None
        for root, _dirs, files in os.walk(extract_dir):
            if exe_name in files:
                found = os.path.join(root, exe_name)
                break
        if not found:
            print(f"'{exe_name}' not found inside {name}.", file=sys.stderr)
            return 1

        suffix = ".exe" if osname == "Windows" else ""
        dest = os.path.join(out_dir, f"llama-server-{triple}{suffix}")
        shutil.copy2(found, dest)
        # Copy the runtime libs next to the binary. Match VERSIONED shared
        # objects too (e.g. libllama-common.so.0) — the libs' SONAMEs are
        # versioned, so copying only bare `.so` names leaves the loader unable to
        # resolve them. Preserve symlinks so the real lib + its SONAME alias both
        # land (the binary's RUNPATH is $ORIGIN, so same-dir is enough).
        def _is_lib(n: str) -> bool:
            low = n.lower()
            return low.endswith((".dll", ".dylib", ".metal")) or ".so" in low

        src_dir = os.path.dirname(found)
        copied = 0
        for f in os.listdir(src_dir):
            if f == exe_name or not _is_lib(f):
                continue
            src = os.path.join(src_dir, f)
            dst = os.path.join(out_dir, f)
            if os.path.islink(src):
                target = os.readlink(src)
                if os.path.lexists(dst):
                    os.remove(dst)
                os.symlink(target, dst)
            else:
                shutil.copy2(src, dst)
            copied += 1
        if osname != "Windows":
            os.chmod(dest, 0o755)

    print(f"\n✓ Installed sidecar: {dest}")
    if copied:
        print(f"  + {copied} runtime libs copied to {out_dir}")

    # Vendor the HF→GGUF converter so activating a trained adapter
    # (serve_prep.py) needs no network. Pinned to a tag where the converter is a
    # SELF-CONTAINED single file (newer tags split it into a multi-file package
    # that can't be vendored standalone) — kept in sync with serve_prep.py.
    # Best-effort: serve_prep falls back to fetching it on demand if this fails.
    CONVERT_TAG = "b6000"
    conv_dest = os.path.join(out_dir, "convert_hf_to_gguf.py")
    conv_url = (
        f"https://raw.githubusercontent.com/{REPO}/{CONVERT_TAG}/convert_hf_to_gguf.py"
    )
    try:
        with _get(conv_url) as resp, open(conv_dest, "wb") as fh:
            shutil.copyfileobj(resp, fh)
        print(f"  + vendored GGUF converter ({CONVERT_TAG}): {conv_dest}")
    except Exception as exc:  # noqa: BLE001
        print(f"  (skipped vendoring convert_hf_to_gguf.py: {exc})", file=sys.stderr)

    # Auto-wire externalBin so `tauri build` bundles it (only now that it exists).
    conf_path = os.path.join(repo_root, "src-tauri", "tauri.conf.json")
    try:
        with open(conf_path, "r", encoding="utf-8") as fh:
            conf = json.load(fh)
        bundle = conf.setdefault("bundle", {})
        ext = bundle.setdefault("externalBin", [])
        if "binaries/llama-server" not in ext:
            ext.append("binaries/llama-server")
            with open(conf_path, "w", encoding="utf-8") as fh:
                json.dump(conf, fh, indent=2)
                fh.write("\n")
            print('  + wired "externalBin": ["binaries/llama-server"] into tauri.conf.json')
        else:
            print('  externalBin already wired in tauri.conf.json')
    except Exception as exc:  # noqa: BLE001
        print(f'  (could not auto-edit tauri.conf.json: {exc}); add "externalBin": ["binaries/llama-server"] manually')

    print('Set the llama-server path to "sidecar" in the app Settings to use it.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
