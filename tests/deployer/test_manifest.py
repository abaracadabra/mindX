"""Unit tests for `.deploy` manifest parse/validate."""

import json
import os

import pytest

from agents.deployer.manifest import ManifestError, load_manifest, resolve_env_map

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "sample.deploy")


def test_parse_sample():
    m = load_manifest(FIX)
    assert m.project == "sample"
    assert m.required_min_tier == "tier1"
    assert [s.chain for s in m.stages] == ["anvil-local", "algorand-localnet"]
    f = m.stage_for("anvil-local")
    assert f.driver == "foundry" and f.config["script"].endswith("DeployTemplate")
    a = m.stage_for("algorand-localnet")
    assert a.driver == "algorand" and a.config["contracts"] == ["AgenticMinter"]


def test_selected_stages():
    m = load_manifest(FIX)
    assert len(m.selected_stages(None)) == 2
    assert len(m.selected_stages("anvil-local")) == 1
    with pytest.raises(ManifestError):
        m.selected_stages("nope")


def test_validation_rejects(tmp_path):
    def write(d):
        p = tmp_path / "x.deploy"
        p.write_text(json.dumps(d))
        return str(p)

    base = {"project": "p", "version": "1", "required_min_tier": "tier1",
            "stages": [{"chain": "c", "chain_id": 1, "driver": "foundry",
                        "rpc_env": "R", "deployer_entity": "e", "foundry": {"script": "s"}}]}
    # missing project
    with pytest.raises(ManifestError):
        load_manifest(write({**base, "project": None}))
    # bad tier
    with pytest.raises(ManifestError):
        load_manifest(write({**base, "required_min_tier": "tier9"}))
    # driver/block mismatch
    bad = json.loads(json.dumps(base))
    bad["stages"][0]["driver"] = "algorand"
    with pytest.raises(ManifestError):
        load_manifest(write(bad))
    # both blocks
    both = json.loads(json.dumps(base))
    both["stages"][0]["algorand"] = {"contracts": []}
    with pytest.raises(ManifestError):
        load_manifest(write(both))
    # no stages
    with pytest.raises(ManifestError):
        load_manifest(write({**base, "stages": []}))


def test_resolve_env_map(monkeypatch):
    monkeypatch.setenv("OWNER_MULTISIG", "0xabc")
    out = resolve_env_map({"OWNER_MULTISIG": "$OWNER_MULTISIG", "LITERAL": "true", "MISSING": "$NOPE"})
    assert out == {"OWNER_MULTISIG": "0xabc", "LITERAL": "true", "MISSING": ""}
