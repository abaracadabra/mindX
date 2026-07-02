"""The Dojo training engine.

A thin, dependency-light orchestration layer that the Tauri desktop app
drives as a subprocess. It speaks a newline-delimited JSON event protocol on
stdout (see ``events.py``) and dispatches jobs to task runners for LoRA
training, fine-tuning, and embedding builds across text and image models.

The task runners ship with a CPU-friendly *simulated* training loop so the
whole app works end-to-end with no heavy ML dependencies installed. Each
runner documents exactly where to drop in the real PEFT / diffusers /
sentence-transformers implementation.
"""

__version__ = "0.1.0"
