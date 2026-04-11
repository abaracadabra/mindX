#!/usr/bin/env python3
"""
test_cloud_inference.py — Quick test: send input, get response from every
Ollama Cloud model + local Ollama + vLLM. Compare footprints.

Usage:
  python3 scripts/test_cloud_inference.py
  python3 scripts/test_cloud_inference.py "What is mindX?"
  python3 scripts/test_cloud_inference.py --local-only
  python3 scripts/test_cloud_inference.py --cloud-only
  python3 scripts/test_cloud_inference.py --model deepseek-v3.2

Author: Professor Codephreak (© Professor Codephreak)
"""

import asyncio
import aiohttp
import json
import time
import sys
import os
import psutil

OLLAMA_LOCAL = os.getenv("MINDX_LLM__OLLAMA__BASE_URL", "http://localhost:11434")
OLLAMA_CLOUD = "https://ollama.com"
VLLM_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

DEFAULT_PROMPT = "You are mindX. In one sentence, describe what you are."


async def get_cloud_models():
    """Fetch available cloud models from ollama.com."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(f"{OLLAMA_CLOUD}/api/tags") as r:
                if r.status == 200:
                    data = await r.json()
                    return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        print(f"  [ERROR] Could not fetch cloud models: {e}")
    return []


async def get_local_models():
    """Fetch available local models from Ollama."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as s:
            async with s.get(f"{OLLAMA_LOCAL}/api/tags") as r:
                if r.status == 200:
                    data = await r.json()
                    return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


