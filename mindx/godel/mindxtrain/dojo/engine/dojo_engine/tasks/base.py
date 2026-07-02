"""Base trainer: orchestration shared by every task runner.

`run()` dispatches between **real** training (when torch + the task's deps are
installed) and a CPU-friendly **simulation** (so the app works on any machine).
Real runners override `train_real(rt)`; the simulation lives in `simulate()`.
Shared dataset helpers for the text disciplines live here too.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import time
import traceback
from typing import Any

from .. import events, runtime


class BaseTrainer:
    #: Short human label, e.g. "Text LoRA". Overridden by subclasses.
    label = "Training"
    #: File written into the output dir describing the produced adapter/model.
    artifact_name = "adapter_config.json"
    #: Dependency-group key in runtime.DEP_GROUPS gating real training.
    group_key: str | None = None

    def __init__(self, job: dict[str, Any]):
        self.job = job
        self.config = job.get("config", {}) or {}
        self.extra = self.config.get("extra") or {}
        self.output_dir = job.get("output_dir") or os.path.join(os.getcwd(), "outputs", job.get("id", "job"))

    # --- knobs ---------------------------------------------------------------

    @property
    def epochs(self) -> int:
        return max(1, int(self.config.get("epochs", 3)))

    @property
    def batch_size(self) -> int:
        return max(1, int(self.config.get("batch_size", 4)))

    @property
    def learning_rate(self) -> float:
        return float(self.config.get("learning_rate", 1e-4))

    @property
    def max_seq_len(self) -> int:
        return int(self.extra.get("max_seq_len", 256))

    @property
    def steps_per_epoch(self) -> int:
        return max(1, int(self.extra.get("steps_per_epoch", 40)))

    @property
    def step_delay(self) -> float:
        return float(self.extra.get("step_delay", 0.08))

    # --- lifecycle hooks (override these) ------------------------------------

    def describe(self) -> None:
        events.log(f"Starting {self.label} run '{self.job.get('name')}'")
        events.log(
            f"base_model={self.job.get('base_model')!r}  dataset={self.job.get('dataset_path')!r}"
        )
        events.log(f"epochs={self.epochs} batch_size={self.batch_size} lr={self.learning_rate:g}")

    def train_real(self, rt: "runtime.Runtime") -> None:
        """Real training. Overridden by runners that support it."""
        raise NotImplementedError

    # --- shared text dataset helpers (used by text_* runners) ----------------

    def load_texts(self, limit: int | None = None) -> list[str]:
        """Load a list of training strings from the dataset path.

        Supports a `.jsonl` file (fields tried: text / content / a prompt+completion
        pair), a `.txt` file (one example per line), or — when the path is missing —
        a small synthetic corpus so a real run can still complete (with a warning).
        """
        path = self.job.get("dataset_path") or ""
        texts: list[str] = []
        if path and os.path.isfile(path):
            lower = path.lower()
            if lower.endswith(".jsonl"):
                with open(path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            texts.append(line)
                            continue
                        texts.append(self._text_from_obj(obj))
            else:  # treat as plain text, one example per line
                with open(path, "r", encoding="utf-8") as fh:
                    texts = [ln.strip() for ln in fh if ln.strip()]
        if not texts:
            events.log(
                f"No usable dataset at {path!r} — using a small synthetic corpus so the run can "
                "complete. Point at a .jsonl/.txt file for real data.",
                level="warn",
            )
            texts = _SYNTHETIC_CORPUS * 8
        texts = [t for t in texts if t]
        return texts[:limit] if limit else texts

    @staticmethod
    def _text_from_obj(obj: Any) -> str:
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            for key in ("text", "content", "output"):
                if isinstance(obj.get(key), str):
                    return obj[key]
            if isinstance(obj.get("prompt"), str):
                return obj["prompt"] + (obj.get("completion") or "")
            if isinstance(obj.get("messages"), list):
                return "\n".join(str(m.get("content", "")) for m in obj["messages"])
        return json.dumps(obj)

    def text_batches(self, texts: list[str], tokenizer, pad_id: int):
        """Yield (input_ids, attention_mask, labels) tensors, per-batch padded."""
        import torch  # local import; only reached in real mode

        encoded = tokenizer(
            texts, truncation=True, max_length=self.max_seq_len, padding=False
        )["input_ids"]
        bs = self.batch_size
        batches = []
        for i in range(0, len(encoded), bs):
            chunk = [seq for seq in encoded[i : i + bs] if seq]
            if not chunk:
                continue
            width = max(len(s) for s in chunk)
            input_ids, attn, labels = [], [], []
            for seq in chunk:
                pad = width - len(seq)
                input_ids.append(seq + [pad_id] * pad)
                attn.append([1] * len(seq) + [0] * pad)
                labels.append(seq + [-100] * pad)  # ignore pad in the loss
            batches.append(
                (
                    torch.tensor(input_ids, dtype=torch.long),
                    torch.tensor(attn, dtype=torch.long),
                    torch.tensor(labels, dtype=torch.long),
                )
            )
        return batches

    def save_descriptor(self, summary: dict[str, Any], extra: dict | None = None) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, "dojo_run.json")
        descriptor = {
            "dojo_version": "0.1.0",
            "task": self.job.get("task"),
            "modality": self.job.get("modality"),
            "base_model": self.job.get("base_model"),
            "config": self.config,
            "summary": summary,
        }
        if extra:
            descriptor.update(extra)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(descriptor, fh, indent=2)
        return path

    # --- simulation ----------------------------------------------------------

    def prepare(self) -> None:
        dataset = self.job.get("dataset_path") or ""
        if dataset and not os.path.exists(dataset):
            events.log(f"Dataset path does not exist: {dataset!r} (simulation continues)", level="warn")

    def build_artifact(self, summary: dict[str, Any]) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, self.artifact_name)
        descriptor = {
            "dojo_version": "0.1.0",
            "task": self.job.get("task"),
            "modality": self.job.get("modality"),
            "base_model": self.job.get("base_model"),
            "config": self.config,
            "summary": summary,
            "simulated": True,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(descriptor, fh, indent=2)
        return path

    def simulate(self) -> None:
        total_steps = self.epochs * self.steps_per_epoch
        events.log(f"[simulation] Planned {total_steps} steps ({self.steps_per_epoch}/epoch)")
        global_step = 0
        last_loss = 0.0
        for epoch in range(1, self.epochs + 1):
            events.log(f"=== Epoch {epoch}/{self.epochs} ===")
            for _ in range(self.steps_per_epoch):
                global_step += 1
                time.sleep(self.step_delay)
                frac = global_step / max(1, total_steps)
                last_loss = max(0.01, 2.4 * math.exp(-3.0 * frac) + 0.15 + (random.random() - 0.5) * 0.08)
                events.progress(step=global_step, total=total_steps, epoch=epoch, loss=last_loss, lr=self.learning_rate)
        summary = {"final_loss": round(last_loss, 6), "total_steps": total_steps, "epochs": self.epochs}
        artifact = self.build_artifact(summary)
        events.log(f"Saved artifact to {artifact}")
        events.done(artifact=artifact, mode="simulation", **summary)

    # --- driver --------------------------------------------------------------

    def run(self) -> None:
        self.describe()
        rt = runtime.detect()

        if self.group_key and rt.can_run(self.group_key):
            events.log(
                f"Real training enabled — device={rt.device} ({rt.backend}), "
                f"dtype={rt.dtype}, torch={rt.torch_version}"
                + (f", gpu={rt.gpu_name}" if rt.gpu_name else "")
            )
            try:
                self.train_real(rt)
                return
            except NotImplementedError:
                events.log("Real path not implemented for this task — simulating.", level="warn")
            except Exception as exc:  # noqa: BLE001
                events.log(
                    f"Real training failed ({type(exc).__name__}: {exc}); falling back to simulation.",
                    level="warn",
                )
                traceback.print_exc(file=sys.stderr)
        else:
            if not rt.torch_available:
                events.log(
                    "PyTorch not installed — simulation mode. Install the stack from Settings to train for real.",
                    level="warn",
                )
            elif self.group_key:
                missing = [m for m in runtime.DEP_GROUPS.get(self.group_key, []) if not rt.extras.get(m)]
                events.log(f"Missing deps for real training: {', '.join(missing)} — simulation mode.", level="warn")

        self.prepare()
        self.simulate()


_SYNTHETIC_CORPUS = [
    "The dojo is where craft is sharpened through repetition.",
    "A low-rank adapter learns a small correction to a frozen model.",
    "Fine-tuning adjusts weights; LoRA adjusts a compact delta.",
    "Embeddings map meaning into vectors a machine can compare.",
    "Patience and precision turn a novice into a master.",
]
