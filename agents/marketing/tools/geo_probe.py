"""
geo_probe — share-of-voice probe across LLM engines.

Per `feedback_no_model_pinning.md` (user-locked 2026-05-04), every LLM call
goes through the self.aware selector + cascades to local Ollama on failure.
This module deliberately accepts an `llm_caller` callable so tests can mock
without import-time dependencies on the live llm_factory; production paths
inject the real `blueprint_agent._resolve_active_handler` at the call site.

Per-(engine, prompt) results are cached for `cache_seconds` (default 24h)
to avoid duplicate spend; the rollup is the proportion of (engine, prompt)
pairs that mention each `brand_term`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional, Tuple


@dataclass
class GeoProbeResult:
    engine: str
    prompt: str
    response: str
    mentions: Dict[str, int]              # brand_term → mention count
    diminished_confidence: bool = False    # true when fell through to Ollama cascade
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class GeoProbeRollup:
    engines: List[str]
    brand_terms: List[str]
    prompts_count: int
    share_of_voice: Dict[str, float]      # brand_term → fraction (0..1) of (engine,prompt) cells mentioning it
    per_engine: Dict[str, Dict[str, float]]   # engine → {brand_term: fraction}
    diminished_share: float               # fraction of cells that fell through cascade
    error_share: float
    cached_share: float
    timestamp: float = field(default_factory=time.time)


# `llm_caller` signature contract
LLMCaller = Callable[[str, str], Awaitable[str]]
#   args:  (engine_name, prompt) — engine_name lets the caller route
#   raises: anything; geo_probe wraps and records as error


def _count_mentions(text: str, brand_terms: List[str]) -> Dict[str, int]:
    lowered = text.lower()
    return {term: lowered.count(term.lower()) for term in brand_terms}


def _cache_key(engine: str, prompt: str) -> str:
    return hashlib.sha256(f"{engine}|{prompt}".encode("utf-8")).hexdigest()


class GeoProbe:
    def __init__(
        self,
        engines: List[str],
        brand_terms: List[str],
        prompts: List[str],
        *,
        llm_caller: LLMCaller,
        cascade_caller: Optional[LLMCaller] = None,
        cache_dir: Optional[Path] = None,
        cache_seconds: int = 86400,
        weekly_budget_usd: float = 20.0,
    ) -> None:
        self.engines = list(engines)
        self.brand_terms = list(brand_terms)
        self.prompts = list(prompts)
        self.llm_caller = llm_caller
        self.cascade_caller = cascade_caller
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.cache_seconds = max(60, int(cache_seconds))
        self.weekly_budget_usd = float(weekly_budget_usd)
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._budget_spent_usd = 0.0
        self._cached_count = 0

    def _read_cache(self, engine: str, prompt: str) -> Optional[GeoProbeResult]:
        if self.cache_dir is None:
            return None
        path = self.cache_dir / f"{_cache_key(engine, prompt)}.json"
        if not path.exists():
            return None
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
            ts = float(blob.get("timestamp", 0))
            if time.time() - ts > self.cache_seconds:
                return None
            return GeoProbeResult(
                engine=blob["engine"],
                prompt=blob["prompt"],
                response=blob["response"],
                mentions=dict(blob.get("mentions") or {}),
                diminished_confidence=bool(blob.get("diminished_confidence", False)),
                error=blob.get("error"),
                timestamp=ts,
            )
        except Exception:
            return None

    def _write_cache(self, result: GeoProbeResult) -> None:
        if self.cache_dir is None:
            return
        path = self.cache_dir / f"{_cache_key(result.engine, result.prompt)}.json"
        try:
            path.write_text(
                json.dumps(
                    {
                        "engine": result.engine,
                        "prompt": result.prompt,
                        "response": result.response,
                        "mentions": result.mentions,
                        "diminished_confidence": result.diminished_confidence,
                        "error": result.error,
                        "timestamp": result.timestamp,
                    }
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    async def _probe_one(self, engine: str, prompt: str) -> GeoProbeResult:
        cached = self._read_cache(engine, prompt)
        if cached is not None:
            self._cached_count += 1
            return cached
        # Live call. Selector first, cascade fallback.
        try:
            text = await self.llm_caller(engine, prompt)
            return GeoProbeResult(
                engine=engine,
                prompt=prompt,
                response=text or "",
                mentions=_count_mentions(text or "", self.brand_terms),
                diminished_confidence=False,
            )
        except Exception as exc:
            primary_err = repr(exc)
            if self.cascade_caller is None:
                return GeoProbeResult(
                    engine=engine,
                    prompt=prompt,
                    response="",
                    mentions={t: 0 for t in self.brand_terms},
                    error=primary_err,
                )
            try:
                text = await self.cascade_caller(engine, prompt)
                return GeoProbeResult(
                    engine=engine,
                    prompt=prompt,
                    response=text or "",
                    mentions=_count_mentions(text or "", self.brand_terms),
                    diminished_confidence=True,
                )
            except Exception as exc2:
                return GeoProbeResult(
                    engine=engine,
                    prompt=prompt,
                    response="",
                    mentions={t: 0 for t in self.brand_terms},
                    diminished_confidence=True,
                    error=f"primary={primary_err}; cascade={exc2!r}",
                )

    async def run(self) -> Tuple[List[GeoProbeResult], GeoProbeRollup]:
        """Run the full grid. Returns (per-cell results, rollup)."""
        cells: List[Tuple[str, str]] = [(e, p) for e in self.engines for p in self.prompts]
        results: List[GeoProbeResult] = await asyncio.gather(
            *(self._probe_one(e, p) for e, p in cells)
        )
        for r in results:
            if not (self._read_cache(r.engine, r.prompt) is r):
                self._write_cache(r)
        rollup = self._rollup(results)
        return results, rollup

    def _rollup(self, results: List[GeoProbeResult]) -> GeoProbeRollup:
        total = max(1, len(results))
        diminished = sum(1 for r in results if r.diminished_confidence)
        errored = sum(1 for r in results if r.error)
        share: Dict[str, float] = {t: 0.0 for t in self.brand_terms}
        per_engine: Dict[str, Dict[str, float]] = {e: {t: 0.0 for t in self.brand_terms} for e in self.engines}
        per_engine_counts: Dict[str, int] = {e: 0 for e in self.engines}
        for r in results:
            per_engine_counts[r.engine] = per_engine_counts.get(r.engine, 0) + 1
            for term, n in r.mentions.items():
                if n > 0:
                    share[term] = share.get(term, 0.0) + 1.0
                    per_engine[r.engine][term] = per_engine[r.engine].get(term, 0.0) + 1.0
        share = {t: v / total for t, v in share.items()}
        for e in per_engine:
            denom = max(1, per_engine_counts.get(e, 0))
            per_engine[e] = {t: v / denom for t, v in per_engine[e].items()}
        return GeoProbeRollup(
            engines=self.engines,
            brand_terms=self.brand_terms,
            prompts_count=len(self.prompts),
            share_of_voice=share,
            per_engine=per_engine,
            diminished_share=diminished / total,
            error_share=errored / total,
            cached_share=self._cached_count / total,
        )


__all__ = ["GeoProbe", "GeoProbeResult", "GeoProbeRollup", "LLMCaller"]
