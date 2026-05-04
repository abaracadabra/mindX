#!/usr/bin/env python3
"""Probe Ollama Cloud and local Ollama for model availability.

Reads candidate model list from data/catalogue/ollama_library.json (cloud-tagged
entries) plus boardroom_assignments tier2/tier3 from data/config/ollama_cloud_models.json.
Sends a minimal completion to each, classifies as: ok / 403 / 404 / timeout / error.
Writes data/catalogue/cloud_probe_results.json with the working set so the
boardroom can be re-assigned to verified models only.

Run on the VPS where OLLAMA_API_KEY is in env.
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import aiohttp

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_PATH = PROJECT_ROOT / "data" / "catalogue" / "ollama_library.json"
CONFIG_PATH = PROJECT_ROOT / "data" / "config" / "ollama_cloud_models.json"
RESULTS_PATH = PROJECT_ROOT / "data" / "catalogue" / "cloud_probe_results.json"

OLLAMA_CLOUD_URL = "https://ollama.com"
OLLAMA_LOCAL_URL = "http://localhost:11434"


async def probe_one(sess: aiohttp.ClientSession, model: str, base_url: str, headers: dict) -> dict:
    """Probe a single model with a 1-token completion. Returns status dict."""
    payload = {
        "model": model,
        "prompt": "Respond with the single word: ok",
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 4},
    }
    t0 = time.time()
    try:
        async with sess.post(f"{base_url}/api/generate", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=45)) as r:
            elapsed_ms = int((time.time() - t0) * 1000)
            if r.status == 200:
                data = await r.json()
                text = (data.get("response") or "").strip()[:80]
                return {"model": model, "status": "ok", "http": 200, "ms": elapsed_ms, "sample": text}
            else:
                body = (await r.text())[:200]
                return {"model": model, "status": f"http_{r.status}", "http": r.status, "ms": elapsed_ms, "body": body}
    except asyncio.TimeoutError:
        return {"model": model, "status": "timeout", "ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        return {"model": model, "status": "error", "ms": int((time.time() - t0) * 1000), "error": f"{type(e).__name__}: {str(e)[:120]}"}


async def main():
    api_key = os.environ.get("OLLAMA_API_KEY", "")
    if not api_key:
        print("ERROR: OLLAMA_API_KEY not in env", file=sys.stderr)
        return 1

    candidates_cloud: set[str] = set()
    candidates_local: set[str] = set()

    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text())
        for m in cfg.get("cloud_models", []):
            name = m.get("name")
            if name:
                candidates_cloud.add(f"{name}:cloud")
        for entry in cfg.get("cloud_pool", []):
            if entry and not entry.endswith(":cloud") and ":" not in entry:
                candidates_cloud.add(f"{entry}:cloud")
            elif entry:
                candidates_cloud.add(entry)
        for m in cfg.get("local_models_on_vps", []):
            name = m.get("name")
            if name:
                candidates_local.add(name)
        for soldier, tiers in cfg.get("boardroom_assignments", {}).items():
            if not isinstance(tiers, dict):
                continue
            for k in ("tier1", "tier2", "tier3"):
                v = tiers.get(k)
                if not v:
                    continue
                if k == "tier1":
                    candidates_local.add(v)
                else:
                    if not v.endswith(":cloud") and "cloud" not in v:
                        candidates_cloud.add(f"{v}:cloud")
                    else:
                        candidates_cloud.add(v)

    if CATALOGUE_PATH.exists():
        cat = json.loads(CATALOGUE_PATH.read_text())
        models_blob = cat.get("models", {})
        # models is keyed by name → entry
        if isinstance(models_blob, dict):
            entries = models_blob.values()
        else:
            entries = models_blob
        for entry in entries:
            if isinstance(entry, dict) and entry.get("is_cloud") and entry.get("name"):
                tag = next((t for t in (entry.get("tags") or []) if t.endswith("cloud")), "cloud")
                candidates_cloud.add(f"{entry['name']}:{tag}")

    candidates_cloud = sorted(candidates_cloud)
    candidates_local = sorted(candidates_local)
    print(f"Probing {len(candidates_cloud)} cloud models + {len(candidates_local)} local models...")

    # IMPORTANT: cloud models are NOT probed via direct https://ollama.com when
    # the local daemon has been `ollama signin`-authenticated. The daemon proxies
    # `name:cloud` model calls using its ed25519 keypair — independent of the
    # OLLAMA_API_KEY env var. So we route both cloud and local through the local
    # daemon, serially (memory-tight box: don't race model loads).
    sem = asyncio.Semaphore(1)

    async def with_sem(coro):
        async with sem:
            return await coro

    async with aiohttp.ClientSession() as sess:
        cloud_results = []
        for m in candidates_cloud:
            cloud_results.append(await probe_one(sess, m, OLLAMA_LOCAL_URL, {}))
        local_results = []
        # Skip embedding-only models — they don't support /api/generate
        skip_local = {"mxbai-embed-large:latest", "nomic-embed-text:latest"}
        for m in candidates_local:
            if m in skip_local:
                local_results.append({"model": m, "status": "skipped_embedding", "ms": 0})
                continue
            local_results.append(await probe_one(sess, m, OLLAMA_LOCAL_URL, {}))

    cloud_working = [r for r in cloud_results if r["status"] == "ok"]
    cloud_403 = [r for r in cloud_results if r.get("http") == 403]
    cloud_404 = [r for r in cloud_results if r.get("http") == 404]
    cloud_other = [r for r in cloud_results if r["status"] != "ok" and r.get("http") not in (403, 404)]

    local_working = [r for r in local_results if r["status"] == "ok"]
    local_404 = [r for r in local_results if r.get("http") == 404]
    local_other = [r for r in local_results if r["status"] not in ("ok", "skipped_embedding") and r.get("http") != 404]

    out = {
        "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "cloud_total": len(cloud_results),
            "cloud_ok": len(cloud_working),
            "cloud_403_subscription": len(cloud_403),
            "cloud_404_unavailable": len(cloud_404),
            "cloud_other_error": len(cloud_other),
            "local_total": len(local_results),
            "local_ok": len(local_working),
            "local_missing": len(local_404),
            "local_error": len(local_other),
        },
        "cloud_working": [r["model"] for r in cloud_working],
        "cloud_403_models": [r["model"] for r in cloud_403],
        "cloud_404_models": [r["model"] for r in cloud_404],
        "local_working": [r["model"] for r in local_working],
        "local_missing": [r["model"] for r in local_404],
        "raw_cloud": cloud_results,
        "raw_local": local_results,
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(out, indent=2))

    print(f"\nCloud:  {out['summary']['cloud_ok']}/{out['summary']['cloud_total']} working")
    print(f"        403 subscription gated: {out['summary']['cloud_403_subscription']}")
    print(f"        404 unavailable:        {out['summary']['cloud_404_unavailable']}")
    print(f"        other errors:           {out['summary']['cloud_other_error']}")
    print(f"Local:  {out['summary']['local_ok']}/{out['summary']['local_total']} working")
    print(f"\nWorking cloud models:")
    for m in sorted(out["cloud_working"]):
        print(f"  ✓ {m}")
    print(f"\nWorking local models:")
    for m in sorted(out["local_working"]):
        print(f"  ✓ {m}")
    print(f"\nResults saved to {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
