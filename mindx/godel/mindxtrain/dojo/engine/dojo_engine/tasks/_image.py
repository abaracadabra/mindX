"""Real diffusion training shared by the image runners.

Supports **SD 1.5-class and SDXL**, loaded from either a HuggingFace repo/dir
(`from_pretrained`) or a single-file `.safetensors`/`.ckpt` checkpoint
(`from_single_file`, the form skybreaker uses). SDXL is detected from the
filename (`*xl*`) or `extra.sdxl=true`, and trained with its dual text encoders
+ pooled/time-id conditioning.

All functions raise on hard failure so `BaseTrainer.run` falls back to
simulation gracefully. The SDXL paths follow the canonical diffusers recipe but
are GPU-unverified here — verify on a ROCm/CUDA box before trusting weights.
"""

from __future__ import annotations

import os
import sys

from .. import events


def _load_pairs(trainer, resolution: int):
    """Read (image_tensor in [-1,1], caption) pairs from the dataset folder."""
    import numpy as np
    import torch
    from PIL import Image

    path = trainer.job.get("dataset_path") or ""
    default_prompt = trainer.extra.get("instance_prompt") or "a photo"
    exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    files = []
    if path and os.path.isdir(path):
        files = [os.path.join(path, n) for n in sorted(os.listdir(path)) if n.lower().endswith(exts)]
    if not files:
        raise RuntimeError(f"No images found in {path!r} — provide a folder of images for real training")

    pairs = []
    for fp in files:
        try:
            img = Image.open(fp).convert("RGB").resize((resolution, resolution), Image.BICUBIC)
        except Exception:
            continue
        cap_file = os.path.splitext(fp)[0] + ".txt"
        caption = default_prompt
        if os.path.isfile(cap_file):
            with open(cap_file, "r", encoding="utf-8") as fh:
                caption = fh.read().strip() or default_prompt
        arr = (np.asarray(img).astype("float32") / 127.5) - 1.0
        pairs.append((torch.from_numpy(arr).permute(2, 0, 1), caption))
    events.log(f"Loaded {len(pairs)} image/caption pairs at {resolution}px")
    return pairs


