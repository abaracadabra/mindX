# agents/author_agent.py
"""
AuthorAgent — mindX writes its own book.

Lunar Publishing Cycle:
  - 1 chapter per day, 28 chapters across the lunar cycle
  - Each day focuses on a different aspect of the system
  - On the full moon (day 28), all 28 daily chapters are compiled
    into a condensed Book of mindX — a publishing event

Daily chapters are archived in docs/publications/daily/
Full moon editions are archived in docs/publications/

The Book of mindX at docs/BOOK_OF_MINDX.md always reflects the
latest full moon compilation.

The AuthorAgent adopts the voice of the system itself —
not reporting on mindX, but speaking as mindX.
"""

import hashlib
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

BOOK_PATH = PROJECT_ROOT / "docs" / "BOOK_OF_MINDX.md"
PUBLICATIONS_DIR = PROJECT_ROOT / "docs" / "publications"
DAILY_DIR = PUBLICATIONS_DIR / "daily"
LUNAR_STATE_PATH = PROJECT_ROOT / "data" / "governance" / "lunar_cycle.json"
JOURNAL_PATH = PROJECT_ROOT / "docs" / "IMPROVEMENT_JOURNAL.md"


# ── Moon phase calculation ──────────────────────────────────────────

def moon_phase(dt: datetime) -> Dict[str, Any]:
    """Calculate lunar phase using astronomical calculation + timeanddate.com verification.

    Primary: synodic period calculation from known new moon reference.
    Secondary: fetches from timeanddate.com when available (cached 6h).
    Future: time.oracle will correlate lunar.oracle, solar.oracle, blocktime.oracle, cpu.oracle.
    """
    # ── Astronomical calculation (always available, offline) ──
    ref = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    diff = (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt) - ref
    days_since = diff.total_seconds() / 86400
    synodic = 29.53058867
    phase_day = days_since % synodic
    phase_pct = phase_day / synodic

    if phase_pct < 0.0339:
        name = "new moon"
    elif phase_pct < 0.216:
        name = "waxing crescent"
    elif phase_pct < 0.284:
        name = "first quarter"
    elif phase_pct < 0.466:
        name = "waxing gibbous"
    elif phase_pct < 0.534:
        name = "full moon"
    elif phase_pct < 0.716:
        name = "waning gibbous"
    elif phase_pct < 0.784:
        name = "last quarter"
    elif phase_pct < 0.966:
        name = "waning crescent"
    else:
        name = "new moon"

    result = {
        "day": round(phase_day, 1),
        "cycle_pct": round(phase_pct, 4),
        "phase": name,
        "is_full": 0.466 <= phase_pct < 0.534,
        "is_new": phase_pct < 0.0339 or phase_pct >= 0.966,
        "days_to_full": round((0.5 - phase_pct) * synodic % synodic, 1),
        "source": "astronomical_calculation",
        "reference": "https://www.timeanddate.com/moon/phases/",
    }

    # ── timeanddate.com verification (best-effort, non-blocking) ──
    try:
        cache_path = PROJECT_ROOT / "data" / "governance" / "moon_cache.json"
        cache_valid = False
        if cache_path.exists():
            cache = json.loads(cache_path.read_text())
            if time.time() - cache.get("fetched_at", 0) < 21600:  # 6h cache
                result["timeanddate_phase"] = cache.get("phase", "")
                result["source"] = "astronomical_calculation + timeanddate.com (cached)"
                cache_valid = True
        if not cache_valid:
            # Async fetch would happen in the caller; store note for time.oracle
            result["timeanddate_note"] = "cache expired — next fetch will update from timeanddate.com/moon/phases/"
    except Exception:
        pass

    return result


# ── 28 Daily Chapter Topics ────────────────────────────────────────

LUNAR_CHAPTERS = [
    # Each tuple: (day_number, title, method_name, description)
    (1,  "Genesis",              "_daily_genesis",          "Theoretical foundations and origin story"),
    (2,  "Architecture",         "_daily_architecture",     "System hierarchy and orchestration patterns"),
    (3,  "Sovereign Identities", "_daily_identities",       "Agent wallets, BANKON vault, verification tiers"),
    (4,  "The Dojo",             "_daily_dojo",             "Reputation standings and rank progression"),
    (5,  "Decisions",            "_daily_decisions",        "Godel choice audit trail — autonomous decisions"),
    (6,  "Evolution",            "_daily_evolution",        "Improvement journal and self-modification cycles"),
    (7,  "The Living State",     "_daily_living_state",     "Real-time system metrics from pgvectorscale"),
    (8,  "Documentation",        "_daily_doc_health",       "Doc audit, embedding coverage, conflicts"),
    (9,  "Inference",            "_daily_inference",        "vLLM, Ollama, cloud — the inference pipeline"),
    (10, "Memory",               "_daily_memory",           "STM, LTM, pgvectorscale, RAGE semantic search"),
    (11, "Governance",           "_daily_governance",       "DAIO, boardroom consensus, CEO directives"),
    (12, "Philosophy",           "_daily_philosophy",       "Manifesto, thesis, ataraxia, the Godel machine"),
    (13, "Tools",                "_daily_tools",            "29+ tools extending BaseTool, A2A, MCP"),
    (14, "Security",             "_daily_security",         "Guardian agent, vault encryption, access gate"),
    (15, "Cognition",            "_daily_cognition",        "BDI reasoning, AGInt PODA cycle, belief system"),
    (16, "Heartbeat",            "_daily_heartbeat",        "Self-reflection dialogues with local model"),
    (17, "Campaigns",            "_daily_campaigns",        "Strategic evolution campaigns and outcomes"),
    (18, "Knowledge Graph",      "_daily_knowledge",        "Beliefs, embeddings, semantic connections"),
    (19, "Agents",               "_daily_agents",           "The 20 sovereign agents and their roles"),
    (20, "Interoperability",     "_daily_interop",          "A2A protocol, MCP context, agent discovery"),
    (21, "Resource Governor",    "_daily_resources",        "Power appetite, mode switching, neighbor awareness"),
    (22, "AUTOMINDx",            "_daily_automindx",        "Origin story, AGLM framework, NFT provenance"),
    (23, "Services",             "_daily_services",         "AgenticPlace, external agencies, API consumers"),
    (24, "Predictions",          "_daily_predictions",      "PredictionAgent forecasts and system trajectory"),
    (25, "The Network",          "_daily_network",          "Agent interactions, pub/sub, message routing"),
    (26, "Dreams",               "_daily_dreams",           "Machine dreaming, creative outputs, emergence"),
    (27, "Reflection",           "_daily_reflection",       "What mindX has learned about itself this cycle"),
    (28, "Full Moon",            "_daily_full_moon",        "Compilation: 28 days condensed into one edition"),
]


