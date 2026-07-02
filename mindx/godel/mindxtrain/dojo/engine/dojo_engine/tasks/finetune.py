"""Full / partial fine-tuning for text or image models — real loop + fallback."""

from __future__ import annotations

import sys

from .. import events
from ..runtime import Runtime
from .base import BaseTrainer


class FinetuneTrainer(BaseTrainer):
    label = "Fine-tune"
    artifact_name = "finetune_run.json"

    @property
    def group_key(self) -> str:
        return "image_finetune" if self.job.get("modality") == "image" else "text_finetune"

    def describe(self) -> None:
        super().describe()
        freeze = self.extra.get("freeze_layers")
        events.log(f"Frozen layers: {freeze}" if freeze else "Full-weight fine-tune (no frozen layers)")

    def train_real(self, rt: Runtime) -> None:
        if self.job.get("modality") == "image":
            from . import _image

            _image.train_unet(self, rt, use_lora=False)
            return
        self._train_text(rt)

    def _train_text(self, rt: Runtime) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        base = self.job.get("base_model")
        texts = self.load_texts()
        events.log(f"Loaded {len(texts)} training examples")

        tok = AutoTokenizer.from_pretrained(base)
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token or tok.unk_token

        use_amp = rt.device == "cuda" and rt.dtype == "float16"
        model = AutoModelForCausalLM.from_pretrained(
            base, torch_dtype=torch.float16 if use_amp else torch.float32
        ).to(rt.device)

        # Optional partial freeze: keep only the last N transformer blocks trainable.
        freeze_n = int(self.extra.get("freeze_layers", 0) or 0)
        if freeze_n > 0:
            for p in model.parameters():
                p.requires_grad = False
            tail = [m for m in model.modules() if hasattr(m, "weight")][-freeze_n * 4 :]
            for m in tail:
                for p in m.parameters():
                    p.requires_grad = True

        batches = self.text_batches(texts, tok, tok.pad_token_id)
        if not batches:
            raise RuntimeError("No batches produced from the dataset")
        total_steps = self.epochs * len(batches)

        params = [p for p in model.parameters() if p.requires_grad]
        events.log(f"Trainable params: {sum(p.numel() for p in params):,}")
        optimizer = torch.optim.AdamW(params, lr=self.learning_rate)
        from ..runtime import grad_scaler

        scaler = grad_scaler(use_amp)
        model.train()

        import random as _random

        step = 0
        last_loss = 0.0
        for epoch in range(1, self.epochs + 1):
            events.log(f"=== Epoch {epoch}/{self.epochs} ===")
            _random.shuffle(batches)
            for input_ids, attn, labels in batches:
                input_ids, attn, labels = input_ids.to(rt.device), attn.to(rt.device), labels.to(rt.device)
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                    loss = model(input_ids=input_ids, attention_mask=attn, labels=labels).loss
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
                step += 1
                last_loss = float(loss.detach().float().item())
                events.progress(step=step, total=total_steps, epoch=epoch, loss=last_loss, lr=self.learning_rate)

        model.save_pretrained(self.output_dir)
        tok.save_pretrained(self.output_dir)
        print(f"[finetune] model saved to {self.output_dir}", file=sys.stderr)
        events.done(
            artifact=self.output_dir,
            mode="real",
            device=rt.device,
            backend=rt.backend,
            final_loss=round(last_loss, 6),
            total_steps=total_steps,
        )
