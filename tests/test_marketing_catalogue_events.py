"""Tests for the 5 new marketing.* EventKind literals."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.catalogue.events import (
    EVENT_KINDS,
    CatalogueEvent,
    emit_catalogue_event,
)
from agents.catalogue.log import CatalogueEventLog


MARKETING_KINDS = (
    "marketing.campaign_proposed",
    "marketing.campaign_executed",
    "marketing.geo_probe",
    "marketing.tessera_attested",
    "marketing.boardroom_routed",
)


def test_marketing_kinds_present_in_event_kinds_tuple():
    for kind in MARKETING_KINDS:
        assert kind in EVENT_KINDS, f"{kind!r} missing from EVENT_KINDS"


def test_catalogue_event_accepts_marketing_kinds():
    for kind in MARKETING_KINDS:
        evt = CatalogueEvent(
            kind=kind,
            actor="marketinga",
            payload={"campaign_id": "abc"},
            source_log="marketing.test",
        )
        assert evt.kind == kind
        # Roundtrip JSON must preserve the kind verbatim.
        decoded = json.loads(evt.model_dump_json())
        assert decoded["kind"] == kind


def test_emit_catalogue_event_roundtrip(tmp_path, monkeypatch):
    log_path = tmp_path / "catalogue_events.jsonl"
    custom_log = CatalogueEventLog(log_path)

    monkeypatch.setattr(
        "agents.catalogue.events._get_log",
        lambda: custom_log,
    )
    monkeypatch.setattr(
        "agents.catalogue.events._emit_disabled",
        False,
    )

    async def emit_one():
        return await emit_catalogue_event(
            kind="marketing.campaign_proposed",
            actor="marketinga",
            payload={"campaign_id": "evt-test", "pillar": "cognition_you_own"},
            source_log="marketing.orchestrator",
        )

    event_id = asyncio.run(emit_one())
    assert event_id is not None and len(event_id) > 0

    text = log_path.read_text(encoding="utf-8")
    assert "marketing.campaign_proposed" in text
    parsed = json.loads(text.splitlines()[-1])
    assert parsed["kind"] == "marketing.campaign_proposed"
    assert parsed["payload"]["pillar"] == "cognition_you_own"


def test_unknown_marketing_kind_is_dropped(tmp_path, monkeypatch):
    log_path = tmp_path / "catalogue_events.jsonl"
    custom_log = CatalogueEventLog(log_path)

    monkeypatch.setattr("agents.catalogue.events._get_log", lambda: custom_log)
    monkeypatch.setattr("agents.catalogue.events._emit_disabled", False)

    async def emit_unknown():
        return await emit_catalogue_event(
            kind="marketing.nonsense",
            actor="marketinga",
            payload={},
            source_log="marketing.test",
        )

    assert asyncio.run(emit_unknown()) is None
    assert not log_path.exists() or log_path.stat().st_size == 0
