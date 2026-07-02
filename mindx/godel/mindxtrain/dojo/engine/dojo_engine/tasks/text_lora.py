"""LoRA training for text / language models — real PEFT loop with sim fallback."""

from __future__ import annotations

import sys

from .. import events
from ..runtime import Runtime
from .base import BaseTrainer


class TextLoraTrainer(BaseTrainer):
    label = "Text LoRA"
    group_key = "text_lora"

    def describe(self) -> None:
        super().describe()
        events.log(f"LoRA rank r={self.config.get('rank', 8)}, alpha={self.config.get('alpha', 16)}")

    def train_real(self, rt: Runtime) -> None:
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer

        base = self.job.get("base_model")
        rank = int(self.config.get("rank", 8) or 8)
        alpha = int(self.config.get("alpha", 16) or 16)
        target = self.extra.get("target_modules")
        target_modules = (
            [m.strip() for m in target.split(",")] if isinstance(target, str) and target else None
        )

        texts = self.load_texts()
        events.log(f"Loaded {len(texts)} training examples")

        tok = AutoTokenizer.from_pretrained(base)
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token or tok.unk_token

        use_amp = rt.device == "cuda" and rt.dtype == "float16"
        model = AutoModelForCausalLM.from_pretrained(
            base, torch_dtype=torch.float16 if use_amp else torch.float32
        ).to(rt.device)

        lcfg = LoraConfig(
            r=rank,
            lora_alpha=alpha,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=target_modules,  # None → PEFT infers from the architecture
        )
        model = get_peft_model(model, lcfg)
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total = sum(p.numel() for p in model.parameters())
        events.log(f"Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.3f}%)")

        batches = self.text_batches(texts, tok, tok.pad_token_id)
        if not batches:
            raise RuntimeError("No batches produced from the dataset")
        total_steps = self.epochs * len(batches)
        events.log(f"{len(batches)} batches/epoch · {total_steps} steps total")

        optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=self.learning_rate)
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
                input_ids = input_ids.to(rt.device)
                attn = attn.to(rt.device)
                labels = labels.to(rt.device)
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                    out = model(input_ids=input_ids, attention_mask=attn, labels=labels)
                    loss = out.loss
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()

                step += 1
                last_loss = float(loss.detach().float().item())
                events.progress(step=step, total=total_steps, epoch=epoch, loss=last_loss, lr=self.learning_rate)

        model.save_pretrained(self.output_dir)
        tok.save_pretrained(self.output_dir)
        summary = {"final_loss": round(last_loss, 6), "total_steps": total_steps, "epochs": self.epochs,
                   "trainable_params": trainable}
        events.log(f"Saved LoRA adapter to {self.output_dir}")
        print(f"[text_lora] adapter saved to {self.output_dir}", file=sys.stderr)
        events.done(artifact=self.output_dir, mode="real", device=rt.device, backend=rt.backend, **summary)