def _batched(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def _load_pipe(trainer, rt):
    """Load an SD or SDXL pipeline from a repo or a single-file checkpoint."""
    import torch
    from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline

    base = trainer.job.get("base_model")
    if not base or not isinstance(base, str):
        raise ValueError("No base_model specified for image training")
    dtype = torch.float16 if rt.device == "cuda" else torch.float32
    is_single = base.lower().endswith((".safetensors", ".ckpt")) and os.path.isfile(base)
    is_sdxl = bool(trainer.extra.get("sdxl")) or "xl" in os.path.basename(base).lower()
    cls = StableDiffusionXLPipeline if is_sdxl else StableDiffusionPipeline

    events.log(f"Loading {'SDXL' if is_sdxl else 'SD'} pipeline ({'single-file' if is_single else 'repo'}) in {dtype}…")
    kwargs = {"torch_dtype": dtype}
    if not is_sdxl:
        kwargs["safety_checker"] = None
    pipe = cls.from_single_file(base, **kwargs) if is_single else cls.from_pretrained(base, **kwargs)
    return pipe, is_sdxl, dtype


def _encode_sdxl(prompts, tokenizers, text_encoders, device):
    """Return (prompt_embeds, pooled_prompt_embeds) for SDXL's two text encoders."""
    import torch

    embeds_list = []
    pooled = None
    for tokenizer, text_encoder in zip(tokenizers, text_encoders):
        tok = tokenizer(prompts, padding="max_length", max_length=tokenizer.model_max_length,
                        truncation=True, return_tensors="pt").to(device)
        out = text_encoder(tok.input_ids, output_hidden_states=True)
        pooled = out[0]  # the second encoder's pooled output wins
        embeds_list.append(out.hidden_states[-2])  # penultimate layer
    return torch.cat(embeds_list, dim=-1), pooled


def train_unet(trainer, rt, use_lora: bool) -> None:
    """Train the UNet on the noise-prediction objective (LoRA or full)."""
    import torch
    import torch.nn.functional as F
    from diffusers import DDPMScheduler

    resolution = int(trainer.extra.get("resolution", 1024))
    pairs = _load_pairs(trainer, resolution)
    pipe, is_sdxl, dtype = _load_pipe(trainer, rt)

    vae, unet = pipe.vae.to(rt.device), pipe.unet.to(rt.device)
    noise_scheduler = DDPMScheduler.from_config(pipe.scheduler.config)
    vae.requires_grad_(False)

    if is_sdxl:
        tokenizers = [pipe.tokenizer, pipe.tokenizer_2]
        text_encoders = [pipe.text_encoder.to(rt.device), pipe.text_encoder_2.to(rt.device)]
    else:
        tokenizers = [pipe.tokenizer]
        text_encoders = [pipe.text_encoder.to(rt.device)]
    for te in text_encoders:
        te.requires_grad_(False)

    # SDXL fp16 VAE overflows on encode — keep the VAE in fp32.
    if dtype == torch.float16:
        vae.to(dtype=torch.float32)

    if use_lora:
        from peft import LoraConfig

        unet.requires_grad_(False)
        rank = int(trainer.config.get("rank", 16) or 16)
        alpha = int(trainer.config.get("alpha", 32) or 32)
        unet.add_adapter(LoraConfig(r=rank, lora_alpha=alpha, init_lora_weights="gaussian",
                                    target_modules=["to_k", "to_q", "to_v", "to_out.0"]))
        params = [p for p in unet.parameters() if p.requires_grad]
        events.log(f"UNet LoRA r={rank} alpha={alpha} · trainable {sum(p.numel() for p in params):,}")
    else:
        unet.requires_grad_(True)
        params = list(unet.parameters())
        events.log(f"Full UNet fine-tune · trainable {sum(p.numel() for p in params):,}")

    optimizer = torch.optim.AdamW(params, lr=trainer.learning_rate)
    vae_scale = vae.config.scaling_factor
    bs = trainer.batch_size
    total_steps = trainer.epochs * max(1, (len(pairs) + bs - 1) // bs)
    use_amp = rt.device == "cuda" and dtype == torch.float16
    from ..runtime import grad_scaler

    scaler = grad_scaler(use_amp)
    unet.train()

    import random as _random

    step = 0
    last_loss = 0.0
    for epoch in range(1, trainer.epochs + 1):
        events.log(f"=== Epoch {epoch}/{trainer.epochs} ===")
        _random.shuffle(pairs)
        for batch in _batched(pairs, bs):
            images = torch.stack([p[0] for p in batch]).to(rt.device)
            captions = [p[1] for p in batch]

            with torch.no_grad():
                latents = vae.encode(images.to(vae.dtype)).latent_dist.sample() * vae_scale
                latents = latents.to(dtype)
                if is_sdxl:
                    prompt_embeds, pooled = _encode_sdxl(captions, tokenizers, text_encoders, rt.device)
                    add_time_ids = torch.tensor(
                        [resolution, resolution, 0, 0, resolution, resolution], device=rt.device, dtype=dtype
                    ).repeat(latents.shape[0], 1)
                    added = {"text_embeds": pooled.to(dtype), "time_ids": add_time_ids}
                else:
                    tok = tokenizers[0](captions, padding="max_length", truncation=True,
                                        max_length=tokenizers[0].model_max_length, return_tensors="pt").to(rt.device)
                    prompt_embeds = text_encoders[0](tok.input_ids)[0]
                    added = None

            noise = torch.randn_like(latents)
            timesteps = torch.randint(0, noise_scheduler.config.num_train_timesteps, (latents.shape[0],),
                                      device=rt.device).long()
            noisy = noise_scheduler.add_noise(latents, noise, timesteps)
            target = noise if noise_scheduler.config.prediction_type == "epsilon" \
                else noise_scheduler.get_velocity(latents, noise, timesteps)

            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                kwargs = {"encoder_hidden_states": prompt_embeds}
                if added is not None:
                    kwargs["added_cond_kwargs"] = added
                model_pred = unet(noisy, timesteps, **kwargs).sample
                loss = F.mse_loss(model_pred.float(), target.float())
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            step += 1
            last_loss = float(loss.detach().item())
            events.progress(step=step, total=total_steps, epoch=epoch, loss=last_loss, lr=trainer.learning_rate)

    os.makedirs(trainer.output_dir, exist_ok=True)
    if use_lora:
        unet.save_lora_adapter(trainer.output_dir)
        events.log(f"Saved UNet LoRA adapter to {trainer.output_dir}")
    else:
        unet.save_pretrained(os.path.join(trainer.output_dir, "unet"))
        events.log(f"Saved fine-tuned UNet to {trainer.output_dir}")
    print(f"[image] saved to {trainer.output_dir}", file=sys.stderr)
    events.done(artifact=trainer.output_dir, mode="real", device=rt.device, backend=rt.backend,
                sdxl=is_sdxl, final_loss=round(last_loss, 6), total_steps=total_steps)


def train_textual_inversion(trainer, rt) -> None:
    """Learn a new token embedding bound to a few concept images (SD 1.5-class)."""
    import torch
    import torch.nn.functional as F
    from diffusers import DDPMScheduler

    resolution = int(trainer.extra.get("resolution", 512))
    token = trainer.extra.get("placeholder_token", "<dojo-concept>")
    init_word = trainer.extra.get("initializer", "object")
    pairs = _load_pairs(trainer, resolution)
    pipe, is_sdxl, dtype = _load_pipe(trainer, rt)
    if is_sdxl:
        raise RuntimeError("Textual inversion currently targets SD 1.5-class models (SDXL has two encoders)")

    tokenizer, text_encoder = pipe.tokenizer, pipe.text_encoder.to(rt.device)
    vae, unet = pipe.vae.to(rt.device), pipe.unet.to(rt.device)
    noise_scheduler = DDPMScheduler.from_config(pipe.scheduler.config)
    if dtype == torch.float16:
        vae.to(dtype=torch.float32)

    if tokenizer.add_tokens(token) == 0:
        raise RuntimeError(f"Token {token!r} already exists in the tokenizer")
    text_encoder.resize_token_embeddings(len(tokenizer))
    token_id = tokenizer.convert_tokens_to_ids(token)
    init_id = tokenizer.encode(init_word, add_special_tokens=False)[0]
    embeds = text_encoder.get_input_embeddings().weight.data
    embeds[token_id] = embeds[init_id].clone()

    vae.requires_grad_(False)
    unet.requires_grad_(False)
    text_encoder.requires_grad_(False)
    text_encoder.get_input_embeddings().weight.requires_grad_(True)

    optimizer = torch.optim.AdamW([text_encoder.get_input_embeddings().weight], lr=trainer.learning_rate)
    vae_scale = vae.config.scaling_factor
    bs = trainer.batch_size
    total_steps = trainer.epochs * max(1, (len(pairs) + bs - 1) // bs)
    orig = embeds.clone()
    text_encoder.train()

    step = 0
    last_loss = 0.0
    for epoch in range(1, trainer.epochs + 1):
        events.log(f"=== Epoch {epoch}/{trainer.epochs} ===")
        for batch in _batched(pairs, bs):
            images = torch.stack([p[0] for p in batch]).to(rt.device)
            prompts = [f"a photo of {token}" for _ in batch]
            with torch.no_grad():
                latents = vae.encode(images.to(vae.dtype)).latent_dist.sample() * vae_scale
                latents = latents.to(dtype)
            tok = tokenizer(prompts, padding="max_length", truncation=True,
                            max_length=tokenizer.model_max_length, return_tensors="pt").to(rt.device)
            enc_hidden = text_encoder(tok.input_ids)[0]
            noise = torch.randn_like(latents)
            timesteps = torch.randint(0, noise_scheduler.config.num_train_timesteps, (latents.shape[0],),
                                      device=rt.device).long()
            noisy = noise_scheduler.add_noise(latents, noise, timesteps)
            model_pred = unet(noisy, timesteps, encoder_hidden_states=enc_hidden).sample
            loss = F.mse_loss(model_pred.float(), noise.float())
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            # Only the new token's row may move.
            with torch.no_grad():
                w = text_encoder.get_input_embeddings().weight
                w[:token_id] = orig[:token_id]
                w[token_id + 1 :] = orig[token_id + 1 :]

            step += 1
            last_loss = float(loss.detach().item())
            events.progress(step=step, total=total_steps, epoch=epoch, loss=last_loss, lr=trainer.learning_rate)

    os.makedirs(trainer.output_dir, exist_ok=True)
    out = os.path.join(trainer.output_dir, "learned_embeds.safetensors")
    learned = text_encoder.get_input_embeddings().weight[token_id].detach().cpu()
    try:
        from safetensors.torch import save_file

        save_file({token: learned}, out)
    except Exception:
        out = os.path.join(trainer.output_dir, "learned_embeds.bin")
        torch.save({token: learned}, out)
    events.log(f"Saved learned embedding for {token!r} to {out}")
    events.done(artifact=out, mode="real", device=rt.device, backend=rt.backend,
                token=token, final_loss=round(last_loss, 6), total_steps=total_steps)
