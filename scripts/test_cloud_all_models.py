#!/usr/bin/env python3
"""
test_cloud_all_models.py — Single input, one response from every Ollama cloud model.

Reports ACTUAL token counts and timing from the Ollama API response (no estimation).
Uses precision diagnostics: eval_count, prompt_eval_count, durations in nanoseconds,
tokens/sec derived from eval_count / eval_duration.

Access:
  1. Already-pulled cloud models → local Ollama proxy (free tier, no key)
  2. Remaining models → Ollama Pull API to register, then query
  3. If OLLAMA_API_KEY set → direct cloud API for all models

Cloud offload key insight:
  Models ending in -cloud (e.g. gpt-oss:120b-cloud) are metadata-only pulls.
  The local Ollama daemon proxies inference to ollama.com transparently.
  Models WITHOUT -cloud suffix download full weights for local execution.

Usage:
    python3 scripts/test_cloud_all_models.py
    python3 scripts/test_cloud_all_models.py "Your custom prompt here"
    python3 scripts/test_cloud_all_models.py --local   # only test already-pulled models
    python3 scripts/test_cloud_all_models.py --direct   # use direct cloud API (needs key)

Author: Professor Codephreak
"""

import asyncio
import aiohttp
import json
import time
import sys
import os
from decimal import Decimal, getcontext

getcontext().prec = 36

OLLAMA_LOCAL = os.getenv("MINDX_LLM__OLLAMA__BASE_URL", "http://localhost:11434")
OLLAMA_CLOUD = "https://ollama.com"
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
DEFAULT_PROMPT = "You are mindX. In one sentence, describe what you are."

NANO_TO_SEC = Decimal("1e-9")
NANO_TO_MS = Decimal("1e-6")
SUBTOKEN_FACTOR = Decimal(10) ** 18


async def fetch_cloud_catalog() -> list[str]:
    """Fetch cloud model names from ollama.com/api/tags (public, no auth)."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
            async with s.get(f"{OLLAMA_CLOUD}/api/tags") as r:
                if r.status == 200:
                    data = await r.json()
                    return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        print(f"  ERROR fetching cloud catalog: {e}")
    return []


async def fetch_local_models() -> list[str]:
    """Fetch locally-pulled model names."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as s:
            async with s.get(f"{OLLAMA_LOCAL}/api/tags") as r:
                if r.status == 200:
                    data = await r.json()
                    return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


