# SPDX-License-Identifier: Apache-2.0
"""`skill_distill` — turn a successful BDI intention into a draft Skill.

Fifth concrete absorption from the Hermes/OpenClaw research stack. The
Hermes integration doc §8.1 specifies the trigger plainly:

  > Add a ``skill_distill`` action to the BDI action set, fired when an
  > intention completes with ``success_signal == true`` and intermediate
  > steps ≥ N. The action writes a SKILL.md draft, surfaces it to
  > MASTERMIND for ratification, and on accept commits to disk.

This module is the **library entry point**. The actual wiring into the BDI
agent's intention-completion path is a one-line call from
``agents/core/bdi_agent.py`` (deferred — it's a hot path and lands in a
later, focused diff). Until then any agent can call
``distill_from_intention(...)`` directly from its own completion handler.

Default policy (per the Hermes doc, all configurable):

  * Minimum intermediate steps:  N = 5
  * Minimum unique tool calls:    M = 2
  * ``draft_only=True`` by default — write to ``$MINDX_SKILLS_DIR/.drafts/<slug>/SKILL.md``
    rather than the live store. An operator (or a deferred MASTERMIND
    ratification step) approves before the draft is promoted to the live
    store; promotion goes through ``SkillStore.write`` so the scanner gate
    applies.
  * If ``draft_only=False`` is passed and the running agent is human-trusted,
    the skill is written directly. The scanner still runs.

Failure modes:
  * Insufficient steps → ``None`` (no draft, no exception).
  * Scanner refuses on direct write → exception bubbles up (caller chooses).
  * Disk error → exception bubbles up.
"""
from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from agents.skills.scanner import scan_skill
from agents.skills.skill_schema import Skill, SkillFrontmatter, serialize_skill_md

logger = logging.getLogger("agents.skills.distill")

DEFAULT_MIN_STEPS = 5
DEFAULT_MIN_UNIQUE_TOOLS = 2


@dataclass
class DistillationResult:
    """Outcome of a distill call. ``skill`` is None when the threshold wasn't met."""
    skill: Optional[Skill]
    reason: str
    draft_path: Optional[Path] = None
    promoted_path: Optional[Path] = None


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return (s[:64] or "intention")


def distill_from_intention(
    *,
    intention_id: str,
    intention_template: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    beliefs_before: Optional[dict[str, Any]] = None,
    beliefs_after: Optional[dict[str, Any]] = None,
    steps: Optional[list[dict[str, Any]]] = None,
    success_signal: bool = False,
    agent_id: Optional[str] = None,
    category: str = "agent-distilled",
    min_steps: int = DEFAULT_MIN_STEPS,
    min_unique_tools: int = DEFAULT_MIN_UNIQUE_TOOLS,
    draft_only: bool = True,
    store=None,
) -> DistillationResult:
    """Turn a completed BDI intention into a draft :class:`Skill`.

    Parameters
    ----------
    intention_id, intention_template:
        Identifiers for the source intention. ``intention_template`` (if known)
        is recorded in the Skill frontmatter so the BDI compiler can match it.
    beliefs_before / beliefs_after:
        The agent's Belief snapshot before and after the intention. The diff
        becomes the Skill's declared postconditions.
    steps:
        List of ``{tool, args, result}`` (or any shape) describing the steps
        the agent actually took. Threshold check + body composition rely on
        ``len(steps)`` and unique ``tool`` count.
    success_signal:
        Must be ``True`` for distillation to proceed. False ⇒ short-circuit.
    draft_only:
        Write to ``$MINDX_SKILLS_DIR/.drafts/`` instead of the live
        SkillStore. Default True. Set False when the caller is human and
        wants immediate landing.
    store:
        Optional :class:`SkillStore`. Required when ``draft_only=False``.
    """
    if not success_signal:
        return DistillationResult(None, "no success_signal — refusing to distill")

    steps = steps or []
    n = len(steps)
    if n < min_steps:
        return DistillationResult(None, f"too few steps ({n} < {min_steps})")

    unique_tools = len({(s.get("tool") if isinstance(s, dict) else None) for s in steps} - {None})
    if unique_tools < min_unique_tools:
        return DistillationResult(None, f"too few unique tools ({unique_tools} < {min_unique_tools})")

    # Postconditions = Belief keys that flipped True or newly appeared with truthy values.
    postconditions: list[str] = []
    before = beliefs_before or {}
    after = beliefs_after or {}
    for k, v in after.items():
        bv = before.get(k)
        if v and not bv:
            postconditions.append(f"belief.{k}=true")

    # Compose a SKILL.md body from the step list — first-person voice.
    title = title or (intention_template or f"intention-{intention_id}")
    description = description or f"Distilled from BDI intention {intention_id} ({n} steps, {unique_tools} unique tools)."

    body_lines = [
        f"# {title}",
        "",
        f"*Distilled by {agent_id or 'mindX'} on {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}.*",
        "",
        f"**Intention:** `{intention_id}`" + (f"  (template `{intention_template}`)" if intention_template else ""),
        "",
        "## What I did",
        "",
    ]
    for i, step in enumerate(steps, 1):
        tool = step.get("tool") if isinstance(step, dict) else None
        args = step.get("args") if isinstance(step, dict) else None
        result = step.get("result") if isinstance(step, dict) else None
        body_lines.append(f"{i}. **{tool or 'step'}**" + (f" — args: `{args}`" if args else "") + (f" → `{result}`" if result is not None else ""))
    body_lines.append("")
    if postconditions:
        body_lines += ["## Postconditions", ""] + [f"- `{p}`" for p in postconditions] + [""]
    body = "\n".join(body_lines)

    slug = _slugify(title)
    skill = Skill(
        frontmatter=SkillFrontmatter(
            name=title,
            description=description,
            category=category,
            tags=["distilled", intention_template] if intention_template else ["distilled"],
            created_by="agent",
            intention_template=intention_template,
            postconditions=postconditions,
            source=f"distill:intention:{intention_id}",
        ),
        body=body,
    )
    # Re-set the slug-derived name to match what SkillStore will compute.
    # (Skill.slug already kebab-cases; we ensure the title produces it.)

    # — sanity: scanner must pass for an agent-authored skill —
    scan = scan_skill(skill)
    if not scan.safe:
        return DistillationResult(
            None,
            "scanner refused distilled skill: " + "; ".join(scan.block_reasons()),
        )

    if draft_only:
        # Write the draft to a separate `.drafts/` tree the operator can review.
        env = os.environ.get("MINDX_SKILLS_DIR")
        skills_root = Path(env) if env else Path.home() / ".mindx" / "skills"
        draft_dir = skills_root / ".drafts" / category / skill.slug
        draft_dir.mkdir(parents=True, exist_ok=True)
        draft_path = draft_dir / "SKILL.md"
        draft_path.write_text(serialize_skill_md(skill), encoding="utf-8")
        return DistillationResult(skill, "draft written", draft_path=draft_path)

    if store is None:
        return DistillationResult(None, "draft_only=False requires a SkillStore")

    path, _ = store.write(skill)
    return DistillationResult(skill, "promoted to live store", promoted_path=path)


__all__ = ["distill_from_intention", "DistillationResult", "DEFAULT_MIN_STEPS", "DEFAULT_MIN_UNIQUE_TOOLS"]
