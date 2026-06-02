"""Test PATCH /v1/config/fallback-model — the mindXtrain → mindX swap path.

The endpoint lets mindXtrain (or an operator) point production at a freshly
fine-tuned checkpoint without a source edit. It works by rewriting
`models/<provider>.yaml`'s `default_model:` field (the canonical source of
truth — JSON overrides under `data/config/` are clobbered by the YAML merge
that runs after them in `utils.config.Config._load_model_capability_configs`).

We exercise two things:

1. The pure file-writing helper round-trips: it reads the YAML, swaps
   `default_model`, writes atomically, and preserves the other fields.
2. The Config singleton picks up the new YAML on reset.

We do **not** spin up the full FastAPI TestClient against main_service —
that import pulls the entire agent stack and is too heavy for a unit test.
The endpoint's HTTP contract is exercised in integration tests against a
running instance.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

# Match the convention of tests/test_dream_retrain.py — push the mindX root
# onto sys.path so `utils.config` is importable when pytest is invoked from
# outside the mindX directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Build a fake PROJECT_ROOT with the minimum mindX layout needed.

    Stands up tmp_path/data/config and tmp_path/models/ollama.yaml so the
    Config loader and the FallbackModelPayload provider validator both
    succeed without touching the real repo.
    """
    (tmp_path / "data" / "config").mkdir(parents=True)
    (tmp_path / "models").mkdir(parents=True)
    (tmp_path / "models" / "ollama.yaml").write_text(
        "provider: ollama\n"
        "default_model: qwen3:0.6b\n"
        "base_url: http://localhost:11434\n"
        "models:\n"
        "  - name: qwen3:0.6b\n"
        "  - name: qwen3:1.7b\n"
    )
    monkeypatch.setattr("utils.config.PROJECT_ROOT", tmp_path)
    from utils.config import Config
    Config.reset_instance()
    yield tmp_path
    Config.reset_instance()


def _write_yaml_override(project_root: Path, provider: str, model: str) -> Path:
    """Mirror of main_service._write_fallback_override for test isolation."""
    yaml_path = project_root / "models" / f"{provider}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"models/{provider}.yaml not found")
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    data["default_model"] = model
    tmp = yaml_path.with_suffix(".yaml.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, default_flow_style=False)
    tmp.replace(yaml_path)
    return yaml_path


def test_write_override_preserves_other_yaml_fields(isolated_config):
    """Helper must update `default_model` while leaving the rest of the YAML intact."""
    out = _write_yaml_override(isolated_config, "ollama", "qwen3:1.7b")
    written = yaml.safe_load(out.read_text())
    assert written["default_model"] == "qwen3:1.7b"
    assert written["provider"] == "ollama"
    assert written["base_url"] == "http://localhost:11434"
    assert {m["name"] for m in written["models"]} == {"qwen3:0.6b", "qwen3:1.7b"}


def test_write_override_raises_for_missing_provider_yaml(isolated_config):
    with pytest.raises(FileNotFoundError):
        _write_yaml_override(isolated_config, "vllm", "Qwen/Qwen3-1.5B")


def test_config_picks_up_new_default_after_reset(isolated_config):
    """End-to-end: rewrite the YAML, reset Config, get() returns new value."""
    from utils.config import Config

    _write_yaml_override(isolated_config, "ollama", "pythai/mindx-fallback-qwen3-1.5b")
    Config.reset_instance()
    cfg = Config()
    assert cfg.get("llm.ollama.default_model") == "pythai/mindx-fallback-qwen3-1.5b"
