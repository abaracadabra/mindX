"""Prepare a trained LoRA adapter for serving by llama.cpp's ``llama-server``.

``llama-server`` speaks GGUF, but a finetune under ``outputs/`` is a PEFT adapter
(``adapter_config.json`` + ``adapter_model.safetensors``) on top of a base model.
This module bridges the gap: it merges the adapter into its base and converts the
result to a single self-contained GGUF the sidecar can serve with just ``-m``.

    python -m dojo_engine.serve_prep --adapter outputs/codephreak-qwen3

Emits newline-delimited JSON events (the ``events.py`` protocol) so the host can
show a live progress bar, and prints a final ``done`` event whose ``artifact`` is
the GGUF path. Results are cached next to the adapter so re-selecting a model is
instant — a second run with the GGUF already present returns immediately.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

from . import events

# The HF→GGUF converter. Pinned to b6000 — a recent llama.cpp tag where
# convert_hf_to_gguf.py is still a SELF-CONTAINED single file (later tags split
# it into an 81-module `conversion/` package, and b6500 added a hard
# mistral_common import) while already supporting Qwen3 / Qwen3-MoE and needing
# no extra deps beyond gguf/sentencepiece. Override with DOJO_LLAMA_TAG.
CONVERT_TAG = os.environ.get("DOJO_LLAMA_TAG", "b6000")
CONVERT_URL = (
    "https://raw.githubusercontent.com/ggml-org/llama.cpp/"
    f"{CONVERT_TAG}/convert_hf_to_gguf.py"
)
UA = {"User-Agent": "the-dojo-serveprep/0.1"}


def _read_base(adapter_dir: str) -> str:
    cfg_path = os.path.join(adapter_dir, "adapter_config.json")
    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    base = cfg.get("base_model_name_or_path")
    if not base:
        raise RuntimeError(f"adapter_config.json has no base_model_name_or_path in {adapter_dir}")
    return base


def _merge(adapter_dir: str, merged_dir: str, base: str) -> None:
    """Merge the LoRA adapter into its base and save plain HF weights."""
    # A trained adapter's base is already in the local HF cache, so default to
    # offline loads — otherwise transformers stalls on a Hub metadata check when
    # the network is down/slow. Set DOJO_SERVE_ONLINE=1 to allow a download.
    if os.environ.get("DOJO_SERVE_ONLINE") != "1":
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    events.log(f"Loading base model '{base}' (CPU merge, offline cache)…")
    model = AutoModelForCausalLM.from_pretrained(
        base, torch_dtype=torch.float32, low_cpu_mem_usage=True
    )
    events.log("Applying LoRA adapter…")
    model = PeftModel.from_pretrained(model, adapter_dir)
    events.log("Merging adapter weights into the base…")
    model = model.merge_and_unload()
    os.makedirs(merged_dir, exist_ok=True)
    model.save_pretrained(merged_dir, safe_serialization=True)
    # Tokenizer: prefer the one saved with the adapter, fall back to the base.
    try:
        tok = AutoTokenizer.from_pretrained(adapter_dir)
    except Exception:
        tok = AutoTokenizer.from_pretrained(base)
    tok.save_pretrained(merged_dir)
    events.log(f"Merged model written to {merged_dir}")


def _save_base(base: str, base_dir: str) -> None:
    """Save the *un-imprinted* base model + tokenizer (no adapter) — for serving
    a 'before the impression' car to compare against the trained actor."""
    if os.environ.get("DOJO_SERVE_ONLINE") != "1":
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    events.log(f"Loading base model '{base}' (pre-imprint, offline cache)…")
    model = AutoModelForCausalLM.from_pretrained(
        base, torch_dtype=torch.float32, low_cpu_mem_usage=True
    )
    os.makedirs(base_dir, exist_ok=True)
    model.save_pretrained(base_dir, safe_serialization=True)
    AutoTokenizer.from_pretrained(base).save_pretrained(base_dir)
    events.log(f"Base model written to {base_dir}")


def _vendored_converter() -> str | None:
    """The converter fetch_llama.py drops next to the sidecar (offline path)."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(here))  # engine/dojo_engine → repo
    cand = os.path.join(repo_root, "src-tauri", "binaries", "convert_hf_to_gguf.py")
    return cand if os.path.exists(cand) else None


def _ensure_converter_deps() -> None:
    """convert_hf_to_gguf.py needs ``gguf`` plus, for some tokenizers,
    ``sentencepiece`` and ``protobuf``. Install whatever's missing into the venv
    (the converter runs under this same interpreter)."""
    need = []
    for mod, pkg in (("gguf", "gguf"), ("sentencepiece", "sentencepiece"),
                     ("google.protobuf", "protobuf")):
        try:
            __import__(mod)
        except Exception:
            need.append(pkg)
    if need:
        events.log(f"Installing converter deps ({', '.join(need)})…")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", *need],
            check=True,
        )


