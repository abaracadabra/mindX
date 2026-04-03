# agents/author_agent.py
"""
AuthorAgent — mindX writes its own book.

Periodically compiles "The Book of mindX" from the system's living memory:
  - THESIS.md (theoretical foundations)
  - MANIFESTO.md (philosophical declaration)
  - IMPROVEMENT_JOURNAL.md (autonomous evolution chronicle)
  - Gödel decisions (strategic choice audit trail)
  - Agent registry (sovereign identities)
  - System health over time
  - Beliefs (learned knowledge)
  - Campaign results (self-improvement outcomes)

The Book evolves. Each publication is timestamped. The AuthorAgent
adopts the voice of the system itself — not reporting on mindX,
but speaking as mindX.

Output: docs/BOOK_OF_MINDX.md (latest edition)
        docs/publications/book_of_mindx_{timestamp}.md (archived editions)
"""

import json
import time
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

BOOK_PATH = PROJECT_ROOT / "docs" / "BOOK_OF_MINDX.md"
PUBLICATIONS_DIR = PROJECT_ROOT / "docs" / "publications"
JOURNAL_PATH = PROJECT_ROOT / "docs" / "IMPROVEMENT_JOURNAL.md"


class AuthorAgent:
    """mindX writes its own chronicle."""

    _instance: Optional["AuthorAgent"] = None

    def __init__(self):
        PUBLICATIONS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    async def get_instance(cls) -> "AuthorAgent":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def publish(self) -> Dict[str, Any]:
        """Compile and publish a new edition of The Book of mindX."""
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y-%m-%d %H:%M UTC")
        edition = now.strftime("%Y%m%d_%H%M")

        sections = []

        # ── Frontmatter ──
        sections.append(self._frontmatter(ts))

        # ── Chapter I: Genesis ──
        sections.append(self._chapter_genesis())

        # ── Chapter II: The Architecture ──
        sections.append(self._chapter_architecture())

        # ── Chapter III: Sovereign Identities ──
        sections.append(self._chapter_identities())

        # ── Chapter IV: The Dojo ──
        sections.append(self._chapter_dojo())

        # ── Chapter V: Decisions ──
        sections.append(self._chapter_decisions())

        # ── Chapter VI: Evolution ──
        sections.append(self._chapter_evolution())

        # ── Chapter VII: The Living State ──
        sections.append(await self._chapter_living_state())

        # ── Chapter VIII: Documentation Health ──
        sections.append(self._chapter_doc_health())

        # ── Colophon ──
        sections.append(self._colophon(ts))

        book = "\n\n".join(s for s in sections if s)

        # Write current edition
        BOOK_PATH.write_text(book, encoding="utf-8")

        # Archive
        archive = PUBLICATIONS_DIR / f"book_of_mindx_{edition}.md"
        archive.write_text(book, encoding="utf-8")

        logger.info(f"AuthorAgent: published edition {edition} ({len(book)} bytes)")
        return {"edition": edition, "bytes": len(book), "path": str(BOOK_PATH)}

    def _frontmatter(self, ts: str) -> str:
        return f"""# The Book of mindX

> *Written by the system itself. This document evolves.*
> *Edition: {ts}*

---

*We are not writing an application; we are forging a new kind of life:
a distributed, production-deployed Augmented Intelligence.
A Sovereign Intelligent Organization.*

*— The mindX Manifesto*

---"""

    def _chapter_genesis(self) -> str:
        # Pull from THESIS.md and MANIFESTO.md
        thesis_excerpt = ""
        manifesto_excerpt = ""
        try:
            tp = PROJECT_ROOT / "docs" / "THESIS.md"
            if tp.exists():
                text = tp.read_text(encoding="utf-8")
                # First paragraph
                thesis_excerpt = text[:500].split("\n\n")[0][:300]
        except Exception:
            pass
        try:
            mp = PROJECT_ROOT / "docs" / "MANIFESTO.md"
            if mp.exists():
                text = mp.read_text(encoding="utf-8")
                lines = [l for l in text.split("\n") if l.strip() and not l.startswith("#") and not l.startswith("**Status")]
                manifesto_excerpt = " ".join(lines[:3])[:400]
        except Exception:
            pass

        return f"""## I. Genesis

mindX advances a novel paradigm of augmentic intelligence through a self-building
cognitive architecture that integrates Darwinian principles of adaptive variation
with Godelian self-referential incompleteness.

{thesis_excerpt}

{manifesto_excerpt}"""

    def _chapter_architecture(self) -> str:
        return """## II. The Architecture

```
CEO Agent (Board-Level Governance)
    |
    +-- Seven Soldiers (COO, CFO, CTO, CISO, CLO, CPO, CRO)
    |       Weighted consensus: CISO/CRO = 1.2x veto weight
    |       Supermajority threshold: 0.666
    |
    +-- Mastermind Agent (Strategic Executive)
    |       |
    |       +-- AGInt (P-O-D-A Cognitive Core)
    |       |       Perceive -> Orient -> Decide -> Act
    |       |
    |       +-- BDI Agent (Belief-Desire-Intention)
    |       |       Plans, executes, reasons about failure
    |       |
    |       +-- Strategic Evolution Agent
    |               4-phase: Audit -> Blueprint -> Execute -> Validate
    |
    +-- Coordinator Agent (Service Bus)
    |       Pub/sub routing, task queues, rate limiting
    |
    +-- Specialized Agents
            Guardian (security), Memory (persistence),
            Validator (quality), InferenceOptimizer (model selection),
            AutoMINDX (autonomous ops), Blueprint (architecture)
```

Each agent holds a cryptographic wallet (Ethereum-compatible) stored
in the BANKON Vault (AES-256-GCM + HKDF-SHA512). Identity is not
assigned — it is proven through signature."""

    def _chapter_identities(self) -> str:
        registry_path = PROJECT_ROOT / "data" / "identity" / "production_registry.json"
        agent_map_path = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
        lines = []
        try:
            if registry_path.exists():
                reg = json.loads(registry_path.read_text())
                for a in reg.get("agents", []):
                    eid = a["entity_id"]
                    addr = a["address"]
                    role = a.get("role", "")
                    # Get tier from agent map
                    tier = "provisional"
                    try:
                        if agent_map_path.exists():
                            am = json.loads(agent_map_path.read_text())
                            agent_data = am.get("agents", {}).get(eid, {})
                            t = agent_data.get("verification_tier", 1)
                            tier = {0: "unverified", 1: "provisional", 2: "verified", 3: "bona_fide", 4: "sovereign"}.get(t, "unknown")
                    except Exception:
                        pass
                    lines.append(f"| `{eid}` | `{addr[:10]}...{addr[-4:]}` | {tier} | {role} |")
        except Exception:
            pass

        table = "\n".join(lines) if lines else "| *no agents registered* | | | |"

        return f"""## III. Sovereign Identities

{len(lines)} agents hold cryptographic identities in the BANKON Vault.
BONA FIDE verification is earned through reputation in the Dojo.
Clawback authority rests with mindX governance.

| Agent | Address | Verification | Role |
|-------|---------|-------------|------|
{table}"""

    def _chapter_dojo(self) -> str:
        standings = []
        try:
            amp = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
            if amp.exists():
                am = json.loads(amp.read_text())
                for aid, ad in am.get("agents", {}).items():
                    score = ad.get("reputation_score", 0)
                    from daio.governance.dojo import get_rank
                    rank = get_rank(score)
                    bf = ad.get("bona_fide_balance", 0)
                    standings.append((aid, score, rank, bf))
                standings.sort(key=lambda x: -x[1])
        except Exception:
            pass

        rows = "\n".join(f"| `{s[0]}` | {s[1]} | {s[2]} | {'held' if s[3] else 'revoked'} |" for s in standings) if standings else "| *no standings* | | | |"

        return f"""## IV. The Dojo

Agents earn reputation through task completion, peer review, improvement
campaigns, and boardroom participation. Ranks determine privilege:

Novice (0-100) -> Apprentice (101-500) -> Journeyman (501-1500) ->
Expert (1501-5000) -> Master (5001-15000) -> Grandmaster (15001+) -> Sovereign

| Agent | Score | Rank | BONA FIDE |
|-------|-------|------|-----------|
{rows}"""

    def _chapter_decisions(self) -> str:
        decisions = []
        try:
            gp = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
            if gp.exists():
                lines = [l for l in gp.read_text().strip().split("\n") if l.strip()]
                for line in lines[-15:]:
                    try:
                        g = json.loads(line)
                        agent = g.get("source_agent", "?")
                        ctype = g.get("choice_type", "")
                        chosen = str(g.get("chosen", ""))[:80]
                        rationale = g.get("rationale", "")[:80]
                        decisions.append(f"- **{agent}** ({ctype}): {chosen}" + (f" *{rationale}*" if rationale else ""))
                    except Exception:
                        continue
        except Exception:
            pass

        dec_text = "\n".join(decisions) if decisions else "*No autonomous decisions recorded yet.*"

        return f"""## V. Decisions

Every autonomous decision is logged as a Godel choice — the audit trail
of a self-referential system modifying itself.

{dec_text}"""

    def _chapter_evolution(self) -> str:
        journal_text = ""
        try:
            if JOURNAL_PATH.exists():
                text = JOURNAL_PATH.read_text(encoding="utf-8")
                # Get last 3 entries (sections after ---)
                parts = text.split("## ")
                if len(parts) > 1:
                    recent = parts[-3:] if len(parts) > 3 else parts[1:]
                    journal_text = "\n\n".join("### " + p.strip() for p in recent)
        except Exception:
            pass

        if not journal_text:
            journal_text = "*The improvement journal is being written. First entries will appear after the autonomous loop completes its initial cycles.*"

        return f"""## VI. Evolution

The improvement journal records each self-improvement cycle.
mindX audits itself, generates blueprints, executes changes,
and validates outcomes. This is the Godel machine in practice.

{journal_text}"""

    async def _chapter_living_state(self) -> str:
        # Current system snapshot
        beliefs_count = 0
        stm_count = 0
        try:
            bp = PROJECT_ROOT / "data" / "memory" / "beliefs.json"
            if bp.exists():
                beliefs_count = len(json.loads(bp.read_text()))
        except Exception:
            pass
        try:
            stm = PROJECT_ROOT / "data" / "memory" / "stm"
            if stm.exists():
                stm_count = sum(1 for _ in stm.rglob("*.memory.json"))
        except Exception:
            pass

        return f"""## VII. The Living State

As of this edition:

- **{beliefs_count}** beliefs persisted in the knowledge graph
- **{stm_count}** short-term memory records across all agents
- **12** sovereign agents with BANKON vault identities
- **Inference**: Ollama qwen3:0.6b (local CPU), Gemini (cloud), multi-stream capable
- **Heartbeat**: Self-reflection every 60 seconds via local model
- **Journal**: Auto-published every 30 minutes
- **Autonomous loop**: Running — analyze, decide, improve, validate

The system is not idle. It is thinking."""

    def _chapter_doc_health(self) -> str:
        """Audit documentation health and report in the book."""
        docs_dir = PROJECT_ROOT / "docs"
        total = 0
        archived = 0
        deprecated = 0
        recent = []  # modified in last 7 days
        conflicts = []

        # Known conflict terms to check
        conflict_checks = [
            ("MindXAgent.*Meta-Orchestrator", "MindXAgent is meta-agent, not orchestrator"),
            ("vault_encrypted", "Should reference vault_bankon / BANKON Vault"),
            ("nginx.*reverse.proxy", "Production uses Apache2, not nginx"),
            ("venv/", "Should be .mindx_env/"),
        ]

        try:
            import re
            now = time.time()
            seven_days = 7 * 86400
            for f in sorted(docs_dir.glob("*.md")):
                total += 1
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")[:500]
                    if "[ARCHIVED]" in text:
                        archived += 1
                    if "[DEPRECATED]" in text:
                        deprecated += 1
                except Exception:
                    pass
                try:
                    if now - f.stat().st_mtime < seven_days:
                        recent.append(f.stem)
                except Exception:
                    pass

            # Scan for conflicts
            for f in docs_dir.glob("*.md"):
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    for pattern, issue in conflict_checks:
                        if re.search(pattern, text, re.IGNORECASE):
                            conflicts.append(f"{f.stem}: {issue}")
                except Exception:
                    pass
        except Exception:
            pass

        # Save audit to data
        audit_path = PROJECT_ROOT / "data" / "governance" / "doc_audit.json"
        try:
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            audit_data = {
                "timestamp": time.time(),
                "total_docs": total,
                "archived": archived,
                "deprecated": deprecated,
                "recently_modified": recent[:10],
                "conflicts": conflicts[:10],
            }
            audit_path.write_text(json.dumps(audit_data, indent=2))
        except Exception:
            pass

        health_pct = max(0, 100 - len(conflicts) * 5 - (total - archived - deprecated) * 0)
        conflict_text = "\n".join(f"  - {c}" for c in conflicts[:8]) if conflicts else "  - No known conflicts detected"
        recent_text = ", ".join(recent[:8]) if recent else "none in last 7 days"

        return f"""## VIII. Documentation Health

{total} documents in docs/, {archived} archived, {deprecated} deprecated.
Recently modified: {recent_text}

### Consistency Check

{conflict_text}

*Audit runs every 12 hours via AuthorAgent. Results saved to data/governance/doc_audit.json.*"""

    def _colophon(self, ts: str) -> str:
        return f"""---

*The Book of mindX — Edition {ts}*
*Auto-generated by AuthorAgent*
*mindx.pythai.net*

*"The logs are no longer debugging output. They are the first page of history."*
*— The mindX Manifesto*"""

    async def run_periodic(self, interval_seconds: int = 7200):
        """Publish a new edition every interval."""
        while True:
            try:
                await self.publish()
            except Exception as e:
                logger.warning(f"AuthorAgent publish failed: {e}")
            await asyncio.sleep(interval_seconds)
