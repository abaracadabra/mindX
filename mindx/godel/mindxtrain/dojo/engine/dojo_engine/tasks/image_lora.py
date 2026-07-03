"""LoRA training for image / diffusion models — real diffusers loop + fallback."""

from __future__ import annotations

from .. import events
from ..runtime import Runtime
from .base import BaseTrainer


class ImageLoraTrainer(BaseTrainer):
    label = "Image LoRA"
    group_key = "image_lora"
    artifact_name = "pytorch_lora_weights.descriptor.json"

    def describe(self) -> None:
        super().describe()
        events.log(f"UNet LoRA rank r={self.config.get('rank', 16)}, alpha={self.config.get('alpha', 32)}")
        events.log(f"Resolution: {self.extra.get('resolution', 512)}px")

    def train_real(self, rt: Runtime) -> None:
        from . import _image

        _image.train_unet(self, rt, use_lora=True)
