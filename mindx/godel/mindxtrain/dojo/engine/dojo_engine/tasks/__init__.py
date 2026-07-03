"""Task runners for The Dojo, selected by (task, modality)."""

from __future__ import annotations

from typing import Any

from .embeddings import EmbeddingTrainer
from .finetune import FinetuneTrainer
from .image_lora import ImageLoraTrainer
from .text_lora import TextLoraTrainer

# (task, modality) -> trainer class. Embeddings share one runner that adapts to
# modality internally.
_REGISTRY = {
    ("lora", "text"): TextLoraTrainer,
    ("lora", "image"): ImageLoraTrainer,
    ("finetune", "text"): FinetuneTrainer,
    ("finetune", "image"): FinetuneTrainer,
    ("embedding", "text"): EmbeddingTrainer,
    ("embedding", "image"): EmbeddingTrainer,
}


def get_trainer(job: dict[str, Any]):
    key = (str(job.get("task")), str(job.get("modality")))
    trainer_cls = _REGISTRY.get(key)
    if trainer_cls is None:
        raise ValueError(f"No trainer registered for task={key[0]!r} modality={key[1]!r}")
    return trainer_cls(job)
