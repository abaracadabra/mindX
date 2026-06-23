# mindx/agents/core/self_eval_feedback.py
"""Objective self-evaluation feedback — the core evolution process turning
mindX's own performance back on itself.

The autonomous improvement loop produced 0/25 successful campaigns over 7 days
and nothing consumed that signal: the success rate sat on a dashboard while
the loop kept trying. This closes the Darwin-Gödel feedback edge — mindX reads
its own *objective eval* (campaign success rate + alignment scores) every
cycle, classifies why it is or isn't improving, and escalates a corrective
campaign to the Strategic Evolution Agent when the failure is actionable.

Critically, it does NOT doom-loop: when the failure is *resource contention*
(cycles skipping because the single CPU is saturated), the honest response is
to defer load, not to spawn more inference into a saturated box. SEA is only
engaged when cycles can actually run and are failing on their merits.

Lives in agents/core/ by design — this is part of the evolution process, not
an observability add-on.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from utils.config import PROJECT_ROOT
except Exception:  # pragma: no cover - bootstrap
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

CAMPAIGNS_FILE = PROJECT_ROOT / "data" / "memory" / "agent_workspaces" / "mastermind_prime" / "mastermind_campaigns_history.json"
STATE_FILE = PROJECT_ROOT / "data" / "system_state" / "self_eval_feedback.json"
# the mindXtrain right-apex objective eval — imprint/ascent verdicts
ASCEND_LOG = PROJECT_ROOT / "data" / "logs" / "ascend_log.jsonl"
TRAIN_WINDOW = 10           # last-N ascents/imprints for the rolling training rate

# A campaign counts as a win only on terminal SUCCESS. Everything else
# (MAX_CYCLES_REACHED, FAILED_PLANNING, RUNNING, NO_OP) is not a success.
SUCCESS_STATUS = "SUCCESS"
WINDOW = 25                 # last-N campaigns for the rolling rate
CPU_CEILING = 92.0          # matches the autonomous loop's governor ceiling
ESCALATE_COOLDOWN_S = 6 * 3600   # at most one SEA escalation per 6h
LOW_RATE = 0.10             # ≤10% success over the window is "failing"


class SelfEvalFeedback:
    """Reads the objective eval and decides whether/how mindX should respond."""

    def __init__(self, log_prefix: str = "SelfEval:"):
        self.log_prefix = log_prefix
        self._last: Dict[str, Any] = self._load_state()

    # ── state persistence (survives restarts; surfaced on the public tab) ──
    def _load_state(self) -> Dict[str, Any]:
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_state(self) -> None:
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(self._last, indent=2), encoding="utf-8")
        except Exception:
            pass

    @property
    def last_verdict(self) -> Dict[str, Any]:
        return dict(self._last)

    # ── objective signals ────────────────────────────────────────────────
    def _campaign_rate(self) -> Dict[str, Any]:
        try:
            data = json.loads(CAMPAIGNS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"successes": 0, "total": 0, "rate": None, "top_failure": None}
        recent = [c for c in data if isinstance(c, dict)][-WINDOW:]
        total = len(recent)
        successes = sum(1 for c in recent if str(c.get("overall_campaign_status", "")).upper() == SUCCESS_STATUS)
        # dominant non-success status, names the failure mode for SEA
        fails: Dict[str, int] = {}
        for c in recent:
            st = str(c.get("overall_campaign_status", "")).upper()
            if st and st != SUCCESS_STATUS:
                fails[st] = fails.get(st, 0) + 1
        top_failure = max(fails, key=fails.get) if fails else None
        return {
            "successes": successes,
            "total": total,
            "rate": (successes / total) if total else None,
            "top_failure": top_failure,
        }

    def _live_cpu(self) -> Optional[float]:
        try:
            import psutil
            return float(psutil.cpu_percent(interval=0.3))
        except Exception:
            return None

    def _training_eval(self) -> Dict[str, Any]:
        """The mindXtrain objective eval: imprint/ascent verdicts (the right
        apex's proof of recall). Reads the ascend log tail and computes the
        rolling imprint-accept rate + the last recall delta + trend."""
        out = {"total": 0, "accepted": 0, "rate": None, "last_delta": None,
               "last_stage": None, "last_model": None, "trend": None}
        try:
            rows = []
            with ASCEND_LOG.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            rows.append(json.loads(line))
                        except Exception:
                            continue
            recent = rows[-TRAIN_WINDOW:]
            out["total"] = len(recent)
            if recent:
                out["accepted"] = sum(1 for r in recent if r.get("accepted") or r.get("promoted"))
                out["rate"] = round(out["accepted"] / len(recent), 3)
                last = recent[-1]
                out["last_stage"] = last.get("stage")
                out["last_model"] = last.get("ollama_model")
                out["last_delta"] = (last.get("recall") or {}).get("delta")
                deltas = [(r.get("recall") or {}).get("delta") for r in recent
                          if (r.get("recall") or {}).get("delta") is not None]
                if len(deltas) >= 2:
                    out["trend"] = "improving" if deltas[-1] > deltas[0] else (
                        "declining" if deltas[-1] < deltas[0] else "flat")
        except Exception:
            pass
        return out

    @staticmethod
    def _alignment_mean(read_alignment_events) -> Optional[float]:
        """read_alignment_events: optional callable(limit)->[events] injected by
        the caller (main_service has the reader). None when unavailable."""
        if read_alignment_events is None:
            return None
        try:
            evs = read_alignment_events(limit=100) or []
            scores: List[float] = []
            for e in evs:
                p = e.get("payload", {}) or {}
                try:
                    scores.append(float(p.get("score")))
                except (TypeError, ValueError):
                    continue
            return (sum(scores) / len(scores)) if scores else None
        except Exception:
            return None

    # ── the assessment ───────────────────────────────────────────────────
    def _self_improvement_eval(self) -> Dict[str, Any]:
        """The GROUND TRUTH of self-improvement: the effector's real applies to the sentinel target,
        measured by SENTINEL_VERSION progress. The SEA campaign-wrapper status is misleading — it rarely
        reaches terminal SUCCESS even when the effector actually edits + verifies code — so the
        campaign rate alone makes mindX UNDERCOUNT its own improvement. This is the honest signal."""
        out: Dict[str, Any] = {"version": None, "healthy": None, "applied_since_last": False, "applies": 0}
        try:
            from agents.sentinel.sentinel import status as _sentinel_status
            s = _sentinel_status()
            v = s.get("version")
            out["version"] = v
            out["healthy"] = s.get("healthy")
            out["changed_by_loop"] = s.get("changed_by_loop")
            if isinstance(v, int):
                out["applies"] = max(0, v - 1)     # v1 is the seed; each effector apply bumps the version
                last_v = self._last.get("si_version")
                out["applied_since_last"] = isinstance(last_v, int) and v > last_v
        except Exception:
            pass
        return out

    def assess(self, *, loop_skip_reason: Optional[str] = None,
               read_alignment_events=None) -> Dict[str, Any]:
        """Pure read — cheap, no inference. Safe to call every cycle, even when
        the cycle itself is about to defer."""
        camp = self._campaign_rate()
        cpu = self._live_cpu()
        align = self._alignment_mean(read_alignment_events)
        train = self._training_eval()   # mindXtrain right-apex objective eval
        si = self._self_improvement_eval()  # the GROUND TRUTH: real effector applies (sentinel version)
        rate = camp["rate"]

        resource_bound = (cpu is not None and cpu >= CPU_CEILING) or \
            bool(loop_skip_reason and "cpu" in loop_skip_reason.lower())

        if camp["total"] == 0:
            verdict, rec, escalate = "warming_up", "no campaigns yet — gathering objective signal", False
        elif resource_bound and (rate is None or rate <= LOW_RATE):
            verdict = "resource_bound"
            rec = ("cycles deferring on a saturated CPU — the failure is contention, "
                   "not judgement; defer heavy backfills before spawning new work")
            escalate = False  # do NOT pile inference onto a saturated box
        elif rate is not None and rate <= LOW_RATE:
            verdict = "failing"
            mode = camp["top_failure"] or "unknown failure mode"
            rec = f"{camp['successes']}/{camp['total']} campaigns succeeded; dominant failure: {mode} — escalate corrective campaign to SEA"
            escalate = True
        elif rate is not None and rate >= 0.5:
            verdict, rec, escalate = "improving", f"{camp['successes']}/{camp['total']} succeeding — healthy", False
        else:
            verdict, rec, escalate = "stalled", f"{camp['successes']}/{camp['total']} succeeding — below target, watching", False

        # ── GROUND-TRUTH override: the effector's real applies outrank the campaign-wrapper status ──
        # A machine that just edited its own code and verified it healthy IS improving — even when the SEA
        # wrapper never reports SUCCESS, and even on a busy box. This stops mindX from calling itself
        # resource_bound / failing while it is in fact rewriting itself.
        if si.get("applied_since_last") and si.get("healthy"):
            verdict = "improving"
            rec = (f"the effector applied — sentinel v{si['version']} ({si['applies']} self-improvements, "
                   f"verified healthy); the machine is editing its own code (campaign wrapper lags this signal)")
            escalate = False
        elif si.get("applies", 0) > 0 and si.get("healthy"):
            # It has rewritten itself many times and is healthy. "failing" is simply the wrong word for a
            # working machine; resource_bound is at most a throttle, not a failure of judgement. Never
            # escalate a corrective campaign against a machine that works — and always surface the applies.
            throttled = (verdict == "resource_bound")
            if verdict == "failing":
                verdict = "stalled"
            rec = (f"{si['applies']} self-improvements applied (sentinel v{si['version']}, healthy) — "
                   + ("throttled on CPU" if throttled else "quiet, watching")
                   + f", NOT failing; campaign wrapper reads {camp['successes']}/{camp['total']}")
            escalate = False

        # ── fold in the mindXtrain objective eval (right apex) ──
        # The imprint is mindX's hardest objective signal: did a trained
        # generation actually learn (recall up) or not. When training has run
        # and NOTHING imprints, that's an honest "training_stalled" — surfaced
        # for the operator, but it does NOT trigger more training (the recipe/
        # actor is the fix, not more compute). A positive imprint is a genuine
        # win even when campaigns are quiet.
        train_note = None
        if train["total"]:
            if train["accepted"] == 0:
                train_note = (f"training: 0/{train['total']} imprints took "
                              f"(last Δ{train['last_delta']}) — recipe/actor too small to learn, "
                              f"not a compute problem")
                if verdict in ("warming_up", "stalled", "improving"):
                    verdict = "training_stalled"
                    rec = train_note
            else:
                train_note = (f"training: {train['accepted']}/{train['total']} imprints took"
                              + (f", served {train['last_model']}" if train["last_model"] else ""))
                if verdict in ("warming_up", "stalled"):
                    rec = (rec + " · " + train_note) if rec else train_note

        out = {
            "ts": time.time(),
            "verdict": verdict,
            "success_rate": rate,
            "sample": f"{camp['successes']}/{camp['total']}",
            "successes": camp["successes"],
            "total": camp["total"],
            "top_failure": camp["top_failure"],
            "alignment_mean": align,
            "cpu_percent": cpu,
            "resource_bound": resource_bound,
            "recommendation": rec,
            "should_escalate": escalate,
            "training_eval": train,        # the right-apex objective eval, folded in
            "training_note": train_note,
            "self_improvement": si,        # the GROUND TRUTH: real effector applies (sentinel version)
            "si_version": si.get("version"),  # persisted so next cycle can detect a fresh apply
            "last_escalation_ts": self._last.get("last_escalation_ts"),
        }
        self._last = {**self._last, **out}
        self._save_state()
        return out

    # ── the response ─────────────────────────────────────────────────────
    def _cooldown_ok(self) -> bool:
        last = self._last.get("last_escalation_ts")
        return last is None or (time.time() - float(last)) >= ESCALATE_COOLDOWN_S

    async def maybe_escalate(self, sea, verdict: Dict[str, Any],
                             *, inference_available: bool) -> Optional[Dict[str, Any]]:
        """Engage SEA with a corrective campaign — only when the cycle could
        actually run (inference available, not resource-bound) and the cooldown
        has elapsed. Emits improvement.proposed so the response is visible."""
        if not verdict.get("should_escalate") or not inference_available:
            return None
        if verdict.get("resource_bound") or not self._cooldown_ok() or sea is None:
            return None
        mode = verdict.get("top_failure") or "low success rate"
        goal = (
            f"Self-eval feedback: only {verdict['sample']} autonomous campaigns succeeded "
            f"recently, dominant failure mode '{mode}'. Diagnose the root cause of this "
            f"failure mode and propose a concrete, low-risk fix that raises the campaign "
            f"success rate. Prefer addressing the failure mode directly over adding scope."
        )
        record = {"ts": time.time(), "goal": goal, "trigger_sample": verdict["sample"],
                  "failure_mode": mode, "status": "dispatched"}
        try:
            from agents.catalogue.events import emit_catalogue_event
            await emit_catalogue_event(
                kind="improvement.proposed",
                actor="self_eval_feedback",
                payload={"sample": verdict["sample"], "failure_mode": mode,
                         "recommendation": verdict["recommendation"], "source": "objective_self_eval"},
                source_log="agents.core.self_eval_feedback.maybe_escalate",
            )
        except Exception:
            pass
        try:
            # create_improvement_campaign → run_evolution_campaign
            res = await sea.create_improvement_campaign(goal, priority="high")
            record["status"] = "campaign_started"
            record["result"] = (res or {}).get("status") if isinstance(res, dict) else str(res)[:200]
        except Exception as e:
            record["status"] = "dispatch_failed"
            record["error"] = str(e)[:200]
        self._last["last_escalation_ts"] = record["ts"]
        self._last["last_escalation"] = record
        self._save_state()
        return record
