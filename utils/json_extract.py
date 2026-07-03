"""utils.json_extract — tolerant JSON extraction from LLM output.

Free-tier and small local models (qwen3:0.6b on a throttled CPU, OpenRouter
free reasoning models) frequently wrap JSON in prose, markdown fences, or
``<think>…</think>`` blocks, or emit whitespace-only responses when starved.
``json.loads`` on that raises ``Expecting value: line 1 column 1 (char 0)`` and
— historically — failed every autonomous campaign at PROPOSE_TOOL_STRATEGY.

``extract_json`` strips that scaffolding and recovers the first valid JSON
object/array. It NEVER raises — callers get ``None`` on genuine failure and can
decide whether to retry or degrade, instead of a crash propagating up the BDI
loop.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

# Reasoning models emit chain-of-thought in these wrappers before the answer.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
# ```json … ``` or ``` … ``` fenced blocks.
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def _balanced_span(text: str, open_ch: str, close_ch: str) -> Optional[str]:
    """Return the first balanced ``open_ch…close_ch`` substring, or None.

    String-aware so braces inside JSON string values do not unbalance the count.
    """
    start = text.find(open_ch)
    if start == -1:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_json(raw: Any) -> Optional[Any]:
    """Best-effort parse of JSON embedded in arbitrary LLM text.

    Returns the parsed object, or ``None`` if nothing parseable is found.
    Never raises.
    """
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw  # already structured
    text = str(raw).strip()
    if not text:
        return None

    # 1) Direct parse — the happy path for json_mode-compliant models.
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass

    # 2) Strip reasoning wrappers, then retry direct.
    cleaned = _THINK_RE.sub("", text).strip()
    if cleaned != text:
        try:
            return json.loads(cleaned)
        except (ValueError, TypeError):
            pass

    # 3) Fenced code block content.
    m = _FENCE_RE.search(cleaned)
    if m:
        inner = m.group(1).strip()
        try:
            return json.loads(inner)
        except (ValueError, TypeError):
            cleaned = inner  # fall through to balanced-span on the fence body

    # 4) First balanced object, then first balanced array.
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        span = _balanced_span(cleaned, open_ch, close_ch)
        if span:
            try:
                return json.loads(span)
            except (ValueError, TypeError):
                continue

    return None
