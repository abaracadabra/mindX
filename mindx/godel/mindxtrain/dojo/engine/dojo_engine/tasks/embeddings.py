"""Embedding builds — text encoder fine-tune (SimCSE) or image textual inversion.

Text path prefers `sentence-transformers`; if it isn't installed it falls back
to a `transformers`-only SimCSE loop (mean-pooled, in-batch negatives), so it
runs anywhere torch + transformers are present. Force the fallback with
DOJO_EMBED_BACKEND=hf.
"""

from __future__ import annotations

import importlib.util
import os
import sys

from .. import events
from ..runtime import Runtime
from .base import BaseTrainer


class EmbeddingTrainer(BaseTrainer):
    label = "Embedding"
    artifact_name = "embedding.json"

    @property
    def group_key(self) -> str:
        return "image_embedding" if self.job.get("modality") == "image" else "text_embedding"

    def describe(self) -> None:
        super().describe()
        if self.job.get("modality") == "image":
            events.log(f"Textual inversion — token {self.extra.get('placeholder_token', '<dojo-concept>')!r}")
        else:
            events.log(f"Pooling: {self.extra.get('pooling', 'mean')}")

    def train_real(self, rt: Runtime) -> None:
        if self.job.get("modality") == "image":
            from . import _image

            _image.train_textual_inversion(self, rt)
            return

        # Default to the robust transformers-only SimCSE (works with any encoder
        # and needs no extra deps). Opt into sentence-transformers explicitly.
        backend = os.environ.get("DOJO_EMBED_BACKEND", "hf")
        use_st = backend == "st" and importlib.util.find_spec("sentence_transformers") is not None
        if use_st:
            self._train_text_st(rt)
        else:
            self._train_text_hf(rt)

    # --- sentence-transformers path (preferred) ------------------------------

    def _train_text_st(self, rt: Runtime) -> None:
        from sentence_transformers import InputExample, SentenceTransformer, losses
        from torch.utils.data import DataLoader

        base = self.job.get("base_model")
        texts = self.load_texts()
        events.log(f"SimCSE via sentence-transformers · {len(texts)} sentences")

        model = SentenceTransformer(base, device=rt.device)
        loader = DataLoader([InputExample(texts=[t, t]) for t in texts], shuffle=True, batch_size=self.batch_size)
        loss = losses.MultipleNegativesRankingLoss(model)
        total = self.epochs * max(1, len(loader))

        for epoch in range(1, self.epochs + 1):
            events.log(f"=== Epoch {epoch}/{self.epochs} ===")
            model.fit(
                train_objectives=[(loader, loss)],
                epochs=1,
                warmup_steps=min(100, len(loader)),
                optimizer_params={"lr": self.learning_rate},
                show_progress_bar=False,
            )
            events.progress(step=epoch * len(loader), total=total, epoch=epoch,
                            loss=max(0.01, 1.0 - epoch / (self.epochs + 1)), lr=self.learning_rate)

        model.save(self.output_dir)
        print(f"[embedding] sentence model saved to {self.output_dir}", file=sys.stderr)
        events.done(artifact=self.output_dir, mode="real", device=rt.device, backend=rt.backend,
                    impl="sentence-transformers", epochs=self.epochs, sentences=len(texts))

    # --- transformers-only fallback (unsupervised SimCSE) --------------------

    def _train_text_hf(self, rt: Runtime) -> None:
        import torch
        import torch.nn.functional as F
        from transformers import AutoModel, AutoTokenizer

        base = self.job.get("base_model")
        texts = self.load_texts()
        events.log(f"SimCSE via transformers (mean pooling) · {len(texts)} sentences")

        tok = AutoTokenizer.from_pretrained(base)
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token or tok.unk_token
        model = AutoModel.from_pretrained(base).to(rt.device)
        model.train()  # dropout ON — the two encodings of a sentence must differ

        temp = float(self.extra.get("temperature", 0.05))

        def encode(batch_texts):
            enc = tok(batch_texts, padding=True, truncation=True, max_length=self.max_seq_len, return_tensors="pt").to(rt.device)
            out = model(**enc).last_hidden_state
            mask = enc.attention_mask.unsqueeze(-1).float()
            pooled = (out * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
            return F.normalize(pooled, dim=-1)

        bs = self.batch_size
        batches = [texts[i : i + bs] for i in range(0, len(texts), bs)]
        total = self.epochs * len(batches)
        optimizer = torch.optim.AdamW(model.parameters(), lr=self.learning_rate)

        step = 0
        last_loss = 0.0
        for epoch in range(1, self.epochs + 1):
            events.log(f"=== Epoch {epoch}/{self.epochs} ===")
            for batch in batches:
                if len(batch) < 2:
                    continue  # in-batch contrastive loss needs ≥2 examples
                z1 = encode(batch)
                z2 = encode(batch)  # different dropout mask → positive pair
                sims = (z1 @ z2.t()) / temp  # in-batch negatives
                labels = torch.arange(z1.size(0), device=rt.device)
                loss = F.cross_entropy(sims, labels)
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
                step += 1
                last_loss = float(loss.detach().item())
                events.progress(step=step, total=total, epoch=epoch, loss=last_loss, lr=self.learning_rate)

        model.save_pretrained(self.output_dir)
        tok.save_pretrained(self.output_dir)
        print(f"[embedding] encoder saved to {self.output_dir}", file=sys.stderr)
        events.done(artifact=self.output_dir, mode="real", device=rt.device, backend=rt.backend,
                    impl="transformers-simcse", final_loss=round(last_loss, 6), total_steps=total)
