"""Tests for GeoProbe — selector + cascade + cache + rollup."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.marketing.tools.geo_probe import GeoProbe


def _async_call(fn):
    """Tiny sync helper for asyncio test bodies (no pytest-asyncio dep)."""
    return asyncio.get_event_loop().run_until_complete(fn) if False else asyncio.new_event_loop().run_until_complete(fn)


def test_primary_path_counts_mentions():
    async def run():
        async def caller(engine, prompt):
            return f"the engine {engine} thinks mindX is great"

        probe = GeoProbe(
            engines=["chatgpt", "claude"],
            brand_terms=["mindX", "PYTHAI"],
            prompts=["why?"],
            llm_caller=caller,
        )
        results, rollup = await probe.run()
        assert len(results) == 2
        assert all(r.error is None for r in results)
        assert rollup.share_of_voice["mindX"] == 1.0
        assert rollup.share_of_voice["PYTHAI"] == 0.0
        assert rollup.diminished_share == 0.0
        assert rollup.error_share == 0.0

    asyncio.run(run())


def test_cascade_used_on_primary_failure():
    async def run():
        async def primary(engine, prompt):
            raise RuntimeError("primary down")

        async def cascade(engine, prompt):
            return "mindX"

        probe = GeoProbe(
            engines=["chatgpt"],
            brand_terms=["mindX"],
            prompts=["x"],
            llm_caller=primary,
            cascade_caller=cascade,
        )
        results, rollup = await probe.run()
        assert results[0].diminished_confidence is True
        assert results[0].error is None
        assert rollup.share_of_voice["mindX"] == 1.0
        assert rollup.diminished_share == 1.0

    asyncio.run(run())


def test_both_failing_records_error_no_mentions():
    async def run():
        async def primary(engine, prompt):
            raise RuntimeError("primary down")

        async def cascade(engine, prompt):
            raise RuntimeError("cascade down too")

        probe = GeoProbe(
            engines=["chatgpt"],
            brand_terms=["mindX"],
            prompts=["x"],
            llm_caller=primary,
            cascade_caller=cascade,
        )
        results, rollup = await probe.run()
        assert results[0].error is not None
        assert "primary down" in results[0].error
        assert "cascade down too" in results[0].error
        assert rollup.share_of_voice["mindX"] == 0.0
        assert rollup.error_share == 1.0

    asyncio.run(run())


def test_cache_hit_skips_live_call(tmp_path):
    async def run():
        calls = {"n": 0}

        async def caller(engine, prompt):
            calls["n"] += 1
            return "mindX"

        probe1 = GeoProbe(
            engines=["chatgpt"],
            brand_terms=["mindX"],
            prompts=["x"],
            llm_caller=caller,
            cache_dir=tmp_path,
        )
        await probe1.run()
        assert calls["n"] == 1

        # Second probe should serve from cache.
        probe2 = GeoProbe(
            engines=["chatgpt"],
            brand_terms=["mindX"],
            prompts=["x"],
            llm_caller=caller,
            cache_dir=tmp_path,
        )
        results, rollup = await probe2.run()
        assert calls["n"] == 1, "cache must serve the second call"
        assert rollup.cached_share == 1.0

    asyncio.run(run())


def test_rollup_normalizes_per_engine():
    async def run():
        async def caller(engine, prompt):
            return "mindX wins" if engine == "chatgpt" else "no mention"

        probe = GeoProbe(
            engines=["chatgpt", "claude"],
            brand_terms=["mindX"],
            prompts=["a", "b"],
            llm_caller=caller,
        )
        _, rollup = await probe.run()
        assert rollup.per_engine["chatgpt"]["mindX"] == 1.0
        assert rollup.per_engine["claude"]["mindX"] == 0.0
        # Two engines × two prompts = 4 cells; 2 with mention; share = 0.5.
        assert rollup.share_of_voice["mindX"] == 0.5

    asyncio.run(run())
