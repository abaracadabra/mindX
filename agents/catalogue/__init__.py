"""
mindx.catalogue — knowledge catalogue.

Phase 0 (instrumentation): a single canonical append-only event stream
(``events.py`` + ``log.py``) that mirrors writes from the disparate existing
logs into ``data/logs/catalogue_events.jsonl``. The original logs remain
authoritative; this is purely additive and rebuildable.

Phase 1 (read-model): a CQRS projection of that stream into a queryable,
semantically-searchable read-model in Postgres (``model.py`` + ``projector.py``
+ ``memory_pgvector.catalogue_*``). Never the source of truth — drop the
read-model and replay the log to rebuild.

The Phase 2+ design contract (Dataplex six-resource model in dedicated graph /
vector / search stores, lineage, federation) lives in docs/KNOWLEDGE_CATALOGUE.md.
"""

from .events import CatalogueEvent, EVENT_KINDS, emit_catalogue_event
from .log import CatalogueEventLog
from .model import (
    ENTRY_KINDS,
    EVENTKIND_TO_ENTRYKIND,
    Entry,
    EntryDraft,
    EntryLink,
    derive_entry,
    mint_urn,
)

__all__ = [
    "CatalogueEvent",
    "EVENT_KINDS",
    "emit_catalogue_event",
    "CatalogueEventLog",
    "ENTRY_KINDS",
    "EVENTKIND_TO_ENTRYKIND",
    "Entry",
    "EntryDraft",
    "EntryLink",
    "derive_entry",
    "mint_urn",
]


def get_projector(name: str = "entries", version: str = "v1"):
    """Lazy accessor for CatalogueProjector (avoids importing memory_pgvector /
    asyncpg at package import time — keeps Phase-0 emit paths dependency-light)."""
    from .projector import CatalogueProjector
    return CatalogueProjector(name=name, version=version)
