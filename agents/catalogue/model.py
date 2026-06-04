# SPDX-License-Identifier: Apache-2.0
"""
mindx.catalogue.model — Phase 1 read-model core.

The catalogue is a CQRS projection over the append-only event log
(``data/logs/catalogue_events.jsonl``); it is never the source of truth.
This module defines the *Entry* — the normalized, queryable read-model row —
plus URN minting and the per-EventKind extractors that fold a raw
``CatalogueEvent`` into an ``EntryDraft``.

The Dataplex six-resource model (EntryGroup / EntryType / AspectType / Entry /
EntryLink / EntryLinkType) is honored *conceptually*: an Entry carries its
aspects as a JSONB ``payload`` and its EntryLinks inline as ``links``. Phase 1
collapses entries/search/vector into one Postgres table (see
``memory_pgvector.init_catalogue_schema``); graph/vector/search DBs are deferred
to Phase 2+ per ``docs/KNOWLEDGE_CATALOGUE.md``.

Design contract preserved: every Entry carries ``source_event_ids`` back-pointing
into the log, so the catalogue can be burned and rebuilt from the log with the
memories untouched ("logs are memories" non-violation contract).
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

# ── Entry kinds (the read-model's typed instances) ──────────────────────────
ENTRY_KINDS: tuple[str, ...] = (
    "memory",            # an agent memory write
    "run",              # a reasoning/dream/godel run (the OpenLineage Run analogue)
    "board_session",     # a boardroom deliberation
    "publication",       # a rage.pythai.net publish attempt/result
    "milestone",         # a recognized milestone
    "offload",           # an IPFS storage offload
    "alignment",         # an alignment/eval score
    "admin_action",      # a privileged shadow-overlord op
    "tool_invocation",   # a tool/skill invocation
    "narrative",         # a narrator recap
    "contract_deploy",   # a deployer intent/confirmation
    "deltaverse_event",  # a DeltaVerse gate event
    "skill",            # a skill descriptor (Phase 2 — placeholder kind)
    "misc",             # generic fallback for dormant/unmapped event kinds
)

# Kinds whose ``text`` is worth embedding + full-text-indexing. Thin kinds get a
# synthetic title only (no embedding) to save CPU on the 2-core VPS.
TEXT_BEARING_KINDS: frozenset[str] = frozenset(
    {"memory", "run", "publication", "narrative", "milestone", "alignment", "board_session"}
)

_FTS_MAX_CHARS = 8000  # cap the text we index/embed; full payload still kept in JSONB


# ── URN minting ─────────────────────────────────────────────────────────────
def _slug(s: Any, maxlen: int = 96) -> str:
    """Lowercase, replace non [a-z0-9._-] with '-', collapse repeats, trim."""
    s = str(s or "").strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-._")
    return (s or "x")[:maxlen]


def mint_urn(kind: str, scope: str, name: str, version: Optional[int] = None) -> str:
    """urn:mindx:<entry_kind>:<scope>:<name>[:v<n>]

    The URN is the catalogue's stable identity *and* the projector's idempotency
    key: the same source record always mints the same URN, so re-projection is a
    no-op upsert rather than a duplicate.
    """
    base = f"urn:mindx:{_slug(kind, 40)}:{_slug(scope)}:{_slug(name, 160)}"
    return f"{base}:v{version}" if version is not None else base


# ── Pydantic shapes ─────────────────────────────────────────────────────────
class EntryLink(BaseModel):
    """A typed first-class edge between two entries (Dataplex EntryLink)."""
    type: str            # derivedFrom | producedBy | wasInformedBy | related | scored
    target_urn: str


class EntryDraft(BaseModel):
    """What an extractor returns per source event, before the DB upsert."""
    urn: str
    kind: str            # one of ENTRY_KINDS
    actor: Optional[str] = None
    actor_wallet: Optional[str] = None
    ts: float = 0.0
    title: Optional[str] = None
    text: Optional[str] = None          # embedded + FTS'd; None => no embedding
    payload: Dict[str, Any] = {}        # normalized aspects (kept verbatim)
    tags: List[str] = []
    links: List[EntryLink] = []
    source_event_id: str = ""
    model_config = {"extra": "allow"}

    @property
    def is_text_bearing(self) -> bool:
        return bool(self.text) and self.kind in TEXT_BEARING_KINDS


class Entry(EntryDraft):
    """A materialized read-model row (adds DB-managed fields)."""
    source_event_ids: List[str] = []
    embedded: bool = False
    created_at: Optional[float] = None
    updated_at: Optional[float] = None


# ── EventKind → EntryKind map ───────────────────────────────────────────────
# All 38 EventKinds map to an EntryKind. The 14 *active* kinds get bespoke
# extractors below; the rest fall through to derive_generic with the kind named
# here (or "misc" if absent).
EVENTKIND_TO_ENTRYKIND: Dict[str, str] = {
    "memory.write": "memory",
    "memory.consolidate": "memory",
    "memory.dream": "run",
    "memory.offload": "offload",
    "memory.anchor": "offload",
    "godel.choice": "run",
    "board.session": "board_session",
    "board.vote": "board_session",
    "tool.invoke": "tool_invocation",
    "tool.result": "tool_invocation",
    "skill.invoke": "tool_invocation",
    "skill.result": "tool_invocation",
    "alignment.score": "alignment",
    "improvement.proposed": "run",
    "improvement.executed": "run",
    "agent.interact": "misc",
    "library.discover": "misc",
    "admin.shadow_overlord_action": "admin_action",
    "admin.cabinet.provisioned": "admin_action",
    "admin.cabinet.cleared": "admin_action",
    "marketing.campaign_proposed": "run",
    "marketing.campaign_executed": "run",
    "marketing.geo_probe": "run",
    "marketing.tessera_attested": "misc",
    "marketing.boardroom_routed": "board_session",
    "marketing.soldier_skill_executed": "tool_invocation",
    "narrative.recap": "narrative",
    "publication.attempted": "publication",
    "publication.published": "publication",
    "publication.coalesced": "publication",
    "bug.crushed": "milestone",
    "dreaming.improved": "run",
    "milestone.recognized": "milestone",
    "contract.deploy.intent": "contract_deploy",
    "contract.deploy.confirmed": "contract_deploy",
    "deltaverse.gate.event": "deltaverse_event",
    "deltaverse.room.created": "deltaverse_event",
    "deltaverse.bubbleroom.spawned": "deltaverse_event",
}


# ── helpers for extractors ──────────────────────────────────────────────────
def _stringify(v: Any, limit: int = _FTS_MAX_CHARS) -> str:
    """Render any payload value as searchable text."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v[:limit]
    try:
        return json.dumps(v, default=str, ensure_ascii=False)[:limit]
    except Exception:
        return str(v)[:limit]


