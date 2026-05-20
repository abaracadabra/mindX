"""Scaled-dot-product-attention microbenchmark — the one *real* probe.

If torch + a GPU are available, this times ``scaled_dot_product_attention``
across four representative shapes on the two candidate backends for the detected
vendor and picks the faster one. If torch is missing (typical CPU dev box) or
no GPU is visible, it returns the canonical default for the profile with an
empty timing list, so ``--dry-run`` parity holds and downstream consumers keep
working unchanged.

Vendor → candidate backends:

  * AMD/ROCm   : ``flash_ck`` (Composable Kernel via AITER) vs ``flash_triton``
                 (AOTriton). The ROCm SDPA dispatcher maps these onto
                 ``SDPBackend.FLASH_ATTENTION`` / ``SDPBackend.MATH`` with the
                 appropriate env toggles; we approximate the comparison with the
                 flash vs math kernels.
  * NVIDIA/CUDA: ``flash_cuda`` (``SDPBackend.FLASH_ATTENTION``) vs
                 ``mem_efficient`` (``SDPBackend.EFFICIENT_ATTENTION``).
  * CPU        : ``math`` only — no benchmark, returned directly.

Extracted and generalized from the mindXtrain hackathon project
(Professor-Codephreak/mindXtrain). Apache-2.0.
"""

from __future__ import annotations

import importlib.util
import time

from autotune.plan import AttentionBackend, ProbeTiming
from autotune.profile import HardwareProfile, detect_hardware

_SHAPES = [
    # (batch, seqlen, num_heads, head_dim)
    (1, 2048, 32, 128),
    (1, 4096, 32, 128),
    (1, 8192, 16, 128),
    (1, 16384, 8, 128),
]


def _torch_available() -> bool:
    return importlib.util.find_spec("torch") is not None


def _candidates(profile: HardwareProfile) -> tuple[AttentionBackend, AttentionBackend] | None:
    """Return the (a, b) backend pair to race for this vendor, or None for CPU."""
    if profile.vendor == "amd":
        return ("flash_ck", "flash_triton")
    if profile.vendor == "nvidia":
        return ("flash_cuda", "mem_efficient")
    return None


def _sdp_backends_for(name: AttentionBackend):
    """Map a logical backend name onto a list of ``torch.nn.attention.SDPBackend``."""
    from torch.nn.attention import SDPBackend

    if name in ("flash_ck", "flash_cuda"):
        return [SDPBackend.FLASH_ATTENTION]
    if name == "flash_triton":
        # AOTriton path is exposed through the math/flash dispatcher on ROCm;
        # we use MATH here as the contrasting kernel for the race.
        return [SDPBackend.MATH]
    if name == "mem_efficient":
        return [SDPBackend.EFFICIENT_ATTENTION]
    return [SDPBackend.MATH]


def _time_backend(name: AttentionBackend, *, iterations: int = 5) -> ProbeTiming:
    import torch
    from torch.nn.attention import sdpa_kernel

    backends = _sdp_backends_for(name)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32

    timings: list[float] = []
    for batch, seqlen, heads, head_dim in _SHAPES:
        q = torch.randn(batch, heads, seqlen, head_dim, device=device, dtype=dtype)
        k = torch.randn(batch, heads, seqlen, head_dim, device=device, dtype=dtype)
        v = torch.randn(batch, heads, seqlen, head_dim, device=device, dtype=dtype)

        with sdpa_kernel(backends=backends):
            for _ in range(2):  # warmup
                _ = torch.nn.functional.scaled_dot_product_attention(q, k, v)
        if device == "cuda":
            torch.cuda.synchronize()

        t0 = time.perf_counter()
        with sdpa_kernel(backends=backends):
            for _ in range(iterations):
                _ = torch.nn.functional.scaled_dot_product_attention(q, k, v)
        if device == "cuda":
            torch.cuda.synchronize()
        timings.append((time.perf_counter() - t0) * 1000.0 / iterations)

    median_ms = sorted(timings)[len(timings) // 2]
    return ProbeTiming(
        label=f"sdpa-{name}",
        backend=name,
        median_ms=float(median_ms),
        iterations=iterations,
    )


def probe_attention(
    device_index: int = 0,
    profile: HardwareProfile | None = None,
) -> tuple[AttentionBackend, list[ProbeTiming]]:
    """Pick the faster SDPA backend for the detected (or supplied) hardware.

    Returns ``("math", [])`` on a torch-less / GPU-less box.
    """
    profile = profile or detect_hardware(device_index)

    pair = _candidates(profile)
    if pair is None:
        return "math", []
    if not _torch_available():
        return pair[0], []

    try:  # pragma: no cover - only on a real GPU box
        a_timing = _time_backend(pair[0])
        b_timing = _time_backend(pair[1])
    except (RuntimeError, ImportError):
        return pair[0], []

    timings = [a_timing, b_timing]
    winner: AttentionBackend = pair[0] if a_timing.median_ms <= b_timing.median_ms else pair[1]
    return winner, timings


__all__ = ["probe_attention"]
