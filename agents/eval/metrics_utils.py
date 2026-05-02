# Portions adapted from confident-ai/deepeval (Apache-2.0). See NOTICE.
"""
Permissive JSON parsing for judge LLM outputs.

mindX uses CPU-pillar models (qwen3:1.7b, deepseek-r1) by default for
eval-as-cheap-as-possible. Small models often wrap JSON in code fences
or chain-of-thought; we strip fences and substring-extract the first
{...} balanced-brace block.

Replaces deepeval/metrics/utils.py:trimAndLoadJson + the Pydantic
structured-output pipeline (generate_with_schema_and_extract).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def trim_and_load_json(text: str) -> Dict[str, Any]:
    """Best-effort JSON extraction from a judge LLM response.

    Order of attempts:
      1. Strip code fences if present, parse the fenced block.
      2. Direct json.loads of the whole string.
      3. Substring-extract the first balanced {...} block and parse it.

    Raises ValueError if no parseable object is found.
    """
    if not isinstance(text, str):
        raise ValueError("Judge output is not a string")

    fence_match = _FENCE_RE.search(text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in judge output")
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Brace block is not valid JSON: {exc}")
    raise ValueError("Unbalanced braces in judge output")
