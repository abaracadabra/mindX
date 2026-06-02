#!/usr/bin/env python
"""Probe: which model the planner SHOULD use. Compares the capable served model
vs the weak default on a planning-style prompt. Read-only diagnostic."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm.llm_factory import create_llm_handler

PROMPT = (
    'Respond ONLY with a JSON object of the form {"plan": ["step one", "step two"]}. '
    "Make a concise 2-step plan to add input validation to an API endpoint."
)


async def probe(provider, model):
    try:
        h = await create_llm_handler(provider_name=provider, model_name=model)
        if not h:
            return f"{provider}/{model}: NO HANDLER"
        r = await h.generate_text(PROMPT, model=h.model_name_for_api, json_mode=True, max_tokens=200)
        body = repr(r)[:180] if r else "EMPTY/None"
        return f"{provider}/{h.model_name_for_api}: {body}"
    except Exception as e:
        return f"{provider}/{model}: ERR {type(e).__name__}: {e}"


async def main():
    bare = await create_llm_handler()
    print("BARE DEFAULT:", f"{bare.provider_name}/{bare.model_name_for_api}" if bare else None)
    print(await probe("ollama", "gpt-oss:120b-cloud"))
    print(await probe("ollama", "qwen3:1.7b"))


if __name__ == "__main__":
    asyncio.run(main())
