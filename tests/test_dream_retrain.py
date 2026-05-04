"""Integration test for MachineDreamCycle._phase_model_selector_retrain.

Plants synthetic selector decisions with explicit success/failure outcomes,
runs the retrain phase, asserts weights drift in the expected direction.

Run: .mindx_env/bin/python -m pytest tests/test_dream_retrain.py -v --no-cov
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Stand up a minimal project tree the retrain phase can read/write."""
    logs = tmp_path / "data" / "logs"
    config = tmp_path / "data" / "config"
    logs.mkdir(parents=True)
    config.mkdir(parents=True)

    # Synthetic godel choices — success rows favor success_rate axis,
    # failure rows favor latency_p50_inverse axis. Retrain should bump
    # success_rate weight and reduce latency_p50_inverse weight.
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows = []
    # 6 successful selections with high success_rate breakdown
    for _ in range(6):
        rows.append({
            "source_agent": "mindx.self.improve.model_selector",
            "choice_type": "self_aware_model_selection",
            "task_class": "reasoning",
            "importance": "standard",
            "confidence": "high",
            "options_considered": [
                {"slug": "model_a",
                 "score": 0.7,
                 "breakdown": {"success_rate": 0.9, "latency_p50_inverse": 0.2,
                               "eval_alignment_mean": 0.6, "capability_match": 1.0,
                               "cost_per_invocation_inverse": 1.0,
                               "recency_bonus": 0.5, "failure_penalty_inverse": 0.9}}
            ],
            "chosen_option": "model_a",
            "rationale": "test row",
            "outcome": "success",
            "timestamp_utc": now_iso,
        })
    # 6 failed selections that scored high on latency
    for _ in range(6):
        rows.append({
            "source_agent": "mindx.self.improve.model_selector",
            "choice_type": "self_aware_model_selection",
            "task_class": "reasoning",
            "importance": "standard",
            "confidence": "high",
            "options_considered": [
                {"slug": "model_b",
                 "score": 0.7,
                 "breakdown": {"success_rate": 0.2, "latency_p50_inverse": 0.95,
                               "eval_alignment_mean": 0.3, "capability_match": 1.0,
                               "cost_per_invocation_inverse": 1.0,
                               "recency_bonus": 0.5, "failure_penalty_inverse": 0.5}}
            ],
            "chosen_option": "model_b",
            "rationale": "test row",
            "outcome": "failed",
            "timestamp_utc": now_iso,
        })

    godel_path = logs / "godel_choices.jsonl"
    with godel_path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    weights_path = config / "self_aware_weights.json"
    weights_doc = {
        "_updated": "2026-05-04",
        "task_classes": {
            "reasoning": {
                "success_rate": 0.20,
                "eval_alignment_mean": 0.20,
                "latency_p50_inverse": 0.20,
                "cost_per_invocation_inverse": 0.10,
                "capability_match": 0.10,
                "recency_bonus": 0.10,
                "failure_penalty_inverse": 0.10,
            },
            "default": {
                "success_rate": 0.20,
                "eval_alignment_mean": 0.20,
                "latency_p50_inverse": 0.20,
                "cost_per_invocation_inverse": 0.10,
                "capability_match": 0.10,
                "recency_bonus": 0.10,
                "failure_penalty_inverse": 0.10,
            },
        },
    }
    weights_path.write_text(json.dumps(weights_doc, indent=2) + "\n")

    # Monkeypatch PROJECT_ROOT in the dream module so it reads from tmp_path.
    import agents.machine_dreaming as md
    monkeypatch.setattr(md, "PROJECT_ROOT", tmp_path)
    return tmp_path


def test_retrain_nudges_weights_toward_success_correlated_axis(tmp_project):
    """6 success rows favor success_rate; 6 fail rows favor latency_p50_inverse.
    After retrain: success_rate weight should increase; latency_p50_inverse should drop."""
    from agents.machine_dreaming import MachineDreamCycle
    dream = MachineDreamCycle.__new__(MachineDreamCycle)
    dream.log_prefix = "[test]"
    result = asyncio.run(dream._phase_model_selector_retrain())

    assert result["decisions_seen"] == 12
    assert "reasoning" in result["task_classes_active"]
    deltas = result["weight_deltas"].get("reasoning") or {}
    # success_rate should have a positive delta; latency_p50_inverse negative.
    assert deltas.get("success_rate", 0) > 0, f"expected success_rate to be bumped, got deltas={deltas}"
    assert deltas.get("latency_p50_inverse", 0) < 0, f"expected latency_p50_inverse to drop, got deltas={deltas}"

    # Weights file was updated and remains a valid distribution.
    weights = json.loads((tmp_project / "data" / "config" / "self_aware_weights.json").read_text())
    new_weights = weights["task_classes"]["reasoning"]
    total = sum(v for k, v in new_weights.items() if not k.startswith("_"))
    assert 0.99 <= total <= 1.01, f"weights should renormalize to ~1.0, got {total}"


def test_retrain_emits_observation_when_no_outcome_data(tmp_project):
    """Plant decisions with all 'pending' outcomes — retrain should emit
    observation rec, NOT mutate weights."""
    godel_path = tmp_project / "data" / "logs" / "godel_choices.jsonl"
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows = []
    for _ in range(3):
        rows.append({
            "source_agent": "mindx.self.improve.model_selector",
            "choice_type": "self_aware_model_selection",
            "task_class": "reasoning",
            "importance": "standard",
            "confidence": "low",
            "options_considered": [{"slug": "x", "score": 0.5, "breakdown": {"success_rate": 0.5}}],
            "chosen_option": "x",
            "rationale": "test",
            "outcome": "pending",
            "timestamp_utc": now_iso,
        })
    with godel_path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    from agents.machine_dreaming import MachineDreamCycle
    dream = MachineDreamCycle.__new__(MachineDreamCycle)
    dream.log_prefix = "[test]"
    result = asyncio.run(dream._phase_model_selector_retrain())

    # No mutation when fewer than 5 outcome rows
    assert result["weight_deltas"] == {}
    # Observation tuning rec is emitted
    recs = result["tuning_recommendations"]
    assert any("insufficient signal" in (r.get("recommendation") or "") for r in recs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
