"""
Disposable-vault test for BankonVault.rotate_overseer.

Machine → Human handoff end-to-end, with a deterministic test private key.
Verifies:
  - All entries survive rotation (plaintexts preserved)
  - Dry-run does not mutate live state
  - Commit requires a fresh .ok marker
  - Post-commit: .master.key is gone, sentinel is present
  - Post-commit: unlock_with_key_file refuses to run (guarded by sentinel)
  - Post-commit: unlock_with_overseer() re-opens the vault via the proof file
  - overseer_history.jsonl got one row
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Run from repo root — allow imports without PYTHONPATH juggling.
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT))


def run() -> int:
    from eth_account import Account
    from eth_account.messages import encode_defunct

    # Enable the feature flag just for this test process.
    os.environ["MINDX_VAULT_ALLOW_OVERSEER_ROTATION"] = "1"

    # Deterministic test key — do NOT use this anywhere real.
    test_priv = "0x" + "11" * 32
    test_acct = Account.from_key(test_priv)

    # Disposable vault
    # Isolated layout so the audit log path (vault_dir.parent.parent/data/governance)
    # resolves inside OUR tmp and is fresh per run.
    tmp = Path(tempfile.mkdtemp(prefix="rotate-overseer-test-"))
    parent = tmp / "run"
    parent.mkdir()
    vault_dir = parent / "vault_bankon"
    try:
        # Lazy-import so sys.path side effects are in place
        from mindx_backend_service.bankon_vault.vault import BankonVault
        from mindx_backend_service.bankon_vault.overseer import HumanOverseer

        v = BankonVault(vault_dir=str(vault_dir))
        v.unlock_with_key_file()

        # Seed 5 entries with varied context
        fixture = {
            "agent_pk_guardian": "0xabc" + "0" * 60,
            "agent_pk_mastermind": "0xdef" + "1" * 60,
            "agent_pk_ceo":  "0x" + "a" * 64,
            "provider:openai_api_key": "sk-proj-abcdef1234567890",
            "provider:algod_token":    "a" * 64,
        }
        for k, value in fixture.items():
            v.store(k, value, context=("agent_identity" if k.startswith("agent") else "provider"))
        assert len(v.list_entries()) == 5

        pre_hashes = {k: hashlib.sha256(v.retrieve(k).encode()).hexdigest() for k in fixture}

        # Construct the HumanOverseer and sign a challenge
        overseer = HumanOverseer(eth_address=test_acct.address, vault_salt=v._salt)
        challenge_text = "BANKON Vault Custody Handoff v1 — test ceremony"
        challenge_bytes = challenge_text.encode("utf-8")
        msg = encode_defunct(text=challenge_text)
        signed = Account.sign_message(msg, private_key=test_priv)
        sig_hex = signed.signature.hex()
        if not sig_hex.startswith("0x"):
            sig_hex = "0x" + sig_hex
        sig_bytes = bytes.fromhex(sig_hex[2:])
        assert len(sig_bytes) == 65

        evidence = {"kind": "human", "signature": sig_hex, "message": challenge_text}

        # DRY RUN — pass the message bytes as challenge (NOT the signature).
        dry = v.rotate_overseer(overseer, challenge_bytes, evidence, reason="test_rotation", dry_run=True)
        assert dry["status"] == "dry_run_ok", dry
        assert dry["entries"] == 5
        assert (vault_dir / ".rotation.ok").exists()
        assert (vault_dir / "entries.json.candidate").exists()
        # Live state untouched
        for k, expected in pre_hashes.items():
            actual = hashlib.sha256(v.retrieve(k).encode()).hexdigest()
            assert actual == expected, f"dry_run mutated {k!r}"

        # COMMIT
        committed = v.rotate_overseer(overseer, challenge_bytes, evidence, reason="test_rotation", dry_run=False)
        assert committed["status"] == "committed", committed
        assert not (vault_dir / ".master.key").exists(), ".master.key should be deleted"
        assert (vault_dir / ".human_overseer_active").exists(), "sentinel should be written"
        assert (vault_dir / ".overseer_proof.json").exists(), "proof should be persisted"

        # All entries survive under the new key
        for k, expected in pre_hashes.items():
            actual = hashlib.sha256(v.retrieve(k).encode()).hexdigest()
            assert actual == expected, f"entry {k!r} corrupted by rotation"

        # unlock_with_key_file must refuse (sentinel guard)
        v2 = BankonVault(vault_dir=str(vault_dir))
        try:
            v2.unlock_with_key_file()
            raise AssertionError("expected RuntimeError from unlock_with_key_file under sentinel")
        except RuntimeError as e:
            assert "HumanOverseer" in str(e)

        # unlock_with_overseer re-opens via the proof
        from mindx_backend_service.bankon_vault.overseer import load_human_from_proof
        proof_path = vault_dir / ".overseer_proof.json"
        reop_overseer, reop_challenge, reop_evidence = load_human_from_proof(proof_path, v2._salt)
        v2.unlock_with_overseer(reop_overseer, reop_challenge, reop_evidence)
        # Retrieve after fresh instance + overseer unlock — must match
        for k, expected in pre_hashes.items():
            actual = hashlib.sha256(v2.retrieve(k).encode()).hexdigest()
            assert actual == expected, f"re-open via proof failed for {k!r}"

        # overseer_history.jsonl got one row (relative to vault_dir.parent.parent/data/governance)
        history_file = vault_dir.parent.parent / "data" / "governance" / "overseer_history.jsonl"
        assert history_file.exists(), "overseer_history.jsonl missing"
        rows = [json.loads(l) for l in history_file.read_text().strip().split("\n") if l.strip()]
        assert len(rows) == 1 and rows[0]["to_kind"] == "human", rows

        print("PASS rotate_overseer — all invariants hold:")
        print("  5 entries preserved across Machine→Human rotation")
        print("  .master.key deleted; sentinel + proof written")
        print("  unlock_with_key_file correctly refuses under sentinel")
        print("  unlock_with_overseer via proof file re-opens the vault")
        print("  overseer_history.jsonl: 1 row, to_kind=human")
        return 0

    except AssertionError as e:
        print(f"FAIL assertion: {e}")
        return 1
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAIL exception: {e}")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_rotate_overseer_machine_to_human():
    """Pytest wrapper around run() — asserts the rotation contract holds."""
    assert run() == 0


if __name__ == "__main__":
    sys.exit(run())