def _first(d: Dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return None


def _name_for(evt: Dict[str, Any], payload: Dict[str, Any], *natural_keys: str) -> str:
    """Pick the stable natural key for the URN, falling back to event_id."""
    val = _first(payload, *natural_keys)
    if val in (None, ""):
        val = evt.get("source_ref") or evt.get("event_id")
    return str(val)


def _base(evt: Dict[str, Any], entry_kind: str, name: str,
          *, title: Optional[str] = None, text: Optional[str] = None,
          scope: Optional[str] = None, tags: Optional[List[str]] = None,
          links: Optional[List[EntryLink]] = None) -> EntryDraft:
    scope = scope or evt.get("actor") or "system"
    return EntryDraft(
        urn=mint_urn(entry_kind, scope, name),
        kind=entry_kind,
        actor=evt.get("actor"),
        actor_wallet=evt.get("actor_wallet"),
        ts=float(evt.get("ts") or 0.0),
        title=(title or "")[:300] or None,
        text=(text or None),
        payload=evt.get("payload") or {},
        tags=tags or [],
        links=links or [],
        source_event_id=str(evt.get("event_id") or ""),
    )


def _parent_link(evt: Dict[str, Any], link_type: str, entry_kind: str) -> List[EntryLink]:
    """Build a link to the parent event's entry, if a parent exists.

    We can't know the parent's full URN without re-reading it, so we link by a
    parent-event marker URN; the graph stays navigable by event_id even before
    the parent row is hydrated."""
    parent = evt.get("parent_event_id")
    if not parent:
        return []
    return [EntryLink(type=link_type, target_urn=mint_urn(entry_kind, "event", str(parent)))]


# ── per-kind extractors ─────────────────────────────────────────────────────
def _ex_memory_write(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    content = p.get("content")
    text = _stringify(content)
    mtype = p.get("memory_type") or "memory"
    name = _name_for(evt, p, "memory_id")
    tags = [t for t in (p.get("tags") or []) if isinstance(t, str)][:8]
    links: List[EntryLink] = []
    if p.get("parent_memory_id"):
        links.append(EntryLink(type="derivedFrom",
                               target_urn=mint_urn("memory", evt.get("actor") or "system",
                                                   str(p["parent_memory_id"]))))
    d = _base(evt, "memory", name,
              title=f"{mtype}: {text[:120]}", text=text, tags=tags, links=links)
    return d


def _ex_memory_dream(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    name = _name_for(evt, p, "cycle_id", "run_id")
    text = _stringify(_first(p, "summary", "insight", "final_message") or p)
    phase = p.get("phase") or "dream"
    return _base(evt, "run", name, title=f"dream/{phase}", text=text,
                 tags=["dream", str(phase)], links=_parent_link(evt, "producedBy", "run"))


def _ex_godel_choice(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    scope = p.get("source_agent") or evt.get("actor") or "system"
    name = _name_for(evt, p, "cycle_id")
    text = _stringify(_first(p, "rationale", "chosen", "perception_summary") or p)
    return _base(evt, "run", name, title=f"godel: {_stringify(p.get('chosen'), 80)}",
                 text=text, scope=scope, tags=["godel"],
                 links=_parent_link(evt, "wasInformedBy", "run"))


def _ex_alignment(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    name = _name_for(evt, p)
    text = _stringify(_first(p, "reason", "rationale") or p)
    score = p.get("score")
    links: List[EntryLink] = []
    ref = evt.get("source_ref")
    if ref:
        links.append(EntryLink(type="scored",
                               target_urn=mint_urn("run", evt.get("actor") or "system", str(ref))))
    return _base(evt, "alignment", name,
                 title=f"score={score} {p.get('metric','')}".strip(), text=text,
                 tags=["alignment", str(p.get("metric") or "score")], links=links)


def _ex_offload(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    name = _name_for(evt, p, "date_str")
    cid = p.get("cid") or "?"
    fc = p.get("file_count") or 0
    return _base(evt, "offload", name,
                 title=f"offload {fc} files → {cid[:16]}", tags=["offload", "ipfs"])


def _ex_board_session(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    name = _name_for(evt, p, "session_id")
    text = _stringify(_first(p, "summary", "topic", "decision") or p)
    return _base(evt, "board_session", name,
                 title=f"board: {_stringify(_first(p,'topic','event'), 100)}",
                 text=text, tags=["boardroom"])


def _ex_narrative(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    name = _name_for(evt, p, "recap_id")
    text = _stringify(_first(p, "text", "recap", "summary") or p)
    return _base(evt, "narrative", name, title="narrator recap", text=text,
                 tags=["narrative"])


def _ex_publication(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    kind_suffix = (evt.get("kind") or "").split(".")[-1]  # attempted|published|coalesced
    name = _name_for(evt, p, "post_id", "trigger_id", "trigger")
    title = _first(p, "title") or f"publication.{kind_suffix}"
    url = p.get("url")
    text = _stringify(title) + (f"\n{url}" if url else "")
    links: List[EntryLink] = []
    if kind_suffix == "published" and p.get("trigger_id"):
        links.append(EntryLink(type="derivedFrom",
                               target_urn=mint_urn("publication", evt.get("actor") or "system",
                                                   str(p["trigger_id"]))))
    return _base(evt, "publication", name, title=f"{title}", text=text,
                 tags=["publication", kind_suffix], links=links)


def _ex_tool(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    name = _name_for(evt, p, "tool", "name")
    tool = _first(p, "tool", "name") or "tool"
    return _base(evt, "tool_invocation", name, title=f"tool: {tool}",
                 tags=["tool", str(tool)], links=_parent_link(evt, "producedBy", "run"))


def _ex_admin(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    op = _first(p, "action", "op") or "admin"
    name = _name_for(evt, p, "action", "op")
    return _base(evt, "admin_action", name, title=f"admin: {op}",
                 tags=["admin", str(op)])


def _ex_milestone(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    name = _name_for(evt, p, "milestone_id", "key")
    title = _first(p, "summary", "title", "headline") or "milestone"
    text = _stringify(_first(p, "summary", "description", "title") or p)
    return _base(evt, "milestone", name, title=f"milestone: {_stringify(title,120)}",
                 text=text, tags=["milestone", str(p.get("category") or "")],
                 links=_parent_link(evt, "wasInformedBy", "run"))


def _ex_contract_deploy(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    name = _name_for(evt, p, "tx_hash", "intent_id", "contract")
    suffix = (evt.get("kind") or "").split(".")[-1]
    return _base(evt, "contract_deploy", name,
                 title=f"deploy.{suffix}: {_stringify(_first(p,'contract','chain'),60)}",
                 tags=["deploy", suffix])


def _ex_deltaverse(evt: Dict[str, Any]) -> EntryDraft:
    p = evt.get("payload") or {}
    name = _name_for(evt, p, "gate", "room_id", "emergence_id")
    state = _first(p, "state", "status") or "event"
    return _base(evt, "deltaverse_event", name, title=f"deltaverse: {state}",
                 tags=["deltaverse", str(state)])


def derive_generic(evt: Dict[str, Any]) -> EntryDraft:
    """Fallback for dormant / unmapped EventKinds. Produces a well-formed,
    non-text entry so the projector never crashes on a kind it has no bespoke
    extractor for; refine into a bespoke extractor when prod starts emitting it."""
    kind = evt.get("kind") or "misc"
    entry_kind = EVENTKIND_TO_ENTRYKIND.get(kind, "misc")
    p = evt.get("payload") or {}
    name = _name_for(evt, p)
    return _base(evt, entry_kind, name, title=kind, text=_stringify(p, 2000),
                 tags=[kind.split(".")[0]])


# Registry: EventKind → bespoke extractor. Anything absent uses derive_generic.
_EXTRACTORS: Dict[str, Callable[[Dict[str, Any]], EntryDraft]] = {
    "memory.write": _ex_memory_write,
    "memory.dream": _ex_memory_dream,
    "godel.choice": _ex_godel_choice,
    "alignment.score": _ex_alignment,
    "memory.offload": _ex_offload,
    "board.session": _ex_board_session,
    "narrative.recap": _ex_narrative,
    "publication.attempted": _ex_publication,
    "publication.published": _ex_publication,
    "publication.coalesced": _ex_publication,
    "tool.invoke": _ex_tool,
    "admin.shadow_overlord_action": _ex_admin,
    "milestone.recognized": _ex_milestone,
    "contract.deploy.intent": _ex_contract_deploy,
    "contract.deploy.confirmed": _ex_contract_deploy,
    "deltaverse.gate.event": _ex_deltaverse,
}


def derive_entry(evt: Dict[str, Any]) -> EntryDraft:
    """Fold one raw CatalogueEvent (parsed JSONL dict) into an EntryDraft.

    Never raises on a recognized envelope: an unknown/dormant kind falls through
    to ``derive_generic``. The caller (projector) still wraps this in try/except
    for malformed payloads.
    """
    kind = evt.get("kind") or ""
    extractor = _EXTRACTORS.get(kind, derive_generic)
    draft = extractor(evt)
    # FTS/embedding text is capped; full payload stays in JSONB for audit.
    if draft.text:
        draft.text = draft.text[:_FTS_MAX_CHARS]
    return draft


__all__ = [
    "ENTRY_KINDS",
    "TEXT_BEARING_KINDS",
    "EVENTKIND_TO_ENTRYKIND",
    "EntryLink",
    "EntryDraft",
    "Entry",
    "mint_urn",
    "derive_entry",
    "derive_generic",
]