async def test_ollama(base_url: str, model: str, prompt: str, label: str, api_key: str = ""):
    """Test a single Ollama model (local or cloud)."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    # Measure memory before
    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss / 1024 / 1024
    prompt_tokens = len(prompt.split())  # rough estimate

    start = time.time()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as s:
            async with s.post(f"{base_url}/api/chat", json=payload, headers=headers) as r:
                elapsed = time.time() - start
                mem_after = proc.memory_info().rss / 1024 / 1024

                if r.status == 200:
                    raw = await r.read()
                    data = json.loads(raw)
                    response = data.get("message", {}).get("content", "")[:200]
                    total_duration = data.get("total_duration", 0)
                    eval_count = data.get("eval_count", 0)
                    prompt_eval_duration = data.get("prompt_eval_duration", 0)
                    eval_duration = data.get("eval_duration", 0)
                    tps = eval_count / (eval_duration / 1e9) if eval_duration > 0 else 0
                    ttft = prompt_eval_duration / 1e9 if prompt_eval_duration > 0 else 0
                    response_bytes = len(raw)
                    net_speed = response_bytes / 1024 / elapsed if elapsed > 0 else 0

                    return {
                        "label": label,
                        "model": model,
                        "status": "OK",
                        "response": response,
                        "latency_s": round(elapsed, 2),
                        "tokens": eval_count,
                        "prompt_tokens": prompt_tokens,
                        "tok_per_sec": round(tps, 1),
                        "time_to_first_token_s": round(ttft, 3),
                        "eval_duration_s": round(eval_duration / 1e9, 2) if eval_duration else 0,
                        "net_speed_kbps": round(net_speed, 1),
                        "response_bytes": response_bytes,
                        "mem_delta_mb": round(mem_after - mem_before, 1),
                        "mem_total_mb": round(mem_after, 1),
                    }
                else:
                    body = await r.text()
                    return {
                        "label": label, "model": model, "status": f"HTTP {r.status}",
                        "response": body[:100], "latency_s": round(elapsed, 2),
                    }
    except asyncio.TimeoutError:
        return {"label": label, "model": model, "status": "TIMEOUT (120s)", "latency_s": 120.0}
    except Exception as e:
        return {"label": label, "model": model, "status": f"ERROR: {e}", "latency_s": round(time.time() - start, 2)}


async def test_vllm(prompt: str):
    """Test vLLM via OpenAI-compatible API."""
    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss / 1024 / 1024

    payload = {
        "model": "default",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100,
    }
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("VLLM_API_KEY", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    start = time.time()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
            async with s.post(f"{VLLM_URL}/v1/chat/completions", json=payload, headers=headers) as r:
                elapsed = time.time() - start
                mem_after = proc.memory_info().rss / 1024 / 1024

                if r.status == 200:
                    data = await r.json()
                    response = data.get("choices", [{}])[0].get("message", {}).get("content", "")[:200]
                    usage = data.get("usage", {})
                    return {
                        "label": "vLLM",
                        "model": data.get("model", "?"),
                        "status": "OK",
                        "response": response,
                        "latency_s": round(elapsed, 2),
                        "tokens": usage.get("completion_tokens", 0),
                        "tok_per_sec": 0,
                        "mem_delta_mb": round(mem_after - mem_before, 1),
                        "mem_total_mb": round(mem_after, 1),
                    }
                else:
                    return {"label": "vLLM", "model": "?", "status": f"HTTP {r.status}", "latency_s": round(elapsed, 2)}
    except Exception as e:
        return {"label": "vLLM", "model": "?", "status": f"NOT AVAILABLE: {e}", "latency_s": 0}


def print_result(r):
    """Print raw scientific diagnostics — no bias, actual measurements.
    cypherpunk2048 standard: precision to 18 decimal places where available."""
    status = r.get("status", "?")
    model = r.get("model", "?")
    label = r.get("label", "?")

    print(f"  [{label:15s}] {model}")
    print(f"    status:           {status}")

    if status == "OK":
        print(f"    latency:          {r.get('latency_s', 0):.18f} s")
        print(f"    tokens_generated: {r.get('tokens', 0)}")
        print(f"    tokens_prompt:    {r.get('prompt_tokens', 0)}")
        print(f"    tok_per_sec:      {r.get('tok_per_sec', 0):.18f}")
        if r.get("time_to_first_token_s"):
            print(f"    ttft:             {r.get('time_to_first_token_s', 0):.18f} s")
        if r.get("eval_duration_s"):
            print(f"    eval_duration:    {r.get('eval_duration_s', 0):.18f} s")
        if r.get("net_speed_kbps"):
            print(f"    net_speed:        {r.get('net_speed_kbps', 0):.18f} KB/s")
        if r.get("response_bytes"):
            print(f"    response_bytes:   {r.get('response_bytes', 0)}")
        if r.get("mem_total_mb"):
            print(f"    mem_rss:          {r.get('mem_total_mb', 0):.6f} MB")
            print(f"    mem_delta:        {r.get('mem_delta_mb', 0):.6f} MB")
        print(f"    response:         {r.get('response', '')[:150]}")
    else:
        if r.get("response"):
            print(f"    detail:           {r.get('response', '')[:150]}")
        print(f"    latency:          {r.get('latency_s', 0):.18f} s")
    print()


async def main():
    args = sys.argv[1:]
    prompt = DEFAULT_PROMPT
    local_only = False
    cloud_only = False
    single_model = None

    for arg in args:
        if arg == "--local-only":
            local_only = True
        elif arg == "--cloud-only":
            cloud_only = True
        elif arg.startswith("--model"):
            single_model = args[args.index(arg) + 1] if arg == "--model" else arg.split("=")[1]
        elif not arg.startswith("-"):
            prompt = arg

    print(f"\n{'='*70}")
    print(f"  mindX Inference Test — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Prompt: \"{prompt[:60]}\"")
    print(f"{'='*70}\n")

    results = []

    # === LOCAL OLLAMA ===
    if not cloud_only:
        print("LOCAL OLLAMA ({})".format(OLLAMA_LOCAL))
        local_models = await get_local_models()
        if local_models:
            for model in local_models:
                if single_model and single_model not in model:
                    continue
                r = await test_ollama(OLLAMA_LOCAL, model, prompt, "local")
                results.append(r)
                print_result(r)
        else:
            print("  ✗ No local models available")
        print()

    # === VLLM ===
    if not cloud_only:
        print(f"VLLM ({VLLM_URL})")
        r = await test_vllm(prompt)
        results.append(r)
        print_result(r)
        print()

    # === OLLAMA CLOUD (via local Ollama client) ===
    if not local_only:
        print(f"OLLAMA CLOUD (via local Ollama → ollama.com)")
        cloud_models = await get_cloud_models()
        if cloud_models:
            print(f"  {len(cloud_models)} cloud models listed at ollama.com/api/tags")

            if single_model:
                cloud_models = [m for m in cloud_models if single_model in m]

            # Cloud models are accessed through the LOCAL Ollama client
            # The client handles authentication and proxying transparently
            # Test a few small cloud models to measure latency vs local
            small_cloud = [m for m in cloud_models if any(s in m for s in ["3b", "4b", "8b", ":12b", "nano"])]
            test_models = (small_cloud[:3] if not single_model else cloud_models[:3])

            if test_models:
                print(f"  Testing {len(test_models)} cloud models via local Ollama...\n")
                for model in test_models:
                    # Route through local Ollama (it proxies to cloud for cloud-only models)
                    r = await test_ollama(OLLAMA_LOCAL, model, prompt, "cloud-via-local")
                    results.append(r)
                    print_result(r)
                    if model != test_models[-1]:
                        await asyncio.sleep(2)
            else:
                print("  No small cloud models found for testing")

            # Also test direct cloud API (requires OLLAMA_API_KEY)
            if OLLAMA_API_KEY:
                print(f"\n  Direct cloud API (with key)...")
                for model in cloud_models[:2]:
                    r = await test_ollama(OLLAMA_CLOUD, model, prompt, "cloud-direct", OLLAMA_API_KEY)
                    results.append(r)
                    print_result(r)
                    await asyncio.sleep(2)
            else:
                print(f"\n  Direct cloud API: set OLLAMA_API_KEY for authenticated access")
                print(f"  Cloud models available without key via: ollama run <cloud-model>")
        else:
            print("  ✗ Could not reach Ollama Cloud")
        print()

    # === SUMMARY ===
    print(f"{'='*70}")
    print("  SUMMARY")
    print(f"{'='*70}")

    ok = [r for r in results if r.get("status") == "OK"]
    failed = [r for r in results if r.get("status") != "OK"]

    print(f"  Tested: {len(results)} | OK: {len(ok)} | Failed: {len(failed)}")

    if ok:
        fastest = min(ok, key=lambda r: r.get("latency_s", 999))
        slowest = max(ok, key=lambda r: r.get("latency_s", 0))
        print(f"  Fastest: {fastest['model']} ({fastest['latency_s']}s)")
        print(f"  Slowest: {slowest['model']} ({slowest['latency_s']}s)")

        local_results = [r for r in ok if r.get("label") == "local"]
        cloud_results = [r for r in ok if r.get("label") == "cloud"]
        vllm_results = [r for r in ok if r.get("label") == "vLLM"]

        # Objective aggregate metrics — raw measurements, no bias
        total_tokens = sum(r.get("tokens", 0) for r in ok)
        total_bytes = sum(r.get("response_bytes", 0) for r in ok)
        total_latency = sum(r.get("latency_s", 0) for r in ok)

        print(f"\n  AGGREGATE METRICS (objective)")
        print(f"    models_tested:    {len(ok)}")
        print(f"    total_tokens:     {total_tokens}")
        print(f"    total_bytes:      {total_bytes}")
        print(f"    total_latency:    {total_latency:.18f} s")
        if ok:
            print(f"    mean_latency:     {total_latency / len(ok):.18f} s")
            print(f"    mean_tok_per_sec: {sum(r.get('tok_per_sec', 0) for r in ok) / len(ok):.18f}")
            print(f"    min_latency:      {min(r.get('latency_s', 999) for r in ok):.18f} s ({fastest['model']})")
            print(f"    max_latency:      {max(r.get('latency_s', 0) for r in ok):.18f} s ({slowest['model']})")

        for group_label, group_results in [("OLLAMA_LOCAL", local_results), ("OLLAMA_CLOUD", cloud_results), ("VLLM", vllm_results)]:
            if group_results:
                n = len(group_results)
                print(f"\n  {group_label} ({n} model{'s' if n > 1 else ''}):")
                print(f"    mean_latency:     {sum(r['latency_s'] for r in group_results) / n:.18f} s")
                print(f"    mean_tok_per_sec: {sum(r.get('tok_per_sec', 0) for r in group_results) / n:.18f}")
                if any(r.get("time_to_first_token_s") for r in group_results):
                    print(f"    mean_ttft:        {sum(r.get('time_to_first_token_s', 0) for r in group_results) / n:.18f} s")
                if any(r.get("net_speed_kbps") for r in group_results):
                    print(f"    mean_net_speed:   {sum(r.get('net_speed_kbps', 0) for r in group_results) / n:.18f} KB/s")
                if any(r.get("mem_total_mb") for r in group_results):
                    print(f"    mean_mem_rss:     {sum(r.get('mem_total_mb', 0) for r in group_results) / n:.6f} MB")

    # Save results
    results_file = os.path.join(os.path.dirname(__file__), "..", "data", "inference_test_results.json")
    try:
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        with open(results_file, "w") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "prompt": prompt,
                "results": results,
            }, f, indent=2)
        print(f"\n  Results saved: {results_file}")
    except Exception:
        pass

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
