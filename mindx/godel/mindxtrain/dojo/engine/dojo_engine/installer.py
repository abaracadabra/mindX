"""Platform/GPU-aware installer for the real training stack.

Installs the correct PyTorch per vendor/OS (it must NOT come from PyPI, or pip
silently pulls a CPU-only wheel), then the engine deps. Targets:

  rocm-windows  AMD on Windows  — repo.radeon.com rocm_sdk wheels + torch+rocm
                                  (needs Python 3.12 / cp312, driver 26.2.2+)
  rocm-linux    AMD on Linux    — pytorch.org ROCm index
  cuda          NVIDIA          — pytorch.org CUDA index
  cpu           no GPU          — pytorch.org CPU index

  python -m dojo_engine.installer --recommend
  python -m dojo_engine.installer --install --target auto
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys

from . import events

# Pinned versions that are known to work together (see skybreaker's notes).
ROCM_VER = "7.2.1"
TORCH_VER = "2.9.1"
TORCHVISION_VER = "0.24.1"
CUDA_INDEX = "https://download.pytorch.org/whl/cu126"
ROCM_LINUX_INDEX = "https://download.pytorch.org/whl/rocm6.2"
CPU_INDEX = "https://download.pytorch.org/whl/cpu"

# Non-torch deps for the full text + image + embedding stack.
ENGINE_DEPS = [
    "transformers<5",
    "peft",
    "datasets",
    "accelerate",
    "diffusers>=0.38,<0.39",
    "safetensors",
    "sentence-transformers",
    "pillow",
    "numpy",
    "einops",
]

VALID_TARGETS = {"rocm-windows", "rocm-linux", "cuda", "cpu"}


def _has_nvidia() -> bool:
    if shutil.which("nvidia-smi"):
        return True
    return _name_contains(("nvidia", "geforce", "quadro", "rtx", "tesla"))


def _has_amd() -> bool:
    if shutil.which("rocminfo") or shutil.which("rocm-smi"):
        return True
    return _name_contains(("radeon", "amd", "gfx"))


def _name_contains(needles: tuple[str, ...]) -> bool:
    """Best-effort GPU name probe across OSes."""
    names = ""
    try:
        if platform.system() == "Windows":
            out = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                capture_output=True, text=True, timeout=10,
            )
            names = out.stdout.lower()
        elif platform.system() == "Linux":
            out = subprocess.run(["lspci"], capture_output=True, text=True, timeout=10)
            names = out.stdout.lower()
    except Exception:
        return False
    return any(n in names for n in needles)


def recommend() -> str:
    system = platform.system()
    if _has_nvidia():
        return "cuda"
    if _has_amd():
        return "rocm-windows" if system == "Windows" else "rocm-linux"
    return "cpu"


def _torch_commands(target: str) -> list[list[str]]:
    """pip command(s) that install torch for a target, in the order that works."""
    pip = [sys.executable, "-m", "pip", "install", "--no-cache-dir"]
    if target == "rocm-windows":
        base = f"https://repo.radeon.com/rocm/windows/rocm-rel-{ROCM_VER}"
        return [
            [*pip,
             f"{base}/rocm_sdk_core-{ROCM_VER}-py3-none-win_amd64.whl",
             f"{base}/rocm_sdk_devel-{ROCM_VER}-py3-none-win_amd64.whl",
             f"{base}/rocm_sdk_libraries_custom-{ROCM_VER}-py3-none-win_amd64.whl",
             f"{base}/rocm-{ROCM_VER}.tar.gz"],
            [*pip,
             f"{base}/torch-{TORCH_VER}%2Brocm{ROCM_VER}-cp312-cp312-win_amd64.whl",
             f"{base}/torchvision-{TORCHVISION_VER}%2Brocm{ROCM_VER}-cp312-cp312-win_amd64.whl"],
        ]
    if target == "rocm-linux":
        return [[*pip, "torch", "torchvision", "--index-url", ROCM_LINUX_INDEX]]
    if target == "cuda":
        return [[*pip, "torch", "torchvision", "--index-url", CUDA_INDEX]]
    return [[*pip, "torch", "torchvision", "--index-url", CPU_INDEX]]


def _run(cmd: list[str]) -> int:
    events.log("$ " + " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            events.log(line)
    return proc.wait()


def install(target: str) -> int:
    if target == "auto":
        target = recommend()
        events.log(f"Auto-selected install target: {target}")
    if target not in VALID_TARGETS:
        events.error(f"Unknown target {target!r}. One of: {', '.join(sorted(VALID_TARGETS))}")
        return 2

    if target == "rocm-windows":
        pyver = f"{sys.version_info.major}.{sys.version_info.minor}"
        if pyver != "3.12":
            events.error(
                f"ROCm-on-Windows wheels are cp312 only; this Python is {pyver}. "
                "Use a Python 3.12 interpreter (set it in Settings)."
            )
            return 2
        events.log("Removing any existing torch (avoids the CPU-wheel trap)...")
        _run([sys.executable, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"])

    events.log(f"Installing PyTorch for target '{target}'...")
    for cmd in _torch_commands(target):
        if _run(cmd) != 0:
            events.error("PyTorch install step failed — see log above.")
            return 1

    events.log("Installing engine dependencies...")
    if _run([sys.executable, "-m", "pip", "install", "--no-cache-dir", *ENGINE_DEPS]) != 0:
        events.error("Engine dependency install failed.")
        return 1

    # Verify the GPU is actually visible (for GPU targets).
    events.log("Verifying installation...")
    check = (
        "import torch;"
        "ok=torch.cuda.is_available();"
        "print('torch', torch.__version__);"
        "print('cuda_available', ok);"
        "print('device', torch.cuda.get_device_name(0) if ok else 'cpu')"
    )
    _run([sys.executable, "-c", check])

    events.done(artifact=None, target=target, summary={"installed": True})
    return 0


def install_vllm(isolated: bool = True) -> int:
    """Install the vLLM inference engine.

    The PyPI ``vllm`` wheel is built against CUDA and **pins its own torch**, so
    installing it into the Dojo's main venv would clobber the training/serving
    torch (e.g. a ROCm or CPU build). By default we install into an **isolated**
    venv (``.venv-vllm`` next to ``.venv``) so the training stack is never touched;
    the Dojo points its vLLM runtime at that venv's ``vllm`` binary. Pass
    ``isolated=False`` to force the (unsafe) same-venv install.
    """
    import os

    if not isolated:
        events.log("Installing vLLM into the MAIN venv (may replace the training torch)…")
        if _run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "vllm"]) != 0:
            events.error("vLLM install failed — see log above (docs.vllm.ai for ROCm/CPU builds).")
            return 1
        events.done(artifact=None, target="vllm", summary={"installed": True, "isolated": False})
        return 0

    # repo root = engine/dojo_engine/installer.py → up 3
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    venv = os.path.join(root, ".venv-vllm")
    bindir = "Scripts" if os.name == "nt" else "bin"
    py = os.path.join(venv, bindir, "python.exe" if os.name == "nt" else "python")
    vllm_bin = os.path.join(venv, bindir, "vllm.exe" if os.name == "nt" else "vllm")

    events.log(f"Creating isolated vLLM venv at {venv} (keeps the training torch safe)…")
    if not os.path.exists(py) and _run([sys.executable, "-m", "venv", venv]) != 0:
        events.error("Could not create the isolated vLLM venv.")
        return 1
    _run([py, "-m", "pip", "install", "--upgrade", "pip"])
    events.log("Installing vLLM into the isolated venv (CUDA-oriented; large download)…")
    if _run([py, "-m", "pip", "install", "--no-cache-dir", "vllm"]) != 0:
        events.error(
            "vLLM install failed — the PyPI build targets CUDA; on ROCm/CPU you need a "
            "platform-specific build (docs.vllm.ai). The main training venv is untouched."
        )
        return 1
    events.log(f"Point the app's vLLM command at: {vllm_bin}  (Settings → vLLM command)")
    events.done(artifact=vllm_bin, target="vllm", summary={"installed": True, "isolated": True, "command": vllm_bin})
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dojo_engine.installer")
    p.add_argument("--recommend", action="store_true")
    p.add_argument("--install", action="store_true")
    p.add_argument("--vllm", action="store_true", help="install the vLLM inference engine (isolated venv by default)")
    p.add_argument("--vllm-same-venv", dest="vllm_same_venv", action="store_true",
                   help="install vLLM into the MAIN venv instead of an isolated one (may clobber torch)")
    p.add_argument("--target", default="auto")
    args = p.parse_args(argv)

    if args.recommend:
        print(recommend())
        return 0
    if args.vllm:
        return install_vllm(isolated=not args.vllm_same_venv)
    if args.install:
        return install(args.target)
    p.error("one of --recommend, --install or --vllm is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
