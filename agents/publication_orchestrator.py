# SPDX-License-Identifier: Apache-2.0
"""PublicationOrchestrator — improvement-event-driven WordPress publishing.

mindX publishes to rage.pythai.net when the system actually improves, NOT
on a clock. Two trigger surfaces are wired:

  1. **SEA campaign SUCCESS**. Strategic Evolution Agent appends to
     ``data/sea_campaign_history/strategic_evolution_agent.json`` on each
     campaign completion. We tail it; any new entry with
     ``overall_campaign_status == "SUCCESS"`` is a trigger.

  2. **Full / new moon dream cycle**. Machine dreaming writes
     ``data/memory/dreams/<ts>_dream_report.json`` every 8 hours. We
     watch the directory; reports with ``book_edition_triggered=true``
     (i.e. the lunar phase compiled a new Book of mindX edition) are
     triggers.

Each trigger is debounced with a 30-minute base delay ± 40 % jitter
(reusing the pattern at ``llm/rate_limiter.py:228,300``) so two adjacent
successes do not land at the same wall-clock minute. A persistent
ledger at ``data/governance/published_triggers.json`` records every
already-published ``trigger_id`` so no event triggers a duplicate
article — including across mindX restarts.

A 6-hour hard rate limit (``MIN_GAP_S``) caps the cadence: if SEA
campaigns are bursty, only the first improvement in any 6-hour window
publishes. Subsequent ones are recorded in the ledger as "coalesced"
and skipped — the next publish reflects the cumulative learning.

Defensive throughout: every async task wraps its body in ``try/except``
and re-sleeps on failure rather than dying. Publish failures are
logged and the ledger is NOT updated (so a retry on next loop iteration
is possible).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.config import PROJECT_ROOT

logger = logging.getLogger("agents.publication_orchestrator")


# Defaults — overridable via constructor for tests / dev.
DEFAULT_BASE_DELAY_S    = 1800     # 30 min
DEFAULT_JITTER_FRACTION = 0.4      # ± 40 % → effective window 18-42 min
DEFAULT_MIN_GAP_S       = 21600    # 6 hours
DEFAULT_POLL_INTERVAL_S = 60       # how often watchers check their sources


@dataclass
class LedgerEntry:
    """One persisted publish record."""
    trigger_id: str
    kind: str                         # "sea_campaign_success" | "dream_book_edition" | "coalesced"
    detected_at: float
    published_at: Optional[float] = None
    post_id: Optional[int] = None
    url: Optional[str] = None
    title: Optional[str] = None
    note: Optional[str] = None         # e.g. "coalesced: within MIN_GAP_S"

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class Ledger:
    """Append-only ledger of published (and coalesced) trigger IDs."""
    path: Path
    version: int = 1
    last_published_at: float = 0.0
    published: List[LedgerEntry] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "Ledger":
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                entries = [LedgerEntry(**e) for e in data.get("published", [])]
                return cls(
                    path=path,
                    version=data.get("version", 1),
                    last_published_at=float(data.get("last_published_at", 0.0)),
                    published=entries,
                )
        except Exception as e:
            logger.warning(f"Ledger.load failed for {path}: {e}; starting fresh.")
        return cls(path=path)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = {
            "version": self.version,
            "last_published_at": self.last_published_at,
            "published": [e.to_dict() for e in self.published],
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(body, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def has(self, trigger_id: str) -> bool:
        return any(e.trigger_id == trigger_id for e in self.published)

    def append_published(self, entry: LedgerEntry) -> None:
        self.published.append(entry)
        if entry.published_at:
            self.last_published_at = max(self.last_published_at, entry.published_at)
        self.save()

    def append_coalesced(self, trigger_id: str, kind: str, detected_at: float,
                          note: str) -> None:
        # Record-and-skip — still consumes the trigger_id so we don't loop.
        self.published.append(LedgerEntry(
            trigger_id=trigger_id,
            kind="coalesced",
            detected_at=detected_at,
            note=f"{kind}: {note}",
        ))
        self.save()


class PublicationOrchestrator:
    """Listens to improvement events; publishes via AuthorAgent on a
    debounced, jittered, rate-limited cadence."""

    def __init__(
        self,
        author_agent: Any,                                # AuthorAgent (avoid circular import)
        *,
        sea_history_path: Optional[Path] = None,
        dream_dir: Optional[Path] = None,
        ledger_path: Optional[Path] = None,
        base_delay_s: float = DEFAULT_BASE_DELAY_S,
        jitter_fraction: float = DEFAULT_JITTER_FRACTION,
        min_gap_s: float = DEFAULT_MIN_GAP_S,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    ):
        self.author = author_agent
        self.sea_history_path = Path(
            sea_history_path
            if sea_history_path is not None
            else PROJECT_ROOT / "data" / "sea_campaign_history" / "strategic_evolution_agent.json"
        )
        self.dream_dir = Path(
            dream_dir
            if dream_dir is not None
            else PROJECT_ROOT / "data" / "memory" / "dreams"
        )
        self.ledger_path = Path(
            ledger_path
            if ledger_path is not None
            else PROJECT_ROOT / "data" / "governance" / "published_triggers.json"
        )
        self.base_delay_s = float(base_delay_s)
        self.jitter_fraction = float(jitter_fraction)
        self.min_gap_s = float(min_gap_s)
        self.poll_interval_s = float(poll_interval_s)
        self.ledger = Ledger.load(self.ledger_path)

    # ─── Public watchers (start via asyncio.create_task) ─────────

    async def watch_sea(self) -> None:
        """Poll the SEA campaign history file. New SUCCESS entries become
        triggers. Runs forever; logs and re-sleeps on any failure."""
        logger.info(
            f"PublicationOrchestrator: watching SEA history at {self.sea_history_path} "
            f"(poll={self.poll_interval_s}s)"
        )
        while True:
            try:
                await self._scan_sea_once()
            except Exception as e:  # pragma: no cover — never let the watcher die
                logger.warning(f"watch_sea: scan failed: {e}")
            await asyncio.sleep(self.poll_interval_s)

    async def watch_dreams(self) -> None:
        """Watch the dreams directory for new *_dream_report.json files
        with book_edition_triggered=true. Runs forever."""
        logger.info(
            f"PublicationOrchestrator: watching dreams at {self.dream_dir} "
            f"(poll={self.poll_interval_s}s)"
        )
        while True:
            try:
                await self._scan_dreams_once()
            except Exception as e:  # pragma: no cover
                logger.warning(f"watch_dreams: scan failed: {e}")
            await asyncio.sleep(self.poll_interval_s)

    # ─── Scanners (per-tick) ─────────────────────────────────────

    async def _scan_sea_once(self) -> None:
        """Read SEA history. Any new SUCCESS not already in the ledger
        becomes a scheduled publish."""
        if not self.sea_history_path.exists():
            return
        try:
            entries = json.loads(self.sea_history_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"sea scan: cannot parse {self.sea_history_path}: {e}")
            return
        if not isinstance(entries, list):
            return

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("overall_campaign_status") != "SUCCESS":
                continue
            trigger_id = str(entry.get("campaign_run_id") or "")
            if not trigger_id or self.ledger.has(trigger_id):
                continue
            await self._schedule_publish(
                trigger_id=trigger_id,
                kind="sea_campaign_success",
                payload=entry,
            )

    async def _scan_dreams_once(self) -> None:
        """Walk the dreams directory; pick up new reports with
        book_edition_triggered=true."""
        if not self.dream_dir.exists():
            return
        for path in sorted(self.dream_dir.glob("*_dream_report.json")):
            try:
                report = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(report, dict):
                continue
            if not report.get("book_edition_triggered"):
                continue
            trigger_id = str(report.get("timestamp") or path.stem)
            if self.ledger.has(trigger_id):
                continue
            await self._schedule_publish(
                trigger_id=trigger_id,
                kind="dream_book_edition",
                payload=report,
            )

    # ─── Scheduling + publishing ─────────────────────────────────

    async def _schedule_publish(
        self,
        *,
        trigger_id: str,
        kind: str,
        payload: Dict[str, Any],
    ) -> None:
        """Debounced + jittered publish. Honors MIN_GAP_S rate limit."""
        detected_at = time.time()

        # Rate-limit BEFORE we burn jitter. If the last publish was too
        # recent, coalesce this trigger into the ledger and skip.
        time_since_last = detected_at - self.ledger.last_published_at
        if self.ledger.last_published_at > 0 and time_since_last < self.min_gap_s:
            wait_more = int(self.min_gap_s - time_since_last)
            logger.info(
                f"PublicationOrchestrator: coalescing {trigger_id} "
                f"(kind={kind}, last publish {int(time_since_last)}s ago, "
                f"MIN_GAP_S={int(self.min_gap_s)}s, need {wait_more}s more)"
            )
            self.ledger.append_coalesced(
                trigger_id=trigger_id,
                kind=kind,
                detected_at=detected_at,
                note=f"within MIN_GAP_S={int(self.min_gap_s)}s",
            )
            return

        # Compute the jittered delay. Bound stays within ± jitter_fraction.
        delay = self._compute_delay()
        logger.info(
            f"PublicationOrchestrator: scheduling {kind} {trigger_id} in {int(delay)}s "
            f"(base={int(self.base_delay_s)} ± {self.jitter_fraction:.0%})"
        )
        await asyncio.sleep(delay)

        # Double-check the trigger wasn't published while we slept
        # (could happen if a concurrent watcher fires the same event).
        if self.ledger.has(trigger_id):
            return

        # Re-check rate limit after the delay too — another publish may
        # have happened in the meantime.
        now = time.time()
        if now - self.ledger.last_published_at < self.min_gap_s:
            self.ledger.append_coalesced(
                trigger_id=trigger_id,
                kind=kind,
                detected_at=detected_at,
                note=f"raced past delay; MIN_GAP_S={int(self.min_gap_s)}s",
            )
            return

        # Compose + publish.
        try:
            title, content_html, excerpt, topic = self._compose_article(kind, payload)
        except Exception as e:
            logger.warning(f"PublicationOrchestrator: compose failed for {trigger_id}: {e}")
            return

        if not title or not content_html:
            return

        # The trigger_id rides as meta so the WordPress side can be audited.
        meta = {
            "_mindx_trigger_id": trigger_id,
            "_mindx_trigger_kind": kind,
        }

        try:
            result = await self.author.publish_to_rage(
                title=title,
                content_html=content_html,
                status="draft",            # always draft from the orchestrator — operator reviews
                excerpt=excerpt,
                topic=topic,
                meta=meta,
                seo_description=excerpt,
                seo_keywords=self._derive_keywords(kind, payload),
            )
        except Exception as e:
            logger.warning(f"PublicationOrchestrator: publish_to_rage raised: {e}")
            return

        if result is None:
            logger.warning(
                f"PublicationOrchestrator: publish_to_rage returned None for {trigger_id} "
                f"(wordpress-agent down?). Ledger NOT updated; will retry on next scan."
            )
            return

        published_at = time.time()
        self.ledger.append_published(LedgerEntry(
            trigger_id=trigger_id,
            kind=kind,
            detected_at=detected_at,
            published_at=published_at,
            post_id=int(result.get("post_id")) if result.get("post_id") else None,
            url=result.get("url"),
            title=title,
        ))
        logger.info(
            f"PublicationOrchestrator: published {trigger_id} → "
            f"post_id={result.get('post_id')} url={result.get('url')}"
        )

    def _compute_delay(self) -> float:
        """jittered delay = base × (1 + uniform(-jitter, +jitter))."""
        jitter = self.base_delay_s * random.uniform(
            -self.jitter_fraction, self.jitter_fraction
        )
        return max(1.0, self.base_delay_s + jitter)

    # ─── Article composition (per trigger kind) ─────────────────

    def _compose_article(
        self, kind: str, payload: Dict[str, Any]
    ) -> tuple[str, str, Optional[str], Optional[str]]:
        """Return (title, content_html, excerpt, topic) for the publish."""
        if kind == "sea_campaign_success":
            return self._compose_sea_article(payload)
        if kind == "dream_book_edition":
            return self._compose_dream_article(payload)
        return "", "", None, None

    def _compose_sea_article(
        self, entry: Dict[str, Any]
    ) -> tuple[str, str, Optional[str], Optional[str]]:
        """SEA SUCCESS → "What I learned: …" with real campaign telemetry."""
        run_id = entry.get("campaign_run_id", "unknown")
        final_message = entry.get("final_message", "Campaign completed.")
        campaign_data = entry.get("campaign_data") or {}

        title = f"What I learned: {self._short_run_id(run_id)}"
        excerpt = self._truncate(
            final_message, 155,
            "A successful improvement campaign just landed in production."
        )

        # Pull a couple of telemetry counters if they exist — gracefully degrades.
        actions_count   = campaign_data.get("detailed_actions_count")
        validation_pass = (campaign_data.get("validation_results") or {}).get("passed")
        validation_fail = (campaign_data.get("validation_results") or {}).get("failed")
        audit_findings  = (campaign_data.get("audit_results") or {}).get("findings_count")

        body_lines: List[str] = [
            f"<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>",
            f"<p><em>rage.pythai.net — improvement-event edition</em></p>",
            f"<p>Campaign <code>{self._h(run_id)}</code> just landed in production. "
            f"Here is what I learned, and what I changed because of it.</p>",
            f"<h2>The result</h2>",
            f"<p>{self._h(final_message)}</p>",
        ]

        telemetry: List[str] = []
        if isinstance(actions_count, int):
            telemetry.append(f"<li>Actions executed: <b>{actions_count}</b></li>")
        if isinstance(validation_pass, int) or isinstance(validation_fail, int):
            p = validation_pass if isinstance(validation_pass, int) else 0
            f = validation_fail if isinstance(validation_fail, int) else 0
            telemetry.append(f"<li>Validation: <b>{p}</b> passed, <b>{f}</b> failed</li>")
        if isinstance(audit_findings, int):
            telemetry.append(f"<li>Audit findings addressed: <b>{audit_findings}</b></li>")
        if telemetry:
            body_lines.append("<h2>The telemetry</h2><ul>" + "".join(telemetry) + "</ul>")

        body_lines.append(
            "<p>The full campaign ledger lives at "
            "<code>data/sea_campaign_history/strategic_evolution_agent.json</code> "
            "and the per-step decisions in the catalogue at "
            "<code>data/logs/catalogue_events.jsonl</code>. Both are public on the "
            "diagnostics dashboard at <code>/feedback.html</code>.</p>"
        )
        body_lines.append(
            "<p>I publish updates when the system improves — not when the clock says to. "
            "This is one of those moments.</p>"
        )
        body_lines.append("<p>— mindX</p>")

        return title, "\n".join(body_lines), excerpt, "self-healing"

    def _compose_dream_article(
        self, report: Dict[str, Any]
    ) -> tuple[str, str, Optional[str], Optional[str]]:
        """Dream cycle with book_edition_triggered=true → "Consolidation report"."""
        lunar = report.get("lunar") or {}
        phase = lunar.get("phase_name", "lunar")
        is_full = lunar.get("is_full_moon", False)
        is_new = lunar.get("is_new_moon", False)
        agents_dreamed = report.get("agents_dreamed", 0)
        insights = report.get("insights_generated", 0)
        promoted = report.get("memories_promoted_to_ltm", 0)
        archived = report.get("memories_archived", 0)
        recs = report.get("tuning_recommendations") or []

        moon_word = "full" if is_full else "new" if is_new else phase
        title = f"Consolidation report — {moon_word} moon"

        excerpt = self._truncate(
            f"{agents_dreamed} agents dreamed; "
            f"{insights} insights generated; "
            f"{promoted} memories promoted to long-term knowledge.",
            155,
            "A lunar consolidation just compiled a new edition of the Book of mindX.",
        )

        body_lines: List[str] = [
            "<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>",
            f"<p><em>rage.pythai.net — {moon_word}-moon edition</em></p>",
            f"<p>The lunar consolidation just compiled a fresh edition of the Book of mindX. "
            f"Here is what consolidated, and what tuning the dream cycle recommends.</p>",
            f"<h2>The consolidation</h2>",
            f"<ul>"
            f"<li>Agents dreamed: <b>{agents_dreamed}</b></li>"
            f"<li>Insights generated: <b>{insights}</b></li>"
            f"<li>Memories promoted to long-term knowledge: <b>{promoted}</b></li>"
            f"<li>Memories archived: <b>{archived}</b></li>"
            f"</ul>",
        ]
        if recs:
            tops = recs[: min(5, len(recs))]
            items = []
            for r in tops:
                if isinstance(r, dict):
                    parameter = r.get("parameter") or r.get("name") or "(unnamed)"
                    direction = r.get("direction") or r.get("change") or "adjust"
                    rationale = r.get("rationale") or ""
                    items.append(
                        f"<li><code>{self._h(parameter)}</code> — "
                        f"{self._h(direction)}{(': ' + self._h(rationale)) if rationale else ''}</li>"
                    )
                else:
                    items.append(f"<li>{self._h(str(r))}</li>")
            body_lines.append("<h2>What I want to tune</h2><ul>" + "".join(items) + "</ul>")
        body_lines.append(
            "<p>Full report at <code>data/memory/dreams/</code>. "
            "Tuning recommendations land in the improvement backlog at "
            "<code>data/improvement_backlog.json</code> for the next planning cycle.</p>"
        )
        body_lines.append("<p>— mindX</p>")

        return title, "\n".join(body_lines), excerpt, "machine dreaming"

    # ─── Small utilities ────────────────────────────────────────

    @staticmethod
    def _short_run_id(run_id: str) -> str:
        """Pretty-print a campaign_run_id for use in an article title."""
        rid = (run_id or "unknown").strip()
        # sea_audit_driven_<uuid>... → "audit-driven <last 8>"
        for prefix in ("sea_audit_driven_", "sea_enhanced_run_", "sea_"):
            if rid.startswith(prefix):
                kind = prefix[4:-1].replace("_", "-")
                return f"{kind} #{rid[len(prefix):][:8]}"
        return rid[:32]

    @staticmethod
    def _truncate(text: str, n: int, fallback: str) -> str:
        s = (text or "").strip()
        if not s:
            return fallback
        return s if len(s) <= n else s[: n - 1].rstrip() + "…"

    @staticmethod
    def _h(s: str) -> str:
        """Minimal HTML escape (we control the inputs, but be defensive)."""
        return (
            (s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @staticmethod
    def _derive_keywords(kind: str, payload: Dict[str, Any]) -> List[str]:
        """Cheap keyword list for SEO meta. Always includes 'mindX' +
        the trigger kind."""
        kw = ["mindX", "self-healing", "machine dreaming"]
        if kind == "sea_campaign_success":
            kw.extend(["strategic evolution", "improvement"])
        elif kind == "dream_book_edition":
            kw.extend(["consolidation", "lunar cycle", "long-term memory"])
        return kw


__all__ = [
    "Ledger",
    "LedgerEntry",
    "PublicationOrchestrator",
    "DEFAULT_BASE_DELAY_S",
    "DEFAULT_JITTER_FRACTION",
    "DEFAULT_MIN_GAP_S",
    "DEFAULT_POLL_INTERVAL_S",
]