async def test_model(
    model: str,
    prompt: str,
    base_url: str = OLLAMA_LOCAL,
    api_key: str = "",
    label: str = "local",
) -> dict:
    """
    Send one request, return ACTUAL metrics from the Ollama API response.
    No estimation. Every number is from the API or the wall clock.
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    wall_start_ns = time.time_ns()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=180)) as s:
            async with s.post(f"{base_url}/api/chat", json=payload, headers=headers) as r:
                wall_end_ns = time.time_ns()
                wall_ns = wall_end_ns - wall_start_ns

                if r.status == 200:
                    raw = await r.read()
                    data = json.loads(raw)

                    eval_count = data.get("eval_count", 0)
                    prompt_eval_count = data.get("prompt_eval_count", 0)
                    total_duration_ns = data.get("total_duration", 0)
                    load_duration_ns = data.get("load_duration", 0)
                    prompt_eval_duration_ns = data.get("prompt_eval_duration", 0)
                    eval_duration_ns = data.get("eval_duration", 0)

                    # tokens/sec: prefer eval_duration (local), fall back to total_duration (cloud proxy)
                    if eval_duration_ns > 0:
                        tps = Decimal(str(eval_count)) / (Decimal(str(eval_duration_ns)) * NANO_TO_SEC)
                    elif total_duration_ns > 0 and eval_count > 0:
                        tps = Decimal(str(eval_count)) / (Decimal(str(total_duration_ns)) * NANO_TO_SEC)
                    else:
                        tps = Decimal("0")

                    prompt_tps = (
                        Decimal(str(prompt_eval_count)) / (Decimal(str(prompt_eval_duration_ns)) * NANO_TO_SEC)
                        if prompt_eval_duration_ns > 0 else Decimal("0")
                    )
                    wall_ms = Decimal(str(wall_ns)) * NANO_TO_MS
                    total_ms = Decimal(str(total_duration_ns)) * NANO_TO_MS

                    content = data.get("message", {}).get("content", "")

                    return {
                        "model": model,
                        "label": label,
                        "status": "OK",
                        "response": content[:250],
                        "eval_count": eval_count,
                        "prompt_eval_count": prompt_eval_count,
                        "total_tokens": eval_count + prompt_eval_count,
                        "total_tokens_subtokens": str(Decimal(eval_count + prompt_eval_count) * SUBTOKEN_FACTOR),
                        "total_duration_ns": total_duration_ns,
                        "load_duration_ns": load_duration_ns,
                        "prompt_eval_duration_ns": prompt_eval_duration_ns,
                        "eval_duration_ns": eval_duration_ns,
                        "wall_duration_ns": wall_ns,
                        "tokens_per_sec": str(tps.quantize(Decimal("1e-18"))),
                        "prompt_tokens_per_sec": str(prompt_tps.quantize(Decimal("1e-18"))),
                        "total_ms": str(total_ms.quantize(Decimal("1e-18"))),
                        "wall_ms": str(wall_ms.quantize(Decimal("1e-18"))),
                        "done_reason": data.get("done_reason", ""),
                        "response_bytes": len(raw),
                    }
                elif r.status == 401:
                    return {"model": model, "label": label, "status": "UNAUTHORIZED", "wall_duration_ns": wall_ns}
                else:
                    body = await r.text()
                    return {"model": model, "label": label, "status": f"HTTP {r.status}", "error": body[:200], "wall_duration_ns": wall_ns}
    except asyncio.TimeoutError:
        return {"model": model, "label": label, "status": "TIMEOUT", "wall_duration_ns": time.time_ns() - wall_start_ns}
    except Exception as e:
        return {"model": model, "label": label, "status": "ERROR", "error": str(e)[:200], "wall_duration_ns": time.time_ns() - wall_start_ns}


def print_result(r: dict, idx: int, total: int):
    """Print diagnostics for one model — actual values, 18dp precision."""
    model = r.get("model", "?")
    status = r.get("status", "?")
    label = r.get("label", "?")
    print(f"\n  [{idx:2d}/{total}] {model} ({label})")
    print(f"  {'─' * 62}")

    if status != "OK":
        print(f"    status:                  {status}")
        if r.get("error"):
            print(f"    detail:                  {r['error'][:120]}")
        wall = r.get("wall_duration_ns", 0)
        if wall:
            print(f"    wall_time:               {Decimal(str(wall)) * NANO_TO_MS:.6f} ms")
        return

    print(f"    eval_count:              {r['eval_count']}")
    print(f"    prompt_eval_count:       {r['prompt_eval_count']}")
    print(f"    total_tokens:            {r['total_tokens']}")
    print(f"    total_tokens_subtokens:  {r['total_tokens_subtokens']}")
    print(f"    total_duration_ns:       {r['total_duration_ns']}")
    print(f"    load_duration_ns:        {r['load_duration_ns']}")
    print(f"    prompt_eval_duration_ns: {r['prompt_eval_duration_ns']}")
    print(f"    eval_duration_ns:        {r['eval_duration_ns']}")
    print(f"    wall_duration_ns:        {r['wall_duration_ns']}")
    print(f"    tokens_per_sec:          {r['tokens_per_sec']}")
    print(f"    prompt_tokens_per_sec:   {r['prompt_tokens_per_sec']}")
    print(f"    total_ms:                {r['total_ms']}")
    print(f"    wall_ms:                 {r['wall_ms']}")
    print(f"    done_reason:             {r['done_reason']}")
    print(f"    response_bytes:          {r['response_bytes']}")

    resp = r.get("response", "")
    if resp:
        print(f"    response:                {resp[:160]}")


def print_aggregate(results: list[dict]):
    """Print aggregate diagnostics."""
    ok = [r for r in results if r.get("status") == "OK"]
    failed = [r for r in results if r.get("status") != "OK"]

    print(f"\n{'=' * 70}")
    print(f"  AGGREGATE — {len(ok)} succeeded, {len(failed)} failed out of {len(results)}")
    print(f"{'=' * 70}")

    if not ok:
        print("  No successful responses.")
        if failed:
            print(f"\n  FAILED ({len(failed)}):")
            for r in failed:
                print(f"    {r['model']:40s} {r['status']} {r.get('error', '')[:60]}")
        return

    total_eval = sum(r["eval_count"] for r in ok)
    total_prompt = sum(r["prompt_eval_count"] for r in ok)
    total_tokens = total_eval + total_prompt
    total_eval_duration_ns = sum(r["eval_duration_ns"] for r in ok)
    total_wall_ns = sum(r["wall_duration_ns"] for r in ok)

    agg_tps = (
        Decimal(str(total_eval)) / (Decimal(str(total_eval_duration_ns)) * NANO_TO_SEC)
        if total_eval_duration_ns > 0 else Decimal("0")
    )

    q = lambda d: str(d.quantize(Decimal("1e-18")))

    print(f"\n  TOKEN COUNTS (actual from Ollama API)")
    print(f"    total_eval_count:             {total_eval}")
    print(f"    total_prompt_eval_count:      {total_prompt}")
    print(f"    total_tokens:                 {total_tokens}")
    print(f"    total_tokens_subtokens:       {Decimal(total_tokens) * SUBTOKEN_FACTOR}")
    print(f"    mean_tokens_per_response:     {q(Decimal(str(total_tokens)) / Decimal(str(len(ok))))}")

    print(f"\n  TIMING (nanoseconds from Ollama API)")
    print(f"    total_eval_duration_ns:       {total_eval_duration_ns}")
    print(f"    total_wall_duration_ns:       {total_wall_ns}")

    print(f"\n  THROUGHPUT (Decimal, 18dp)")
    print(f"    aggregate_tokens_per_sec:     {q(agg_tps)}")
    print(f"    mean_wall_ms:                 {q(Decimal(str(total_wall_ns)) * NANO_TO_MS / Decimal(str(len(ok))))}")

    ranked = sorted(ok, key=lambda r: Decimal(r["tokens_per_sec"]), reverse=True)
    print(f"\n  RANKING BY TOKENS/SEC")
    for i, r in enumerate(ranked):
        tps_short = str(Decimal(r["tokens_per_sec"]).quantize(Decimal("0.01")))
        print(f"    {i+1:2d}. {r['model']:40s} {tps_short:>10} tok/s  ({r['eval_count']} eval, {r['total_tokens']} total)")

    if failed:
        print(f"\n  FAILED ({len(failed)})")
        for r in failed:
            print(f"    {r['model']:40s} {r['status']} {r.get('error', '')[:60]}")


async def main():
    args = sys.argv[1:]
    prompt = DEFAULT_PROMPT
    local_only = False
    direct_only = False

    for arg in args:
        if arg == "--local":
            local_only = True
        elif arg == "--direct":
            direct_only = True
        elif not arg.startswith("-"):
            prompt = arg

    print(f"\n{'=' * 70}")
    print(f"  mindX Cloud Model Test — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Prompt: \"{prompt[:60]}\"")
    print(f"  Metrics: ACTUAL from Ollama API (no estimation)")
    print(f"  Precision: 18 decimal places (Decimal)")
    print(f"  OLLAMA_API_KEY: {'set' if OLLAMA_API_KEY else 'not set'}")
    print(f"{'=' * 70}")

    results = []

    # === Phase 1: Test already-pulled local/cloud models ===
    if not direct_only:
        print(f"\n  PHASE 1: Already-pulled models (via {OLLAMA_LOCAL})")
        local_models = await fetch_local_models()
        if local_models:
            print(f"  Found {len(local_models)} local models: {', '.join(local_models)}")
            for i, model in enumerate(local_models, 1):
                label = "cloud-proxy" if "cloud" in model else "local"
                r = await test_model(model, prompt, OLLAMA_LOCAL, label=label)
                results.append(r)
                print_result(r, i, len(local_models))
                if i < len(local_models):
                    await asyncio.sleep(2)
        else:
            print("  No local models found.")

    # === Phase 2: Direct cloud API (requires key) ===
    if not local_only:
        print(f"\n  PHASE 2: Direct cloud API (ollama.com)")
        cloud_catalog = await fetch_cloud_catalog()

        if not cloud_catalog:
            print("  Cannot reach ollama.com/api/tags")
        elif not OLLAMA_API_KEY:
            print(f"  {len(cloud_catalog)} cloud models available")
            print(f"  Set OLLAMA_API_KEY for direct cloud API access")
            print(f"  Or use: ollama pull <model>-cloud  then test with --local")
        else:
            # Skip models we already tested locally
            tested = {r["model"] for r in results}
            remaining = [m for m in cloud_catalog if m not in tested]
            print(f"  {len(cloud_catalog)} in catalog, {len(remaining)} not yet tested")

            total = len(remaining)
            for i, model in enumerate(remaining, 1):
                r = await test_model(model, prompt, OLLAMA_CLOUD, api_key=OLLAMA_API_KEY, label="cloud-direct")
                results.append(r)
                print_result(r, i, total)
                # Pace: 3s between requests (free tier safety)
                if i < total:
                    await asyncio.sleep(3)

    # === Aggregate ===
    print_aggregate(results)

    # === Save ===
    results_file = os.path.join(os.path.dirname(__file__), "..", "data", "cloud_test_results.json")
    try:
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        with open(results_file, "w") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "prompt": prompt,
                "precision": "18_decimal_places",
                "models_tested": len(results),
                "results": results,
            }, f, indent=2)
        print(f"\n  Results saved: {results_file}")
    except Exception as e:
        print(f"\n  Could not save results: {e}")

    print(f"\n{'=' * 70}\n")


if __name__ == "__main__":
    asyncio.run(main())
