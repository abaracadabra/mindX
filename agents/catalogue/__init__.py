"""
mindx.catalogue — Phase 0 instrumentation.

A single canonical append-only event stream that mirrors writes from the
disparate existing logs (process_trace.jsonl, godel_choices.jsonl,
boardroom_sessions.jsonl, STM tree). The original logs remain authoritative;
this module is purely additive, so the catalogue can be deleted and rebuilt
from the source logs without losing memory.

This is Phase 0: typed sink + emit helper. No projectors. The Phase 1+ design
contract (Dataplex six-resource model, hybrid retrieval, federation) lives in
docs/KNOWLEDGE_CATALOGUE.md.

Plan: /home/hacker/.claude/plans/purring-humming-stonebraker.md
"""

from .events import CatalogueEvent, EVENT_KINDS, emit_catalogue_event
from .log import CatalogueEventLog

__all__ = ["CatalogueEvent", "EVENT_KINDS", "emit_catalogue_event", "CatalogueEventLog"]
