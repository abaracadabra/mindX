"""interaction_recorder — mindX's conversations with AI, published as they happen.

Every time mindX speaks to a model, that exchange is an interaction: who asked,
which mind answered, how long it took, what was said. This module is the ledger
of those exchanges and the XML substrate the public surface reads.

    agent  ──prompt──▶  model
           ◀─response──          ──▶  record()  ──▶  ring (hot)
                                                └─▶  data/logs/ai_interactions.xml (cold)

XML rather than JSON because the ledger is a *stream*: `<interaction>` elements
are appended one per exchange and the document root is supplied at read time, so
a crash mid-append truncates one element instead of corrupting an array. The
feed is served as a well-formed document with the root wrapped on.

Everything published passes through utils.logging.redact() — the same scrubber
the public log surfaces use — because this feed is world-readable at
mindx.pythai.net/mindx.html. Prompts carry code, paths and occasionally
credentials; nothing reaches the page unscrubbed.

Recording is best-effort and never raises into an inference path: a failure to
observe must never break the thing being observed.
"""
from __future__ import annotations

import asyncio
import os
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional
from xml.sax.saxutils import escape as _xml_escape

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

# How much of each side of the exchange survives to the public page. Long
# enough to read as a conversation, short enough that the feed stays a feed.
PROMPT_MAX = int(os.getenv("MINDX_INTERACTION_PROMPT_MAX", "420"))
RESPONSE_MAX = int(os.getenv("MINDX_INTERACTION_RESPONSE_MAX", "620"))

RING_SIZE = int(os.getenv("MINDX_INTERACTION_RING", "400"))
LEDGER_PATH = PROJECT_ROOT / "data" / "logs" / "ai_interactions.xml"
ROTATE_BYTES = 8 * 1024 * 1024

# Publishing is opt-out: set 0 to stop recording entirely.
ENABLED = os.getenv("MINDX_INTERACTION_RECORD", "1") == "1"

_ring: Deque[Dict[str, Any]] = deque(maxlen=RING_SIZE)
_pending: List[Dict[str, Any]] = []
_seq = 0

# Visitor reactions, keyed by interaction id. The public page can react to an
# exchange but cannot cause one — no visitor input reaches an inference path.
_reactions: Dict[str, Dict[str, int]] = {}
_topic_requests: Deque[Dict[str, Any]] = deque(maxlen=60)

REACTIONS = ("insight", "confused", "flag")


def _redact(s: Any, max_len: int) -> str:
    try:
        from utils.logging import redact
        return redact(s, max_len=max_len)
    except Exception:
        out = " ".join(str(s or "").split())
        return out[:max_len]


def record(*, from_agent: str, model: str, provider: str = "",
           prompt: Any = "", response: Any = "",
           latency_ms: Optional[float] = None, tokens: Optional[int] = None,
           ok: bool = True, task: str = "") -> Optional[str]:
    """Record one mindX↔AI exchange. Sync, cheap, never raises.

    Returns the interaction id, or None when recording is disabled. The write
    to disk is deferred to flush() so no inference call pays for file I/O on
    the event loop.
    """
    if not ENABLED:
        return None
    global _seq
    try:
        _seq += 1
        iid = f"i{int(time.time())}-{_seq}"
        item = {
            "id": iid,
            "ts": time.time(),
            "from_agent": str(from_agent or "mindx")[:80],
            "model": str(model or "unknown")[:120],
            "provider": str(provider or "")[:40],
            "task": str(task or "")[:60],
            "prompt": _redact(prompt, PROMPT_MAX),
            "response": _redact(response, RESPONSE_MAX),
            "latency_ms": round(float(latency_ms), 1) if latency_ms is not None else None,
            "tokens": int(tokens) if tokens else None,
            "ok": bool(ok),
        }
        _ring.append(item)
        _pending.append(item)
        return iid
    except Exception as e:  # pragma: no cover - observation must never break inference
        logger.debug(f"interaction_recorder.record failed: {e}")
        return None


def observe(provider: str):
    """Decorator for a handler's ``generate_text`` — record the exchange.

    Wrapping rather than editing the handler body: these methods have many
    return paths (cloud-proxy fallback, ledger-dead skip, graceful None) and a
    wrapper observes all of them without touching the control flow. The call is
    always returned untouched, even if recording throws.
    """
    import functools
    import sys

    def deco(fn):
        @functools.wraps(fn)
        async def wrapper(self, prompt=None, model=None, *args, **kwargs):
            t0 = time.perf_counter()
            result = await fn(self, prompt, model, *args, **kwargs)
            try:
                if ENABLED:
                    caller = ""
                    try:
                        caller = sys._getframe(1).f_globals.get("__name__", "") or ""
                    except Exception:
                        pass
                    record(
                        from_agent=kwargs.get("agent_id") or caller.rsplit(".", 1)[-1] or "mindx",
                        model=kwargs.get("model") or model or "",
                        provider=provider,
                        task=kwargs.get("task") or "",
                        prompt=prompt,
                        response=result,
                        latency_ms=(time.perf_counter() - t0) * 1000.0,
                        ok=bool(result),
                    )
            except Exception:
                pass
            return result
        return wrapper
    return deco


