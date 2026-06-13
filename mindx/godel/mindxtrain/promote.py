"""promote — LoRA -> Modelfile -> Ollama: the next generation becomes servable.

After the dcoach proof gate accepts a trained generation, this turns the LoRA
into an Ollama model so mindX's existing inference layer can serve the wiser
mind. Two paths:

  1. PREFERRED — mindXtrain v1.0.0 ships a "LoRA -> Modelfile -> Ollama"
     pipeline. If a verb/flag exposes it, drive it through the bridge.
  2. FALLBACK — construct a Modelfile (FROM <ollama base> + ADAPTER <lora>) and
     run `ollama create`. Ollama is a SEPARATE external tool already on the box
     (not mindXtrain) so calling it directly does not violate the isolation
     contract.

The model is namespaced `mindx-gen{N}` and is NOT routed into production
inference automatically — an unproven generation is servable but not trusted
until an operator (or the autonomous flag) promotes it into the task map.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from . import CPU_BASE_OLLAMA_TAG
from . import bridge as _bridge

logger = logging.getLogger(__name__)


def _find_lora_dir(weights_path: str) -> Optional[Path]:
    """Locate the adapter dir under the run output (best-effort)."""
    root = Path(weights_path)
    if not root.exists():
        return None
    for cand in (root, root / "adapter", root / "lora", root / "checkpoint"):
        if cand.exists() and any(cand.glob("adapter_*")) or (cand / "adapter_config.json").exists():
            return cand
    # any subdir containing an adapter_config.json
    for p in root.rglob("adapter_config.json"):
        return p.parent
    return root if root.exists() else None


async def promote_to_ollama(
    cap,
    fr,
    weights_path: str,
    generation: int,
    *,
    served_name: Optional[str] = None,
    base_ollama_tag: str = CPU_BASE_OLLAMA_TAG,
) -> dict:
    """Create an Ollama model from the trained LoRA. Returns {ok, model_name, ...}."""
    model_name = served_name or f"mindx-gen{generation}"

    # 1. Preferred: mindXtrain's own pipeline, if a verb exposes a modelfile/
    #    ollama emit. Probe flags rather than guess.
    for verb in ("quantize", "serve", "deploy"):
        if verb in (cap.verbs or ()):
            flags = _bridge.discover_verb_flags(verb, cap)
            if any(f in flags for f in ("--ollama", "--modelfile", "--gguf")):
                args = [verb]
                if "--ollama" in flags:
                    args += ["--ollama", model_name]
                res = _bridge.run_cli(args, cap=cap, cwd=Path(weights_path).parent, timeout=1800)
                if res.get("ok"):
                    return {"ok": True, "model_name": model_name, "via": f"mindxtrain {verb}",
                            "stdout": (res.get("stdout") or "")[:400]}
                logger.info("mindXtrain %s ollama path failed, falling back: %s", verb, res.get("stderr", "")[:200])
                break

    # 2. Fallback: build a Modelfile + `ollama create`.
    if not shutil.which("ollama"):
        return {"ok": False, "reason": "ollama not on PATH and no mindXtrain ollama verb"}
    lora_dir = _find_lora_dir(weights_path)
    if lora_dir is None:
        return {"ok": False, "reason": f"no LoRA adapter found under {weights_path}"}
    modelfile = Path(weights_path) / "Modelfile"
    system = (f"You are mindX generation {generation}, fine-tuned on your own "
              f"consolidated dream wisdom (knowledge->wisdom->weights).")
    try:
        modelfile.write_text(
            f"FROM {base_ollama_tag}\n"
            f"ADAPTER {lora_dir}\n"
            f'SYSTEM """{system}"""\n',
            encoding="utf-8",
        )
    except Exception as e:
        return {"ok": False, "reason": f"could not write Modelfile: {e}"}
    try:
        proc = subprocess.run(
            ["ollama", "create", model_name, "-f", str(modelfile)],
            capture_output=True, text=True, timeout=1800,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"ok": False, "reason": f"ollama create failed: {e}"}
    if proc.returncode != 0:
        return {"ok": False, "reason": "ollama create non-zero",
                "stderr": (proc.stderr or "")[:400], "modelfile": str(modelfile)}
    return {"ok": True, "model_name": model_name, "via": "ollama create",
            "modelfile": str(modelfile), "stdout": (proc.stdout or "")[:400]}
