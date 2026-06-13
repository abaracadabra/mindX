"""Proof-suite for /insight/self/diagnostic — the honest 'what is mindX
actually improving?' aggregator (mindx_backend_service/self_diagnostic.py).

Uses asyncio.run directly (house pattern — no pytest-asyncio) and a tmp_path
data root so no live data is touched.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mindx_backend_service.self_diagnostic import compute_self_diagnostic  # noqa: E402
from mindx_backend_service.text_render import render_self_diagnostic  # noqa: E402


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_empty_root_yields_honest_zeros(tmp_path):
    d = asyncio.run(compute_self_diagnostic(root=tmp_path))
    assert d["real_changes"]["sia_diffs"]["count"] == 0
    assert d["real_changes"]["sia_diffs"]["note"]          # the honest zero note
    assert d["real_changes"]["milestones"] == []
    assert d["process_health"]["backlog"]["size"] == 0
    assert d["verdict"]["line"]                             # verdict always present
    assert "0 autonomous code diffs recorded" in " ".join(d["verdict"]["evidence"])


def test_campaign_buckets_and_loop_detection(tmp_path):
    now = time.time()
    campaigns = []
    # 6 repeats of one directive under rotating idx decoration → loop detected
    for i in range(6):
        campaigns.append({
            "overall_campaign_status": "FAILURE_OR_INCOMPLETE",
            "final_bdi_message": "BDI run RUNNING. Reason: None",
            "directive": f"Implement validation [target: system, priority: 9, backlog_idx: {900 + i}]",
            "ts": now - i * 1800,
        })
    campaigns.append({
        "overall_campaign_status": "SUCCESS",
        "final_bdi_message": "BDI run COMPLETED_GOAL_ACHIEVED. Reason: N/A",
        "directive": "Something else", "ts": now - 100,
    })
    campaigns.append({
        "overall_campaign_status": "TIMED_OUT",
        "final_bdi_message": "Mastermind loop timeout (600s)",
        "directive": "Third thing", "ts": now - 200,
    })
    f = tmp_path / "data" / "memory" / "agent_workspaces" / "mastermind_prime" / "mastermind_campaigns_history.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(campaigns), encoding="utf-8")

    d = asyncio.run(compute_self_diagnostic(root=tmp_path))
    c7 = d["process_health"]["campaigns_7d"]
    assert c7["total"] == 8
    assert c7["succeeded"] == 1
    assert c7["max_cycles_reached"] == 6   # legacy RUNNING rows bucket here
    assert c7["timed_out"] == 1
    looped = d["process_health"]["looped_directives"]
    assert looped and looped[0]["count"] == 6
    assert "implement validation" in looped[0]["directive"]


def test_old_unstamped_campaigns_do_not_inflate_week(tmp_path):
    campaigns = [{"overall_campaign_status": "FAILURE_OR_INCOMPLETE",
                  "final_bdi_message": "BDI run FAILED_PLANNING. Reason: x",
                  "directive": "old"}] * 150  # no ts → cannot claim this week
    f = tmp_path / "data" / "memory" / "agent_workspaces" / "mastermind_prime" / "mastermind_campaigns_history.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(campaigns), encoding="utf-8")
    d = asyncio.run(compute_self_diagnostic(root=tmp_path))
    # falls back to last-100 slice, never the full 150
    assert d["process_health"]["campaigns_7d"]["total"] == 100


def test_backlog_health_and_dup_factor(tmp_path):
    items = [{"suggestion": "One", "status": "attempted"}] * 10 + [{"suggestion": "Two"}] * 20
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "improvement_backlog.json").write_text(json.dumps(items), encoding="utf-8")
    d = asyncio.run(compute_self_diagnostic(root=tmp_path))
    bl = d["process_health"]["backlog"]
    assert bl["size"] == 30 and bl["unique"] == 2
    assert bl["dup_factor"] == 15.0
    assert bl["attempted"] == 10
    assert bl["dedup_live"] is False


def test_real_changes_from_catalogue_and_milestones(tmp_path):
    _write_jsonl(tmp_path / "data" / "milestones" / "milestone_log.jsonl", [
        {"short_sha": "abc123", "date": "2026-06-10", "subject": "feat: thing", "worthy": True},
    ])
    _write_jsonl(tmp_path / "data" / "logs" / "catalogue_events.jsonl", [
        {"kind": "publication.published", "ts": time.time(), "payload": {"note": "post 800"}},
        {"kind": "library.discover", "ts": time.time(),
         "payload": {"package_name": "llmfit", "decision": "ADOPT"}},
        {"kind": "dreaming.improved", "ts": time.time(),
         "payload": {"new_hash": "deadbeef"}},
    ])
    d = asyncio.run(compute_self_diagnostic(root=tmp_path))
    rc = d["real_changes"]
    assert rc["milestones"][0]["sha"] == "abc123"
    assert rc["publications"][0]["note"] == "post 800"
    assert rc["adoptions"][0] == {"ts": rc["adoptions"][0]["ts"], "package": "llmfit", "decision": "ADOPT"}
    assert rc["code_change_events"][0]["kind"] == "dreaming.improved"


def test_sia_diffs_counted_when_present(tmp_path):
    _write_jsonl(
        tmp_path / "data" / "self_improvement_work_sia" / "agentx" / "archive" / "improvement_history.jsonl",
        [
            {"timestamp": "2026-06-10T00:00:00", "target_file": "/x/y/mod.py",
             "success": True, "diff_patch": "--- a/mod.py\n+++ b/mod.py\n@@ -1 +1 @@\n-x=1\n+x=2"},
            {"timestamp": "2026-06-10T01:00:00", "target_file": "/x/y/mod.py",
             "success": False, "diff_patch": "No functional code changes generated"},
        ],
    )
    d = asyncio.run(compute_self_diagnostic(root=tmp_path))
    sia = d["real_changes"]["sia_diffs"]
    assert sia["count"] == 1            # the no-op row is not a real diff
    assert sia["note"] is None
    assert sia["samples"][0]["target"] == "mod.py"


def test_secrets_sanitized_in_output(tmp_path):
    _write_jsonl(tmp_path / "data" / "milestones" / "milestone_log.jsonl", [
        {"short_sha": "fff", "date": "2026-06-10",
         "subject": "leak api_key=sk_live_abcdef0123456789 and /home/hacker/secret"},
    ])
    d = asyncio.run(compute_self_diagnostic(root=tmp_path))
    subject = d["real_changes"]["milestones"][0]["subject"]
    assert "sk_live_abcdef0123456789" not in subject
    assert "/home/hacker" not in subject


def test_renderer_plaintext_verdict_first(tmp_path):
    d = asyncio.run(compute_self_diagnostic(root=tmp_path))
    txt = render_self_diagnostic(d)
    assert txt.splitlines()[0].startswith("mindX self-diagnostic")
    assert "<" not in txt
    assert "process health" in txt