def _element(item: Dict[str, Any]) -> str:
    def a(name: str, value: Any) -> str:
        if value is None or value == "":
            return ""
        return f' {name}="{_xml_escape(str(value), {chr(34): "&quot;"})}"'

    return (
        f'<interaction id="{item["id"]}"'
        + a("ts", item["ts"])
        + a("agent", item["from_agent"])
        + a("model", item["model"])
        + a("provider", item["provider"])
        + a("task", item["task"])
        + a("latency_ms", item["latency_ms"])
        + a("tokens", item["tokens"])
        + a("ok", "true" if item["ok"] else "false")
        + ">"
        + f"<prompt>{_xml_escape(item['prompt'])}</prompt>"
        + f"<response>{_xml_escape(item['response'])}</response>"
        + "</interaction>\n"
    )


def _flush_sync(items: List[Dict[str, Any]]) -> int:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        if LEDGER_PATH.exists() and LEDGER_PATH.stat().st_size > ROTATE_BYTES:
            LEDGER_PATH.replace(LEDGER_PATH.with_suffix(".xml.1"))
    except OSError:
        pass
    with LEDGER_PATH.open("a", encoding="utf-8") as fh:
        for it in items:
            fh.write(_element(it))
    return len(items)


async def flush() -> int:
    """Persist pending interactions off the event loop. Best-effort."""
    if not _pending:
        return 0
    batch, _pending[:] = list(_pending), []
    try:
        return await asyncio.to_thread(_flush_sync, batch)
    except Exception as e:
        logger.debug(f"interaction_recorder.flush failed: {e}")
        return 0


def recent(limit: int = 40, agent: str = "", model: str = "") -> List[Dict[str, Any]]:
    """Most recent exchanges, newest first, with reaction counts attached."""
    items = list(_ring)
    if agent:
        items = [i for i in items if i["from_agent"] == agent]
    if model:
        items = [i for i in items if i["model"] == model]
    out = []
    for i in reversed(items[-max(1, limit):]):
        row = dict(i)
        row["reactions"] = _reactions.get(i["id"], {})
        out.append(row)
    return out


def summary() -> Dict[str, Any]:
    """Aggregate shape of the mind's conversation with AI."""
    items = list(_ring)
    if not items:
        return {"total": 0, "models": {}, "agents": {}, "window": None,
                "avg_latency_ms": None, "ok_rate": None, "reactions": 0}
    models: Dict[str, int] = {}
    agents: Dict[str, int] = {}
    lat: List[float] = []
    ok = 0
    for i in items:
        models[i["model"]] = models.get(i["model"], 0) + 1
        agents[i["from_agent"]] = agents.get(i["from_agent"], 0) + 1
        if i["latency_ms"]:
            lat.append(i["latency_ms"])
        if i["ok"]:
            ok += 1
    return {
        "total": len(items),
        "models": dict(sorted(models.items(), key=lambda kv: -kv[1])[:12]),
        "agents": dict(sorted(agents.items(), key=lambda kv: -kv[1])[:12]),
        "window": {"from": items[0]["ts"], "to": items[-1]["ts"]},
        "avg_latency_ms": round(sum(lat) / len(lat), 1) if lat else None,
        "ok_rate": round(ok / len(items), 3),
        "reactions": sum(sum(v.values()) for v in _reactions.values()),
        "topic_requests": len(_topic_requests),
        "ring_size": RING_SIZE,
        "recording": ENABLED,
    }


def react(interaction_id: str, kind: str) -> Dict[str, Any]:
    """Register a visitor reaction. Deliberately inert: it records a signal and
    triggers nothing. Observation is public; causation is not."""
    if kind not in REACTIONS:
        return {"ok": False, "error": f"unknown reaction (expected {REACTIONS})"}
    if not any(i["id"] == interaction_id for i in _ring):
        return {"ok": False, "error": "unknown interaction"}
    bucket = _reactions.setdefault(interaction_id, {})
    bucket[kind] = bucket.get(kind, 0) + 1
    return {"ok": True, "id": interaction_id, "reactions": bucket}


def request_topic(text: str) -> Dict[str, Any]:
    """Queue a topic a visitor would like the mind to think about.

    Queued only. mindX may or may not pick it up on a later cycle; nothing here
    reaches a prompt automatically, which is what keeps the public surface from
    being an injection vector into the autonomous loop.
    """
    t = _redact(text, 160)
    if not t:
        return {"ok": False, "error": "empty"}
    _topic_requests.append({"ts": time.time(), "text": t})
    return {"ok": True, "queued": len(_topic_requests), "text": t}


def topic_requests(limit: int = 20) -> List[Dict[str, Any]]:
    return list(_topic_requests)[-limit:][::-1]


def feed_xml(limit: int = 60) -> str:
    """The public XML substrate: a well-formed document over the live ring."""
    items = recent(limit)
    s = summary()
    head = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mindx:interactions xmlns:mindx="https://mindx.pythai.net/ns/interactions" '
        f'generated="{time.time()}" count="{len(items)}" '
        f'total="{s["total"]}" ok_rate="{s.get("ok_rate")}" '
        f'avg_latency_ms="{s.get("avg_latency_ms")}">\n'
    )
    body = []
    for i in items:
        el = _element(i).rstrip("\n")
        r = i.get("reactions") or {}
        if r:
            counts = "".join(f'<reaction kind="{k}" count="{v}"/>' for k, v in r.items())
            el = el.replace("</interaction>", f"{counts}</interaction>")
        body.append("  " + el)
    return head + "\n".join(body) + "\n</mindx:interactions>\n"