def _ensure_converter(cache_dir: str) -> str:
    """Locate (or fetch) llama.cpp's convert_hf_to_gguf.py and ensure ``gguf``.

    Resolution order: ``DOJO_LLAMA_CONVERT`` override → the copy vendored beside
    the sidecar by fetch_llama.py (no network) → a previously cached download →
    fetching it on demand. ``gguf`` is ensured for *every* path.
    """
    _ensure_converter_deps()  # required regardless of which converter we use
    override = os.environ.get("DOJO_LLAMA_CONVERT")
    if override and os.path.exists(override):
        return override
    vendored = _vendored_converter()
    if vendored:
        events.log(f"Using vendored GGUF converter: {vendored}")
        return vendored
    os.makedirs(cache_dir, exist_ok=True)
    script = os.path.join(cache_dir, "convert_hf_to_gguf.py")
    if not os.path.exists(script):
        events.log(f"Fetching GGUF converter ({CONVERT_TAG})…")
        try:
            with urlopen(Request(CONVERT_URL, headers=UA), timeout=60) as resp, open(script, "wb") as fh:
                fh.write(resp.read())
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "Couldn't fetch the GGUF converter and none is vendored. "
                "Run the sidecar fetch once with a network connection "
                "(.venv/bin/python scripts/fetch_llama.py) to vendor it, or set "
                f"DOJO_LLAMA_CONVERT to a local convert_hf_to_gguf.py. ({exc})"
            ) from exc
    return script


def _convert(merged_dir: str, out_gguf: str, cache_dir: str, outtype: str) -> None:
    script = _ensure_converter(cache_dir)
    events.log(f"Converting to GGUF ({outtype})…")
    proc = subprocess.run(
        [sys.executable, script, merged_dir, "--outfile", out_gguf, "--outtype", outtype],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-12:]
        raise RuntimeError("convert_hf_to_gguf.py failed:\n" + "\n".join(tail))
    if not os.path.exists(out_gguf):
        raise RuntimeError(f"converter reported success but {out_gguf} is missing")


def prepare(adapter_dir: str, outtype: str = "q8_0", force: bool = False, base_only: bool = False) -> str:
    adapter_dir = os.path.abspath(adapter_dir)
    if not os.path.isdir(adapter_dir):
        raise RuntimeError(f"Not a directory: {adapter_dir}")
    name = os.path.basename(adapter_dir.rstrip(os.sep))
    work = os.path.join(adapter_dir, ".gguf")
    cache_dir = os.path.join(work, "tools")
    # base_only → the un-imprinted base model, for before/after comparison.
    out_gguf = os.path.join(work, f"{name}{'-base' if base_only else ''}.{outtype}.gguf")

    # Cache hit: GGUF already built → serve it straight away.
    if os.path.exists(out_gguf) and not force:
        events.log(f"Using cached GGUF: {out_gguf}")
        events.done(artifact=out_gguf, summary={"cached": True, "base_only": base_only})
        return out_gguf

    base = _read_base(adapter_dir)

    if base_only:
        events.log(f"Preparing the PRE-IMPRINT base of '{name}' (base: {base})")
        base_dir = os.path.join(work, "base-hf")
        if not os.path.exists(os.path.join(base_dir, "config.json")) or force:
            _save_base(base, base_dir)
        else:
            events.log(f"Reusing base weights at {base_dir}")
        _convert(base_dir, out_gguf, cache_dir, outtype)
        events.log(f"✓ Base GGUF ready: {out_gguf}")
        events.done(artifact=out_gguf, summary={"base": base, "outtype": outtype, "base_only": True})
        return out_gguf

    events.log(f"Preparing '{name}' (base: {base}) for the llama.cpp sidecar")
    merged_dir = os.path.join(work, "merged-hf")
    if not os.path.exists(os.path.join(merged_dir, "config.json")) or force:
        _merge(adapter_dir, merged_dir, base)
    else:
        events.log(f"Reusing merged weights at {merged_dir}")

    _convert(merged_dir, out_gguf, cache_dir, outtype)
    events.log(f"✓ GGUF ready: {out_gguf}")
    events.done(artifact=out_gguf, summary={"base": base, "outtype": outtype})
    return out_gguf


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Prepare a trained adapter as a GGUF for llama.cpp.")
    p.add_argument("--adapter", required=True, help="path to the trained adapter dir")
    p.add_argument("--outtype", default="q8_0", help="GGUF quant: f16 | q8_0 | q4_k_m …")
    p.add_argument("--force", action="store_true", help="rebuild even if a cached GGUF exists")
    p.add_argument("--base-only", dest="base_only", action="store_true",
                   help="serve the un-imprinted base model (pre-impression) for comparison")
    args = p.parse_args(argv)
    try:
        prepare(args.adapter, outtype=args.outtype, force=args.force, base_only=args.base_only)
        return 0
    except Exception as exc:  # noqa: BLE001
        events.error(f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