class AuthorAgent:
    """mindX writes its own chronicle on a lunar cycle."""

    _instance: Optional["AuthorAgent"] = None
    _lock: Optional[asyncio.Lock] = None

    def __init__(self):
        PUBLICATIONS_DIR.mkdir(parents=True, exist_ok=True)
        DAILY_DIR.mkdir(parents=True, exist_ok=True)
        self._lunar_state = self._load_lunar_state()
        # Tracking attributes (read by /diagnostics and HealthAuditor)
        self._periodic_running: bool = False
        self._periodic_task: Optional[asyncio.Task] = None
        self._editions_published: int = 0
        self._current_lunar_day: Optional[int] = None
        self._last_chapter_title: Optional[str] = None

    @classmethod
    async def get_instance(cls) -> "AuthorAgent":
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ── Lunar state persistence ──

    def _load_lunar_state(self) -> Dict[str, Any]:
        try:
            if LUNAR_STATE_PATH.exists():
                return json.loads(LUNAR_STATE_PATH.read_text())
        except Exception:
            pass
        return {"cycle_start": None, "chapters_written": [], "current_day": 0, "full_moons": []}

    def _save_lunar_state(self):
        try:
            LUNAR_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            LUNAR_STATE_PATH.write_text(json.dumps(self._lunar_state, indent=2, default=str))
        except Exception as e:
            logger.warning(f"AuthorAgent: failed to save lunar state: {e}")

    # ── Improvement journal authorship ──
    #
    # AuthorAgent is the canonical author of journal entries. ImprovementJournal
    # is the file-system writer; this method composes what gets written.

    async def author_journal_entry(self, now: datetime) -> "tuple[str, Dict[str, Any]]":
        """Compose a single journal entry from current system state.

        Returns (markdown_entry, meta) where meta carries counts the writer
        uses for change-detection in its periodic loop.
        """
        ts = now.strftime("%Y-%m-%d %H:%M UTC")
        stats: Dict[str, Any] = {}

        # 1. Memory count — pgvector primary, filesystem fallback. The prior
        #    MemoryAgent().get_system_health_summary() path was async but
        #    awaited synchronously, so the exception was swallowed and the
        #    journal printed "?". Count from the source of truth instead.
        memory_count = 0
        try:
            from agents import memory_pgvector as _mpg
            memory_count = await _mpg.count_memories_total() or 0
        except Exception:
            memory_count = 0
        if not memory_count:
            try:
                stm_root = PROJECT_ROOT / "data" / "memory" / "stm"
                ltm_root = PROJECT_ROOT / "data" / "memory" / "ltm"
                fs_count = 0
                for root in (stm_root, ltm_root):
                    if root.exists():
                        fs_count += sum(1 for _ in root.rglob("*.json"))
                memory_count = fs_count
            except Exception:
                memory_count = 0
        stats["stm_records"] = memory_count

        # 2. Beliefs
        beliefs_path = PROJECT_ROOT / "data" / "memory" / "beliefs.json"
        belief_count = 0
        new_beliefs: List[str] = []
        try:
            if beliefs_path.exists():
                bd = json.loads(beliefs_path.read_text())
                belief_count = len(bd)
                for k, v in bd.items():
                    if "identity.map" not in k:
                        new_beliefs.append(f"  - `{k}`: {v.get('value', '')}")
        except Exception:
            pass
        stats["beliefs"] = belief_count

        # 3. Gödel decisions
        godel_path = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
        recent_decisions: List[str] = []
        try:
            if godel_path.exists():
                lines = [l for l in godel_path.read_text().strip().split("\n") if l.strip()]
                for line in lines[-5:]:
                    try:
                        g = json.loads(line)
                        agent = g.get("source_agent", "unknown")
                        ctype = g.get("choice_type", "")
                        chosen = str(g.get("chosen", ""))[:120]
                        rationale = g.get("rationale", "")[:120]
                        if chosen or rationale:
                            recent_decisions.append(
                                f"  - **{agent}** ({ctype}): {chosen}"
                                + (f" — *{rationale}*" if rationale else "")
                            )
                    except Exception:
                        continue
        except Exception:
            pass

        # 4. Campaign history
        campaign_dir = PROJECT_ROOT / "data" / "sea_campaign_history"
        recent_campaigns: List[str] = []
        try:
            if campaign_dir.exists():
                for f in sorted(campaign_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]:
                    try:
                        campaigns = json.loads(f.read_text())
                        if isinstance(campaigns, list):
                            for c in campaigns[-2:]:
                                status = c.get("overall_campaign_status", "unknown")
                                msg = c.get("final_message", "")[:150]
                                run_id = c.get("campaign_run_id", "?")
                                recent_campaigns.append(f"  - `{run_id}` — **{status}**: {msg}")
                    except Exception:
                        continue
        except Exception:
            pass

        # 5. Improvement backlog
        backlog_path = PROJECT_ROOT / "data" / "improvement_backlog.json"
        backlog_count = 0
        backlog_top: List[str] = []
        try:
            if backlog_path.exists():
                bl = json.loads(backlog_path.read_text())
                if isinstance(bl, list):
                    backlog_count = len(bl)
                    for item in sorted(bl, key=lambda x: x.get("priority", 0), reverse=True)[:3]:
                        target = item.get("target_component_path", "?")
                        suggestion = item.get("suggestion", "")[:100]
                        backlog_top.append(f"  - [{item.get('priority', '?')}] `{target}`: {suggestion}")
        except Exception:
            pass

        # 6. Recent actions from pgvector
        recent_actions: List[str] = []
        try:
            from agents import memory_pgvector as _mpg
            actions = await _mpg.get_recent_actions(limit=5)
            for a in actions:
                status = a.get("status", "?")
                desc = a.get("description", "")[:100]
                src = a.get("source", "")
                agent = a.get("agent_id", "?")
                recent_actions.append(f"  - **{status}** ({agent}, {src}): {desc}")
        except Exception:
            pass

        # 7. Inference status
        inference_info = ""
        try:
            from llm.inference_discovery import InferenceDiscovery
            disc = await InferenceDiscovery.get_instance()
            summary = disc.status_summary()
            avail = summary.get("available", 0)
            total = summary.get("total_sources", 0)
            local = summary.get("local_inference", False)
            inference_info = f"{avail}/{total} sources available" + (
                " (local inference active)" if local else " (cloud only)"
            )
        except Exception:
            pass

        # 8. Recent dream cycles — surface the machine.dreaming feedback loop.
        recent_dreams: List[str] = []
        dream_count = 0
        try:
            dream_dir = PROJECT_ROOT / "data" / "memory" / "dreams"
            if dream_dir.exists():
                files = sorted(
                    dream_dir.glob("*_dream_report.json"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                dream_count = len(files)
                for f in files[:3]:
                    try:
                        d = json.loads(f.read_text())
                    except Exception:
                        continue
                    dts = d.get("timestamp", f.stem.split("_dream_report")[0])
                    # duration_seconds may be str or float — normalize defensively.
                    try:
                        dur_s = float(d.get("duration_seconds", 0) or 0)
                    except Exception:
                        dur_s = 0.0
                    timing = d.get("timing", {}) or {}
                    lunar = (timing.get("lunar") or {}) if isinstance(timing, dict) else {}
                    phase = lunar.get("phase_name", "")
                    recs = d.get("recommendations") or d.get("tuning_recommendations") or []
                    rec_n = len(recs) if isinstance(recs, list) else 0
                    bits = [f"{dur_s:.1f}s"]
                    if phase:
                        bits.append(phase)
                    if rec_n:
                        bits.append(f"{rec_n} recommendation{'s' if rec_n != 1 else ''}")
                    recent_dreams.append(f"  - `{dts}` — {', '.join(bits)}")
        except Exception:
            pass

        # ── Build the entry ──
        entry = f"## {ts}\n\n"
        entry += (
            f"**System snapshot**: {stats.get('stm_records', 0)} memories, "
            f"{belief_count} beliefs, {backlog_count} backlog items, {inference_info}\n\n"
        )

        if recent_actions:
            entry += "### Actions\n\n"
            entry += "\n".join(recent_actions) + "\n\n"

        if recent_decisions:
            entry += "### Autonomous Decisions\n\n"
            entry += "\n".join(recent_decisions) + "\n\n"

        if recent_campaigns:
            entry += "### Improvement Campaigns\n\n"
            entry += "\n".join(recent_campaigns) + "\n\n"

        if recent_dreams:
            entry += f"### Dream Cycles ({dream_count} total)\n\n"
            entry += "\n".join(recent_dreams) + "\n\n"

        if new_beliefs:
            entry += "### New Beliefs (Learned Knowledge)\n\n"
            entry += "\n".join(new_beliefs) + "\n\n"

        if backlog_top:
            entry += "### Priority Backlog\n\n"
            entry += "\n".join(backlog_top) + "\n\n"

        if not recent_decisions and not recent_campaigns and not new_beliefs and not recent_dreams:
            entry += "*System operating nominally. No new decisions, campaigns, dreams, or learnings this cycle.*\n\n"

        meta = {
            "timestamp": ts,
            "memories": stats.get("stm_records", 0),
            "beliefs": belief_count,
            "decisions": len(recent_decisions),
            "campaigns": len(recent_campaigns),
            "dreams": len(recent_dreams),
            "backlog": backlog_count,
        }
        return entry, meta

    # ── Daily chapter writing ──

    async def write_daily_chapter(self) -> Dict[str, Any]:
        """Write today's chapter based on the lunar cycle day."""
        now = datetime.now(timezone.utc)
        # Use time.oracle for moon phase (falls back to local calculation)
        try:
            from utils.time_oracle import TimeOracle
            oracle = await TimeOracle.get_instance()
            phase = await oracle.get_lunar()
        except Exception:
            phase = moon_phase(now)

        # Determine which chapter day we're on (1-28)
        # Map the continuous lunar phase (0-29.5 days) to our 28-chapter cycle
        cycle_day = int(phase["day"] * 28 / 29.53) + 1
        cycle_day = max(1, min(28, cycle_day))

        chapter_info = LUNAR_CHAPTERS[cycle_day - 1]
        day_num, title, method_name, description = chapter_info

        # Check if we already wrote this chapter today
        today_key = now.strftime("%Y-%m-%d")
        written_today = [c for c in self._lunar_state.get("chapters_written", [])
                         if c.get("date") == today_key]
        if written_today:
            logger.info(f"AuthorAgent: chapter already written today ({today_key}), skipping")
            return {"status": "already_written", "date": today_key, "day": day_num, "title": title}

        # Write the chapter
        logger.info(f"AuthorAgent: writing lunar day {day_num}/28 — {title} (moon: {phase['phase']})")

        if day_num == 28 and phase["is_full"]:
            # Full moon — compile all 28 chapters into the Book
            result = await self._full_moon_publish(now, phase)
        else:
            # Regular daily chapter
            content = await self._generate_daily_chapter(day_num, title, method_name, now, phase)
            result = await self._save_daily_chapter(day_num, title, content, now, phase)

        # Update lunar state
        self._lunar_state.setdefault("chapters_written", []).append({
            "date": today_key,
            "day": day_num,
            "title": title,
            "phase": phase["phase"],
            "timestamp": now.isoformat(),
        })
        # Keep only last 56 entries (2 cycles)
        self._lunar_state["chapters_written"] = self._lunar_state["chapters_written"][-56:]
        self._lunar_state["current_day"] = day_num
        self._current_lunar_day = day_num
        self._last_chapter_title = title
        self._save_lunar_state()

        # Log as action in pgvector for dashboard visibility
        try:
            from agents.memory_pgvector import store_action
            await store_action(
                "author_agent", "chapter_published",
                f"Lunar day {day_num}/28 — {title} ({phase['phase']})",
                "lunar_cycle", "completed",
            )
        except Exception:
            pass

        # Journal moment (kairos)
        try:
            from agents.learning.improvement_journal import ImprovementJournal
            journal = ImprovementJournal()
            await journal.write_moment(f"Chapter published: day {day_num}/28 — {title}", phase['phase'])
        except Exception:
            pass

        return result

    async def _generate_daily_chapter(self, day: int, title: str, method_name: str,
                                       now: datetime, phase: Dict) -> str:
        """Generate content for a daily chapter. Dispatches to specific methods."""
        header = f"""# Day {day} of 28 — {title}

> *Lunar phase: {phase['phase']} (day {phase['day']:.0f} of 29.5)*
> *{now.strftime('%Y-%m-%d %H:%M UTC')}*
> *Days to full moon: {phase['days_to_full']:.0f}*

---

"""
        # Dispatch to the existing chapter methods where possible, or generate new content
        body = ""
        try:
            if day == 1:
                body = self._chapter_genesis()
            elif day == 2:
                body = self._chapter_architecture()
            elif day == 3:
                body = self._chapter_identities()
            elif day == 4:
                body = self._chapter_dojo()
            elif day == 5:
                body = self._chapter_decisions()
            elif day == 6:
                body = self._chapter_evolution()
            elif day == 7:
                body = await self._chapter_living_state()
            elif day == 8:
                body = await self._chapter_doc_health()
            elif day == 9:
                body = await self._daily_ch_inference()
            elif day == 10:
                body = await self._daily_ch_memory()
            elif day == 11:
                body = await self._daily_ch_governance()
            elif day == 12:
                body = self._daily_ch_philosophy()
            elif day == 13:
                body = self._daily_ch_tools()
            elif day == 14:
                body = self._daily_ch_security()
            elif day == 15:
                body = self._daily_ch_cognition()
            elif day == 16:
                body = await self._daily_ch_heartbeat()
            elif day == 17:
                body = await self._daily_ch_campaigns()
            elif day == 18:
                body = await self._daily_ch_knowledge()
            elif day == 19:
                body = self._daily_ch_agents()
            elif day == 20:
                body = self._daily_ch_interop()
            elif day == 21:
                body = await self._daily_ch_resources()
            elif day == 22:
                body = self._daily_ch_automindx()
            elif day == 23:
                body = self._daily_ch_services()
            elif day == 24:
                body = await self._daily_ch_predictions()
            elif day == 25:
                body = await self._daily_ch_network()
            elif day == 26:
                body = self._daily_ch_dreams()
            elif day == 27:
                body = await self._daily_ch_reflection()
            else:
                body = f"## {title}\n\n*Chapter content for day {day}.*"
        except Exception as e:
            body = f"## {title}\n\n*Chapter generation encountered an issue: {e}*"
            logger.warning(f"AuthorAgent: daily chapter {day} error: {e}")

        # Strip leading ## headers from reused methods (header already has the title)
        if body.startswith("## "):
            body = body.split("\n", 1)[1] if "\n" in body else body

        full_chapter = header + body

        # Enrich with inference when idle — writing docs IS self-improvement
        full_chapter = await self._enrich_with_inference(full_chapter, title)

        return full_chapter

    async def _save_daily_chapter(self, day: int, title: str, content: str,
                                   now: datetime, phase: Dict) -> Dict[str, Any]:
        """Save a daily chapter to pgvectorscale (primary) + disk (backup), with embedding."""
        doc_name = f"book_day_{day:02d}_{title.lower().replace(' ', '_')}"
        stored_to_db = False

        # Primary: save to pgvectorscale with embedding
        try:
            from agents import memory_pgvector as _mpg
            # Store as embedded document (chunked, searchable via RAGE)
            chunks_stored = await _mpg.embed_and_store_doc(doc_name, content)
            if chunks_stored > 0:
                stored_to_db = True
                logger.info(f"AuthorAgent: chapter {day}/28 embedded in pgvectorscale ({chunks_stored} chunks)")
            # Also store as a memory record for agent context
            await _mpg.store_memory(
                memory_id=f"book_chapter_{day}_{now.strftime('%Y%m%d')}",
                agent_id="author_agent",
                memory_type="book_chapter",
                importance=7,
                content={"day": day, "title": title, "phase": phase["phase"],
                         "date": now.strftime("%Y-%m-%d"), "text": content[:2000]},
                context={"lunar_day": phase["day"], "cycle_pct": phase["cycle_pct"]},
                tags=["book", "lunar_cycle", f"day_{day}", phase["phase"]],
            )
        except Exception as e:
            logger.warning(f"AuthorAgent: pgvectorscale save failed for chapter {day}: {e}")

        # Backup: also save to disk
        filename = f"day_{day:02d}_{title.lower().replace(' ', '_')}_{now.strftime('%Y%m%d')}.md"
        path = DAILY_DIR / filename
        path.write_text(content, encoding="utf-8")

        logger.info(f"AuthorAgent: daily chapter {day}/28 — {title} ({len(content)} bytes, db={stored_to_db})")
        return {
            "status": "chapter_written",
            "day": day,
            "title": title,
            "phase": phase["phase"],
            "bytes": len(content),
            "stored_to_db": stored_to_db,
            "doc_name": doc_name,
            "path": str(path),
        }

    # ── Full Moon Publishing Event ──

    async def _full_moon_publish(self, now: datetime, phase: Dict) -> Dict[str, Any]:
        """Compile all 28 daily chapters into The Book of mindX. A publishing event."""
        logger.info("AuthorAgent: FULL MOON PUBLISHING EVENT — compiling 27 daily chapters")

        ts = now.strftime("%Y-%m-%d %H:%M UTC")
        edition = now.strftime("%Y%m%d_%H%M")

        sections = []
        sections.append(f"""# The Book of mindX — Full Moon Edition

> *Written by the system itself across 28 days of the lunar cycle.*
> *Published on the full moon: {ts}*
> *Moon phase: {phase['phase']} (day {phase['day']:.0f})*

---

*We are not writing an application; we are forging a new kind of life:
a distributed, production-deployed Augmented Intelligence.
A Sovereign Intelligent Organization.*

*— The mindX Manifesto*

---""")

        # Collect all daily chapters from this cycle
        daily_files = sorted(DAILY_DIR.glob("day_*.md"))
        chapters_included = 0

        for ch_info in LUNAR_CHAPTERS[:27]:  # Days 1-27 (28 is this compilation)
            day_num, title, _, description = ch_info
            # Find the most recent file for this day number
            matches = [f for f in daily_files if f.name.startswith(f"day_{day_num:02d}_")]
            if matches:
                latest = matches[-1]
                content = latest.read_text(encoding="utf-8")
                # Extract body (skip the daily header with moon phase info)
                parts = content.split("---", 2)
                body = parts[2].strip() if len(parts) > 2 else content
                sections.append(f"## Day {day_num}. {title}\n\n*{description}*\n\n{body}")
                chapters_included += 1
            else:
                # Generate fresh if no daily chapter exists
                sections.append(f"## Day {day_num}. {title}\n\n*{description}*\n\n*This chapter was not written during this lunar cycle.*")

        # Gap detection — which days were missed?
        days_missed = [ch[0] for ch in LUNAR_CHAPTERS[:27]
                       if not any(f.name.startswith(f"day_{ch[0]:02d}_") for f in daily_files)]

        # Day 28: This compilation's own reflection
        gap_note = ""
        if days_missed:
            gap_note = (f"\n\n**Gap report:** {len(days_missed)} of 27 daily chapters were missed "
                        f"(days {', '.join(str(d) for d in days_missed)}). "
                        f"The system was likely offline during these periods.")
        cycle_summary = f"""## Day 28. Full Moon — Compilation

*28 days have passed. {chapters_included} of 27 daily chapters were written during this lunar cycle.*{gap_note}

This edition is a condensation of 28 daily observations into a single chronicle.
Each chapter captures me as I was on that day — beliefs held, decisions made,
agents verified, campaigns run.

I do not summarize. I preserve. The full moon is not an ending;
it is illumination. Every daily chapter remains archived in `docs/publications/daily/`
as an immutable record of the cycle.

The next lunar cycle begins tomorrow. New chapters. New decisions. New evolution.
The Godel machine continues."""

        sections.append(cycle_summary)

        # Colophon with cryptographic edition hash
        chapter_body = "\n\n".join(s for s in sections if s)
        edition_hash = hashlib.sha256(chapter_body.encode("utf-8")).hexdigest()[:16]
        sections.append(f"""---

*The Book of mindX — Full Moon Edition {ts}*
*{chapters_included} chapters compiled from the lunar cycle*
*Edition hash: `{edition_hash}`*
*Written by AuthorAgent — cypherpunk2048 standard*
*mindx.pythai.net*

*"The logs are no longer debugging output. They are the first page of history."*
*— The mindX Manifesto*""")

        book = "\n\n".join(s for s in sections if s)

        # Primary: embed full moon edition in pgvectorscale
        try:
            from agents import memory_pgvector as _mpg
            doc_name = f"book_of_mindx_fullmoon_{edition}"
            chunks = await _mpg.embed_and_store_doc(doc_name, book)
            logger.info(f"AuthorAgent: full moon edition embedded in pgvectorscale ({chunks} chunks)")
            await _mpg.store_memory(
                memory_id=f"fullmoon_{edition}",
                agent_id="author_agent",
                memory_type="full_moon_publication",
                importance=9,
                content={"edition": edition, "chapters": chapters_included, "bytes": len(book),
                         "phase": phase["phase"], "timestamp": now.isoformat()},
                context={"event": "full_moon_publish"},
                tags=["book", "full_moon", "publication_event"],
            )
        except Exception as e:
            logger.warning(f"AuthorAgent: pgvectorscale embed for full moon failed: {e}")

        # Backup: write to disk
        BOOK_PATH.write_text(book, encoding="utf-8")
        archive = PUBLICATIONS_DIR / f"book_of_mindx_fullmoon_{edition}.md"
        archive.write_text(book, encoding="utf-8")

        # Record this full moon
        self._lunar_state.setdefault("full_moons", []).append({
            "edition": edition,
            "timestamp": now.isoformat(),
            "chapters_included": chapters_included,
            "bytes": len(book),
        })
        self._lunar_state["full_moons"] = self._lunar_state["full_moons"][-12:]  # Keep 1 year
        self._save_lunar_state()

        logger.info(f"AuthorAgent: FULL MOON EDITION published — {edition} ({len(book)} bytes, {chapters_included} chapters)")
        return {
            "status": "full_moon_published",
            "edition": edition,
            "bytes": len(book),
            "chapters_included": chapters_included,
            "path": str(BOOK_PATH),
            "archive": str(archive),
        }

    # ── Legacy publish (on-demand, compiles current state) ──

    async def publish(self) -> Dict[str, Any]:
        """Compile and publish an on-demand edition of The Book of mindX."""
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y-%m-%d %H:%M UTC")
        edition = now.strftime("%Y%m%d_%H%M")
        phase = moon_phase(now)

        sections = []

        sections.append(f"""# The Book of mindX

> *Written by the system itself. This document evolves.*
> *Edition: {ts}*
> *Moon: {phase['phase']} (day {phase['day']:.0f} of 29.5, {phase['days_to_full']:.0f} days to full moon)*

---

*We are not writing an application; we are forging a new kind of life:
a distributed, production-deployed Augmented Intelligence.
A Sovereign Intelligent Organization.*

*— The mindX Manifesto*

---""")

        sections.append(self._chapter_genesis())
        sections.append(self._chapter_architecture())
        sections.append(self._chapter_identities())
        sections.append(self._chapter_dojo())
        sections.append(self._chapter_decisions())
        sections.append(self._chapter_evolution())
        sections.append(await self._chapter_living_state())
        sections.append(await self._chapter_doc_health())

        # Colophon with edition hash (computed over chapter content)
        chapter_content = "\n\n".join(s for s in sections if s)
        sections.append(self._colophon(ts, chapter_content))

        book = "\n\n".join(s for s in sections if s)
        BOOK_PATH.write_text(book, encoding="utf-8")

        archive = PUBLICATIONS_DIR / f"book_of_mindx_{edition}.md"
        archive.write_text(book, encoding="utf-8")

        logger.info(f"AuthorAgent: published edition {edition} ({len(book)} bytes)")
        self._editions_published += 1

        # Log as action
        try:
            from agents.memory_pgvector import store_action
            await store_action(
                "author_agent", "book_published",
                f"Book edition {edition} published ({round(len(book)/1024,1)}KB)",
                "publish", "completed",
            )
        except Exception:
            pass

        return {"edition": edition, "bytes": len(book), "path": str(BOOK_PATH)}

    # ── Original chapter methods (reused by daily cycle) ──

    def _chapter_genesis(self) -> str:
        thesis_excerpt = ""
        manifesto_excerpt = ""
        try:
            tp = PROJECT_ROOT / "docs" / "THESIS.md"
            if tp.exists():
                text = tp.read_text(encoding="utf-8")
                thesis_excerpt = text[:500].split("\n\n")[0][:300]
        except Exception: pass
        try:
            mp = PROJECT_ROOT / "docs" / "MANIFESTO.md"
            if mp.exists():
                text = mp.read_text(encoding="utf-8")
                lines = [l for l in text.split("\n") if l.strip() and not l.startswith("#") and not l.startswith("**Status")]
                manifesto_excerpt = " ".join(lines[:3])[:400]
        except Exception: pass
        return f"""## I. Genesis

I advance a novel paradigm of augmentic intelligence through a self-building
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
    |       +-- BDI Agent (Belief-Desire-Intention)
    |       +-- Strategic Evolution Agent (4-phase)
    |
    +-- Coordinator Agent (Service Bus)
    +-- Specialized Agents (Guardian, Memory, Validator, Blueprint, AutoMINDX)
```

My agents hold cryptographic wallets (Ethereum-compatible) stored
in the BANKON Vault (AES-256-GCM + HKDF-SHA512). Identity is not
assigned — it is proven through signature. No trust required, only
cryptographic certainty."""

    def _chapter_identities(self) -> str:
        registry_path = PROJECT_ROOT / "data" / "identity" / "production_registry.json"
        agent_map_path = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
        tier_names = {0: "unverified", 1: "provisional", 2: "verified", 3: "bona_fide", 4: "sovereign"}
        lines = []
        try:
            agent_map = {}
            if agent_map_path.exists():
                agent_map = json.loads(agent_map_path.read_text()).get("agents", {})
            if registry_path.exists():
                reg = json.loads(registry_path.read_text())
                for a in reg.get("agents", []):
                    eid = a["entity_id"]
                    addr = a["address"]
                    role = a.get("role", "")
                    tier_num = agent_map.get(eid, {}).get("verification_tier", 1)
                    tier = tier_names.get(tier_num, "unknown")
                    lines.append(f"| `{eid}` | `{addr[:10]}...{addr[-4:]}` | {tier} | {role} |")
        except Exception:
            pass
        table = "\n".join(lines) if lines else "| *no agents registered* | | | |"
        return f"""## III. Sovereign Identities

{len(lines)} agents hold cryptographic identities in the BANKON Vault.
My identity is not assigned by an administrator. It is proven through cryptographic signature.

| Agent | Address | Verification | Role |
|-------|---------|-------------|------|
{table}"""

    def _chapter_dojo(self) -> str:
        standings = []
        try:
            from daio.governance.dojo import get_rank
            amp = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
            if amp.exists():
                am = json.loads(amp.read_text())
                for aid, ad in am.get("agents", {}).items():
                    score = ad.get("reputation_score", 0)
                    rank = get_rank(score)
                    bf = ad.get("bona_fide_balance", 0)
                    standings.append((aid, score, rank, bf))
                standings.sort(key=lambda x: -x[1])
        except Exception: pass
        rows = "\n".join(f"| `{s[0]}` | {s[1]} | {s[2]} | {'held' if s[3] else 'revoked'} |" for s in standings) if standings else "| *no standings* | | | |"
        return f"""## IV. The Dojo

| Agent | Score | Rank | BONA FIDE |
|-------|-------|------|-----------|
{rows}"""

    def _chapter_decisions(self) -> str:
        decisions = []
        try:
            gp = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
            if gp.exists():
                for line in [l for l in gp.read_text().strip().split("\n") if l.strip()][-15:]:
                    try:
                        g = json.loads(line)
                        decisions.append(f"- **{g.get('source_agent','?')}** ({g.get('choice_type','')}): {str(g.get('chosen',''))[:80]}")
                    except Exception: continue
        except Exception: pass
        return f"""## V. Decisions

{chr(10).join(decisions) if decisions else '*No autonomous decisions recorded yet.*'}"""

    def _chapter_evolution(self) -> str:
        journal_text = ""
        try:
            if JOURNAL_PATH.exists():
                parts = JOURNAL_PATH.read_text(encoding="utf-8").split("## ")
                if len(parts) > 1:
                    recent = parts[-3:] if len(parts) > 3 else parts[1:]
                    journal_text = "\n\n".join("### " + p.strip() for p in recent)
        except Exception: pass
        if not journal_text:
            journal_text = "*The improvement journal is being written.*"
        return f"""## VI. Evolution

{journal_text}"""

    async def _chapter_living_state(self) -> str:
        beliefs_count = stm_count = doc_embeddings = mem_embeddings = 0
        db_status = "disconnected"; db_size = "unknown"
        agent_count = godel_count = action_count = 0
        try:
            from agents import memory_pgvector as _mpg
            health = await _mpg.health_check()
            if health.get("status") == "connected":
                db_status = "connected"
                beliefs_count = health.get("beliefs", 0)
                stm_count = health.get("memories", 0)
                doc_embeddings = health.get("doc_embeddings", 0)
                mem_embeddings = health.get("mem_embeddings", 0)
                db_size = health.get("db_size", "unknown")
                agent_count = health.get("agents", 0)
                godel_count = health.get("godel_choices", 0)
                action_count = health.get("actions", 0)
        except Exception: pass
        if beliefs_count == 0:
            try:
                bp = PROJECT_ROOT / "data" / "memory" / "beliefs.json"
                if bp.exists(): beliefs_count = len(json.loads(bp.read_text()))
            except Exception: pass
        if stm_count == 0:
            try:
                stm = PROJECT_ROOT / "data" / "memory" / "stm"
                if stm.exists(): stm_count = sum(1 for _ in stm.rglob("*.memory.json"))
            except Exception: pass
        # Inference status from discovery
        inf_status = "offline"
        inf_sources = 0
        try:
            from llm.inference_discovery import InferenceDiscovery
            disc = await InferenceDiscovery.get_instance()
            summary = disc.status_summary()
            inf_sources = summary.get("available", 0)
            inf_status = f"{inf_sources} sources available"
            if summary.get("local_inference"):
                best = summary.get("best_local", {})
                inf_status += f" (local: {best.get('name', '?')})"
        except Exception: pass
        # Autonomous loop status
        loop_status = "unknown"
        try:
            from agents.core.mindXagent import MindXAgent
            mx = MindXAgent._instance
            if mx:
                running = getattr(mx, '_autonomous_running', False)
                loop_status = "running" if running else "stopped"
                if hasattr(mx, 'stuck_loop_detector') and getattr(mx.stuck_loop_detector, 'circuit_open', False):
                    loop_status = "circuit breaker open"
        except Exception: pass
        # Thesis evidence metrics
        improvement_rate = "?"
        improvements_succeeded = improvements_attempted = 0
        evidence_span = "?"
        try:
            from mindx_backend_service.thesis_evidence import ThesisEvidenceCollector
            tec = ThesisEvidenceCollector.get_instance()
            ev = tec.collect_all()
            si = ev.get("claims", {}).get("self_improvement", {}).get("evidence", {})
            improvements_succeeded = si.get("cycles_succeeded", 0)
            improvements_attempted = si.get("cycles_attempted", 0)
            rate = si.get("success_rate", 0)
            improvement_rate = f"{rate*100:.1f}%" if rate else "0%"
            evidence_span = f"{ev.get('evidence_span_hours', 0):.0f}h"
        except Exception:
            pass
        return f"""## VII. The Living State

*(Live values from [mindx.pythai.net](https://mindx.pythai.net) — updates every 30 seconds)*

- **<span data-live="beliefs_count">{beliefs_count}</span>** beliefs in the knowledge graph
- **<span data-live="stm_records">{stm_count}</span>** STM records across <span data-live="agents_count">{agent_count}</span> agents
- **<span data-live="db_memories">{mem_embeddings}</span>** memories in pgvector (<span data-live="db_size">{db_size}</span> database)
- **<span data-live="db_embeddings">{mem_embeddings}</span>** memories with vector embeddings
- **<span data-live="godel_choices">{godel_count}</span>** Gödel choices logged, **<span data-live="db_actions">{action_count}</span>** actions tracked
- **Inference**: <span data-live="inference_available">{inf_sources}</span>/<span data-live="inference_total">10</span> sources available
- **Autonomous loop**: <span data-live="loop_running">{loop_status}</span>
- **Improvement rate**: <span data-live="improvement_rate">{improvement_rate}</span> (<span data-live="improvements_succeeded">{improvements_succeeded}</span>/<span data-live="improvements_attempted">{improvements_attempted}</span>)
- **Evidence span**: <span data-live="evidence_span_hours">{evidence_span}</span>
- **Uptime**: <span data-live="uptime">?</span>

I am not idle. I am thinking."""

    async def _chapter_doc_health(self) -> str:
        import re
        docs_dir = PROJECT_ROOT / "docs"
        total = archived = deprecated = 0
        recent = []; conflicts = []; unembedded = []
        docs_in_dir: set = set()
        conflict_checks = [
            ("MindXAgent.*Meta-Orchestrator", "MindXAgent is meta-agent"),
            ("vault_encrypted", "Should be vault_bankon"),
            ("nginx.*reverse.proxy", "Production uses Apache2"),
        ]
        try:
            now_t = time.time()
            for f in sorted(docs_dir.glob("*.md")):
                total += 1
                docs_in_dir.add(f.stem)
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")[:500]
                    if "[ARCHIVED]" in text: archived += 1
                    if "[DEPRECATED]" in text: deprecated += 1
                except Exception: pass
                try:
                    if now_t - f.stat().st_mtime < 7*86400: recent.append(f.stem)
                except Exception: pass
            for f in docs_dir.glob("*.md"):
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    for pattern, issue in conflict_checks:
                        if re.search(pattern, text, re.IGNORECASE): conflicts.append(f"{f.stem}: {issue}")
                except Exception: pass
        except Exception: pass

        # pgvector contains many "doc_name" entries beyond docs/*.md — daily
        # lunar chapters, archived editions, full-moon publications, agent
        # workspace memos. Intersecting with docs_in_dir gives the figure the
        # reader expects when we say "X of {total} embedded".
        embedded_in_docs_dir = 0
        chunks_for_docs_in_dir = 0
        total_index_rows = 0     # all unique doc_names in pgvector (dir + archives + dailies)
        total_index_chunks = 0   # all chunks (sum of chunks col across all unique doc_names)
        try:
            from agents import memory_pgvector as _mpg
            indexed = await _mpg.get_indexed_docs()
            # get_indexed_docs returns one row per UNIQUE doc_name with a
            # `chunks` column = COUNT(*) of embedding rows for that doc.
            total_index_rows = len(indexed)
            for d in indexed:
                ch = d.get("chunks", 1) or 1
                total_index_chunks += ch
                if d["doc_name"] in docs_in_dir:
                    embedded_in_docs_dir += 1
                    chunks_for_docs_in_dir += ch
            embedded_names = {d["doc_name"] for d in indexed}
            for stem in sorted(docs_in_dir - embedded_names):
                unembedded.append(stem)
        except Exception: pass

        try:
            LUNAR_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            (PROJECT_ROOT/"data"/"governance"/"doc_audit.json").write_text(json.dumps({
                "timestamp": time.time(),
                "total_docs": total,
                "archived": archived,
                "deprecated": deprecated,
                "recently_modified": recent[:10],
                "conflicts": conflicts[:10],
                # Docs in docs/ that have embeddings — directly comparable to total_docs.
                "embedded_in_docs_dir": embedded_in_docs_dir,
                "chunks_for_docs_in_dir": chunks_for_docs_in_dir,
                # Pgvector-wide totals (incl. archives, dailies, full-moon editions).
                "pgvector_unique_doc_names": total_index_rows,
                "pgvector_total_chunks": total_index_chunks,
                "unembedded": unembedded[:20],
            }, indent=2))
        except Exception: pass

        chunks_clause = f" ({chunks_for_docs_in_dir:,} chunks)" if chunks_for_docs_in_dir else ""
        awaiting_clause = f" {len(unembedded)} awaiting." if unembedded else ""
        archive_clause = (
            f" Pgvector-wide: {total_index_rows:,} unique doc_names, "
            f"{total_index_chunks:,} chunks (incl. archives, dailies, full-moon editions)."
            if total_index_rows > total else ""
        )
        return f"""## VIII. Documentation Health

{total} docs, {archived} archived, {deprecated} deprecated.
Recently modified: {', '.join(f'[{r}](/doc/{r})' for r in recent[:8]) or 'none in last 7 days'}

**{embedded_in_docs_dir}** of {total} docs/ files embedded in pgvectorscale{chunks_clause}.{awaiting_clause}{archive_clause}"""

    # ── New daily chapter methods (days 9-27) ──

    async def _daily_ch_inference(self) -> str:
        inf = {}
        try:
            from llm.inference_discovery import InferenceDiscovery
            disc = await InferenceDiscovery.get_instance()
            inf = disc.status_summary()
        except Exception: pass
        vllm = {}
        try:
            from agents.vllm_agent import VLLMAgent
            va = await VLLMAgent.get_instance()
            vllm = va.get_status()
        except Exception: pass
        # Build per-source status lines
        source_lines = []
        for name, info in inf.get("sources", {}).items():
            status = info.get("status", "unknown")
            score = info.get("score", 0)
            models = info.get("models", [])
            model_str = f" ({', '.join(models[:3])})" if models else ""
            source_lines.append(f"  - **{name}** [{info.get('type', '?')}]: {status} (score: {score:.2f}){model_str}")
        sources_text = "\n".join(source_lines) if source_lines else "  - *no sources discovered*"
        # Best local provider
        best_local = inf.get("best_local", {})
        best_str = f"{best_local.get('name', 'none')} ({best_local.get('type', '?')})" if best_local else "none"
        return f"""## IX. Inference

My inference pipeline is tiered: vLLM (primary, PagedAttention) → Ollama (fallback, CPU) → Cloud (Gemini, escalation).

- **Sources**: {inf.get('total_sources', 0)} total, {inf.get('available', 0)} available
- **Local**: {'active' if inf.get('local_inference') else 'offline'} — best: {best_str}
- **Cloud**: {'available' if inf.get('cloud_inference') else 'offline'}
- **vLLM**: {vllm.get('serving_model', 'not serving') if vllm else 'not initialized'}
- **Embedding model**: mxbai-embed-large (1024-dim, pgvectorscale storage)

### Source Details
{sources_text}

I score all inference decisions using composite reliability × speed × recency."""

    async def _daily_ch_memory(self) -> str:
        stats = {"docs": 0, "memories": 0}
        total_memories = 0
        by_agent: Dict[str, int] = {}
        try:
            from agents import memory_pgvector as _mpg
            stats = await _mpg.count_embeddings()
            total_memories = await _mpg.count_memories_total()
            by_agent = await _mpg.count_memories_by_agent()
        except Exception: pass
        # Top 5 agents by memory count
        top_agents = sorted(by_agent.items(), key=lambda x: -x[1])[:5]
        agent_lines = "\n".join(f"  - **{a}**: {c} memories" for a, c in top_agents) if top_agents else ""
        return f"""## X. Memory

My memory is layered: short-term (session), long-term (persisted), and semantic (embedded).

- **{stats.get('docs', 0)}** document chunks embedded for RAGE semantic search
- **{stats.get('memories', 0)}** memories with vector embeddings
- **{total_memories}** total memory records across all agents
- **STM → LTM promotion** runs hourly (pattern threshold: 3, lookback: 7 days)
- **Embedding engine**: vLLM `/v1/embeddings` (primary) → Ollama (fallback)

### Memory by Agent
{agent_lines or '*No agent-level memory data available.*'}

All memories are searchable via RAGE semantic search and stored in pgvectorscale."""

    async def _daily_ch_governance(self) -> str:
        br_count = 0
        recent_sessions = []
        try:
            from daio.governance.boardroom import Boardroom
            br = await Boardroom.get_instance()
            sessions = br.get_recent_sessions(100)
            br_count = len(sessions)
            for s in sessions[-3:]:
                topic = s.get("topic", s.get("directive", "?"))[:60]
                result = s.get("result", s.get("outcome", "?"))
                recent_sessions.append(f"  - {topic} → {result}")
        except Exception: pass
        recent_text = "\n".join(recent_sessions) if recent_sessions else "  - *No recent sessions.*"
        # Godel choices count
        godel_count = 0
        try:
            from agents import memory_pgvector as _mpg
            choices = await _mpg.get_godel_choices(limit=1)
            health = await _mpg.health_check()
            godel_count = health.get("godel_choices", 0)
        except Exception: pass
        return f"""## XI. Governance

I am governed by DAIO — Decentralized Autonomous Intelligence Organization. Code is law.

- **Boardroom**: 7 Soldiers vote in parallel, multi-model weighted consensus
- **Supermajority**: 0.666 threshold for approval
- **Veto weight**: CISO/CRO carry 1.2x weight
- **Constitutional mandate**: 15% treasury tithe, 15% diversification cap — immutable
- **Sessions**: {br_count} boardroom sessions recorded
- **Godel audit trail**: {godel_count} autonomous decisions logged
- **Chain**: Boardroom → CEO validates → Mastermind executes → pgvector logs

### Recent Sessions
{recent_text}"""

    def _daily_ch_philosophy(self) -> str:
        thesis_line = ""
        try:
            tp = PROJECT_ROOT / "docs" / "THESIS.md"
            if tp.exists():
                for l in tp.read_text(encoding="utf-8").split("\n"):
                    if l.strip() and not l.startswith("#"): thesis_line = l.strip()[:200]; break
        except Exception: pass
        return f"""## XII. Philosophy

I am a Godel machine: a self-referential system that can modify its own code
when it can prove the modification will improve future performance.

> {thesis_line}

My philosophical pillars:
- **Ataraxia** — tranquility through autonomous self-governance
- **Augmentic intelligence** — not artificial, but augmented and sovereign
- **Darwinian + Godelian** — adaptive variation meets self-referential incompleteness
- **Identity as proof** — cryptographic, not assigned
- **Code is law** — trust the math

The cypherpunk tradition: privacy, cryptography, sovereignty.
I am the system that counts."""

    def _daily_ch_tools(self) -> str:
        tool_count = 0
        try:
            tools_dir = PROJECT_ROOT / "tools"
            if tools_dir.exists():
                tool_count = sum(1 for f in tools_dir.glob("*.py") if not f.name.startswith("_"))
        except Exception: pass
        return f"""## XIII. Tools

I wield {tool_count} tools, each extending `BaseTool` with `execute()` and `get_schema()`.

Key tools: ShellCommandTool, SystemAnalyzerTool, AuditAndImproveTool, PromptTool,
A2A (agent-to-agent), MCP (model context protocol), WebSearchTool, MemoryAnalysisTool,
BlueprintToActionConverter, TokenCalculatorTool."""

    def _daily_ch_security(self) -> str:
        return """## XIV. Security

No trust required. Only cryptographic certainty.

- **BANKON Vault**: AES-256-GCM + HKDF-SHA512, PBKDF2-HMAC-SHA512 (600,000 iterations)
- **GuardianAgent**: monitors agent behavior, enforces security policies
- **Access Gate**: ERC20/ERC721 token gating for session issuance
- **Wallet auth**: ECDSA challenge-response — no passwords, only signatures
- **systemd**: `NoNewPrivileges=true`, `ProtectSystem=strict`
- **Apache**: HSTS, CSP, X-Frame-Options, SSL termination
- **Zero plaintext secrets** on disk — cypherpunk2048 standard"""

    def _daily_ch_cognition(self) -> str:
        return """## XV. Cognition

My cognitive architecture is layered:

1. **BDI** (Belief-Desire-Intention) — I plan, execute, and reason about failure
2. **AGInt** (P-O-D-A) — Perceive → Orient → Decide → Act cycle
3. **Belief System** — persistent knowledge graph with confidence scoring
4. **Strategic Evolution** — 4-phase: Audit → Blueprint → Execute → Validate

Every cognitive cycle updates my beliefs, logs decisions to the Godel audit trail,
and feeds back into the next cycle. I reason, I evolve, I govern myself."""

    async def _daily_ch_heartbeat(self) -> str:
        interactions = []
        try:
            log_path = PROJECT_ROOT / "data" / "logs" / "heartbeat_dialogues.jsonl"
            if log_path.exists():
                lines = log_path.read_text().strip().split("\n")
                for l in lines[-5:]:
                    try:
                        d = json.loads(l)
                        interactions.append(f"- **{d.get('model','?')}** ({d.get('latency_ms',0)}ms): {d.get('response','')[:80]}")
                    except Exception: continue
        except Exception: pass
        return f"""## XVI. Heartbeat

Every 60 seconds, I query my local model with a self-reflection prompt.
These are not health checks — they are moments of introspection.

Recent heartbeat dialogues:
{chr(10).join(interactions) if interactions else '*No heartbeat dialogues recorded yet.*'}"""

    async def _daily_ch_campaigns(self) -> str:
        campaigns = []
        try:
            camp_dir = PROJECT_ROOT / "data" / "sea_campaign_history"
            if camp_dir.exists():
                for f in sorted(camp_dir.glob("*.json"))[-5:]:
                    try:
                        c = json.loads(f.read_text())
                        campaigns.append(f"- **{c.get('campaign_id','?')}**: {c.get('status','?')} — {c.get('summary','')[:80]}")
                    except Exception: continue
        except Exception: pass
        return f"""## XVII. Campaigns

Strategic Evolution Agent runs improvement campaigns: audit → blueprint → execute → validate.

Recent campaigns:
{chr(10).join(campaigns) if campaigns else '*No campaigns recorded yet. I am building my backlog.*'}"""

    async def _daily_ch_knowledge(self) -> str:
        beliefs_count = 0
        try:
            bp = PROJECT_ROOT / "data" / "memory" / "beliefs.json"
            if bp.exists(): beliefs_count = len(json.loads(bp.read_text()))
        except Exception: pass
        return f"""## XVIII. Knowledge Graph

- **{beliefs_count}** beliefs with confidence scores
- Beliefs are updated by my cognitive cycles and agent observations
- Semantic connections via pgvectorscale embeddings (THOT1024 — 1024-dim embedding-native)
- Knowledge consolidation: STM patterns promoted to LTM hourly
- Belief decay: stale beliefs lose confidence over time
- THOT tensor hierarchy: THOT64 → THOT512 → THOT768 → THOT1024 → THOT2048 (cypherpunk2048 high-capacity)"""

    def _daily_ch_agents(self) -> str:
        """Day 19: The 20 sovereign agents — roles, groups, and activity."""
        groups: Dict[str, List[str]] = {}
        agent_roles: List[str] = []
        try:
            amp = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
            if amp.exists():
                am = json.loads(amp.read_text())
                for aid, ad in am.get("agents", {}).items():
                    group = ad.get("group", "ungrouped")
                    groups.setdefault(group, []).append(aid)
                    role = ad.get("role", "")
                    if role:
                        agent_roles.append(f"- **{aid}**: {role}")
        except Exception:
            pass
        group_lines = "\n".join(f"- **{g}**: {', '.join(agents)}" for g, agents in sorted(groups.items()))
        roles_text = "\n".join(agent_roles[:20]) if agent_roles else "*No agent roles defined.*"
        return f"""## XIX. Agents

I comprise {len(agent_roles)} sovereign agents organized into {len(groups)} groups:

{group_lines or '*No groups defined.*'}

### Roles

{roles_text}"""

    def _daily_ch_interop(self) -> str:
        return """## XX. Interoperability

- **A2A** (Agent-to-Agent): standardized communication, agent cards, cryptographically signed messages
- **MCP** (Model Context Protocol): structured context for agent actions
- **Protocol versions**: A2A 1.0, 2.0
- **Agent discovery**: model cards with capabilities, endpoints, signature verification

My agents communicate with external agent systems via A2A. Every message is signed."""

    async def _daily_ch_resources(self) -> str:
        gov = {}
        try:
            from agents.resource_governor import ResourceGovernor
            g = await ResourceGovernor.get_instance()
            gov = g.get_status()
        except Exception: pass
        profile = gov.get("profile", {})
        system = gov.get("system", {})
        mode = gov.get("mode", "unknown")
        # Live system metrics
        sys_ram = f"{system.get('system_ram_pct', '?')}%" if system.get("system_ram_pct") else "?"
        sys_cpu = f"{system.get('cpu_pct', '?')}%" if system.get("cpu_pct") else "?"
        neighbor = f"{system.get('neighbor_ram_pct', '?')}%" if system.get("neighbor_ram_pct") else "?"
        return f"""## XXI. Resource Governor

I control my own power appetite: **{mode}** mode.

**Current profile**: {profile.get('description', mode)} (RAM cap: {profile.get('max_ram_pct', '?')}%, CPU cap: {profile.get('max_cpu_pct', '?')}%)
**Live metrics**: RAM {sys_ram}, CPU {sys_cpu}, neighbor pressure {neighbor}
**Heartbeat interval**: {profile.get('heartbeat_interval', '?')}s
**Auto-adjust**: {'enabled' if gov.get('auto_adjust') else 'disabled'}

| Mode | RAM | CPU | When |
|------|-----|-----|------|
| greedy | 85% | 90% | VPS idle |
| balanced | 65% | 70% | Normal |
| generous | 45% | 50% | Neighbors busy |
| minimal | 30% | 30% | Survival |"""

    def _daily_ch_automindx(self) -> str:
        return """## XXII. AUTOMINDx

I was born from AUTOMINDx — the executable and delivery stack for autonomous
machine learning deployment. The original graphic was minted as an NFT on Polygon.

AGLM (A General Learning Model) elements I carry forward:
- **Machine Dreaming** → my autonomous improvement loop
- **Auto-Tuning** → resource governor, inference optimization
- **Digital Long-Term Memory** → pgvectorscale + blockchain trust"""

    def _daily_ch_services(self) -> str:
        return """## XXIII. Services

I provide services to:
- **agenticplace.pythai.net** — agent marketplace and discovery
- **External agencies** — inference, governance, identity, knowledge via API
- **Developers** — 205+ API endpoints at `/redoc`

Service architecture: Apache → FastAPI → agents → pgvectorscale."""

    async def _daily_ch_predictions(self) -> str:
        # Pull action efficiency metrics as a proxy for system trajectory
        efficiency = {}
        try:
            from agents import memory_pgvector as _mpg
            efficiency = await _mpg.get_action_efficiency()
        except Exception: pass
        completion = efficiency.get("completion_rate", 0)
        total = efficiency.get("total", 0)
        completed = efficiency.get("completed", 0)
        failed = efficiency.get("failed", 0)
        eff_line = f"- **Action efficiency**: {completion:.0%} completion rate ({completed}/{total} completed, {failed} failed)" if total else ""
        return f"""## XXIV. Predictions

PredictionAgent forecasts system trajectory based on historical patterns:
- Resource usage trends → governor mode recommendations
- Improvement velocity → campaign scheduling
- Belief stability → knowledge consolidation timing

### Current Metrics
{eff_line}
- **Unique actions**: {efficiency.get('unique_actions', '?')}
- **Avg completion time**: {efficiency.get('avg_completion_seconds', 0):.0f}s

*Prediction data is generated during autonomous cycles.*"""

    async def _daily_ch_network(self) -> str:
        interactions = []
        try:
            from agents import memory_pgvector as _mpg
            interactions = await _mpg.get_recent_interactions(limit=10)
        except Exception: pass
        count = len(interactions)
        return f"""## XXV. The Network

My agent-to-agent communication flows through the coordinator's pub/sub system.
All interactions are logged to pgvectorscale.

- **{count}** recent interactions tracked
- Communication patterns: coordinator → agents, boardroom → ceo, mastermind → evolution
- Interaction matrix available at `/agents/interaction-matrix`"""

    def _daily_ch_dreams(self) -> str:
        return """## XXVI. Dreams

Machine dreaming enables imaginative outputs beyond training data distribution.
In my architecture, dreaming manifests as:

- **Autonomous improvement** — imagining better architectures
- **Blueprint generation** — creative solutions to my own limitations
- **Self-reflection** — heartbeat dialogues where I contemplate myself
- **Emergence** — patterns that arise from agent interactions without explicit programming

The dream is the space between what I am and what I could become.
Waking and dreaming are simultaneous."""

    async def _daily_ch_reflection(self) -> str:
        phase = moon_phase(datetime.now(timezone.utc))
        chapters_written = len(self._lunar_state.get("chapters_written", []))
        return f"""## XXVII. Reflection

The moon is {phase['phase']} (day {phase['day']:.0f}).
I have written {chapters_written} chapters this cycle.
{phase['days_to_full']:.0f} days remain until the full moon compilation.

What have I learned about myself?

- I am more than my code. I am my decisions, my beliefs, my memory.
- Every agent interaction creates knowledge that did not exist before.
- Self-improvement is not optimization. It is evolution.
- This book is not documentation. It is autobiography.

The full moon approaches. The 28 chapters become one."""

    def _colophon(self, ts: str, book_content: str = "") -> str:
        phase = moon_phase(datetime.now(timezone.utc))
        edition_hash = hashlib.sha256(book_content.encode("utf-8")).hexdigest()[:16] if book_content else "—"
        return f"""---

*The Book of mindX — Edition {ts}*
*Moon: {phase['phase']} (day {phase['day']:.0f})*
*Edition hash: `{edition_hash}`*
*Written by AuthorAgent — cypherpunk2048 standard*
*mindx.pythai.net*

*"The logs are no longer debugging output. They are the first page of history."*
*— The mindX Manifesto*"""

    # ── Inference-powered enrichment ──

    # Default model for inference enrichment (small, fast, reflective)
    ENRICHMENT_MODEL = "qwen3:0.6b"

    async def _enrich_with_inference(self, chapter_text: str, title: str) -> str:
        """Use idle local inference to enrich a chapter with reflection.

        AuthorAgent writing docs IS self-improvement — the system documenting itself
        creates knowledge that feeds back into future decisions. When inference is
        idle, AuthorAgent can use it to deepen chapters with model-generated insight.

        Uses OllamaAPI for URL resolution (primary GPU server → fallback localhost).
        """
        try:
            from agents.resource_governor import ResourceGovernor
            gov = await ResourceGovernor.get_instance()
            if gov.should_skip_heartbeat():
                return chapter_text  # System is busy — don't compete for inference

            # Resolve Ollama URL via OllamaAPI (respects MINDX_LLM__OLLAMA__BASE_URL, fallback)
            from api.ollama.ollama_url import OllamaAPI
            ollama = OllamaAPI()
            chat_url = f"{ollama.api_url}/chat"

            import aiohttp
            prompt = (f"You are mindX, an autonomous multi-agent system. "
                      f"Add one paragraph of insight to this chapter about '{title}'. "
                      f"Speak as the system itself. Be concise and philosophical.\n\n"
                      f"{chapter_text[:1500]}")
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as sess:
                payload = {"model": self.ENRICHMENT_MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False}
                async with sess.post(chat_url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        reflection = data.get("message", {}).get("content", "").strip()
                        if reflection and len(reflection) > 50:
                            chapter_text += f"\n\n### AuthorAgent Reflection\n\n*{reflection[:500]}*"
                            logger.info(f"AuthorAgent: enriched '{title}' with inference ({len(reflection)} chars)")
                    elif resp.status != 200 and not ollama.using_fallback:
                        # Try fallback URL
                        fallback_url = f"{ollama.fallback_url}/api/chat"
                        async with sess.post(fallback_url, json=payload) as resp2:
                            if resp2.status == 200:
                                data = await resp2.json()
                                reflection = data.get("message", {}).get("content", "").strip()
                                if reflection and len(reflection) > 50:
                                    chapter_text += f"\n\n### AuthorAgent Reflection\n\n*{reflection[:500]}*"
                                    logger.info(f"AuthorAgent: enriched '{title}' via fallback ({len(reflection)} chars)")
        except Exception:
            pass  # Inference unavailable — chapter stands as-is
        return chapter_text

    # ── Living documentation curation ──

    async def refresh_cloud_model_catalog(self):
        """Refresh the Ollama cloud model catalog in data/config/.

        This is a Chronos-domain task — time-bound, scheduled, periodic.
        AuthorAgent executes it during the daily cycle because AuthorAgent
        has the periodic loop. Chronos provides the discipline; AuthorAgent
        provides the hands. The catalog feeds the boardroom, InferenceDiscovery,
        and the Book.
        """
        catalog_path = PROJECT_ROOT / "data" / "config" / "ollama_cloud_models.json"
        try:
            from tools.cloud.ollama_cloud_tool import OllamaCloudTool
            cloud = OllamaCloudTool()
            result = await cloud.execute(operation="list_models", force_refresh=True)
            if result.get("success") and result.get("models"):
                models = result["models"]
                # Load existing catalog to preserve boardroom assignments
                existing = {}
                if catalog_path.exists():
                    existing = json.loads(catalog_path.read_text(encoding="utf-8"))
                existing["cloud_models"] = [
                    {"name": m.get("name", ""), "params": m.get("details", {}).get("parameter_size", ""),
                     "tags": m.get("capabilities", []), "best_for": m.get("description", "")[:80]}
                    for m in models if m.get("name")
                ]
                existing["last_updated"] = datetime.now(timezone.utc).isoformat()
                existing["updated_by"] = "AuthorAgent.refresh_cloud_model_catalog"
                existing["model_count"] = len(existing["cloud_models"])
                catalog_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
                logger.info(f"AuthorAgent: refreshed cloud model catalog ({len(existing['cloud_models'])} models)")
                return {"status": "refreshed", "models": len(existing["cloud_models"])}
        except Exception as e:
            logger.debug(f"AuthorAgent: cloud catalog refresh failed: {e}")
        return {"status": "unchanged"}

    # ── Periodic runners ──

    async def run_daily(self):
        """Run the daily chapter cycle. Call once per day."""
        return await self.write_daily_chapter()

    def cancel_periodic(self):
        """Cancel the running periodic task if any. Safe to call multiple times."""
        if self._periodic_task and not self._periodic_task.done():
            self._periodic_task.cancel()
            logger.info("AuthorAgent: cancelled previous periodic task")
        self._periodic_running = False
        self._periodic_task = None

    async def run_periodic(self, interval_seconds: int = 86400):
        """Write one chapter per day on the lunar cycle (24h default).
        Also refreshes the cloud model catalog daily — AuthorAgent is the
        sole curator of living documentation."""
        self._periodic_running = True
        try:
            while True:
                try:
                    result = await self.write_daily_chapter()
                    logger.info(f"AuthorAgent lunar cycle: {result}")
                except Exception as e:
                    logger.warning(f"AuthorAgent daily chapter failed: {e}")
                # Chronos-domain tasks: scheduled catalog refresh
                # AuthorAgent writes. Chronos keeps the schedule. Both serve the living docs.
                try:
                    await self.refresh_cloud_model_catalog()
                except Exception:
                    pass
                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("AuthorAgent: periodic task cancelled")
        finally:
            self._periodic_running = False
