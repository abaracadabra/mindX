#!/usr/bin/env python3
"""
OpenRouter boardroom probe — rate-limited end-to-end test.

Reads the OpenRouter API key from BANKON Vault (never from .env, never via argv),
fetches the live :free catalogue from GET /api/v1/models, then probes a curated
candidate slug per boardroom seat with a small prompt under a strict 8 RPS / 18
RPM client-side throttle to avoid tripping OpenRouter's account-wide rate limit.

Outputs a per-seat map of {slug, ok, latency_ms, finish_reason, error?} and writes
a fresh data/config/board_openrouter_map.json reflecting the empirically reachable
slugs.

Usage:
    .mindx_env/bin/python scripts/test_openrouter_boardroom.py
    .mindx_env/bin/python scripts/test_openrouter_boardroom.py --dry-run
    .mindx_env/bin/python scripts/test_openrouter_boardroom.py --soldier ciso_security

The script does not write the config file unless --write is passed.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from collections import deque
from pathlib import Path
from typing import Optional

import httpx

# Add project root to path so we can import mindx_backend_service
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mindx_backend_service.bankon_vault.vault import BankonVault
from mindx_backend_service.bankon_vault.credential_provider import CredentialProvider

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOARD_MAP_PATH = PROJECT_ROOT / "data" / "config" / "board_openrouter_map.json"

# Curated candidate slugs per seat, ordered primary → fallback.
# Empirically validated against https://openrouter.ai/models snapshot May 2026.
# Test will pick the first reachable + tool-capable slug per seat.
CANDIDATES = {
    # CEO — workhorse default, OpenAI-hosted
    "ceo": [
        "openai/gpt-oss-120b:free",
        "openai/gpt-oss-20b:free",
        "openrouter/free",
    ],
    # CISO — security/reasoning, NVIDIA-hosted (no Venice throttle)
    "ciso_security": [
        "nvidia/nemotron-3-super-120b-a12b:free",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "openai/gpt-oss-120b:free",
    ],
    # CFO — numeric, hybrid thinking, Z.AI-hosted
    "cfo_finance": [
        "z-ai/glm-4.5-air:free",
        "minimax/minimax-m2.5:free",
        "openai/gpt-oss-120b:free",
    ],
    # CTO — coding/architecture, try Poolside coder first (less throttled than Venice-Qwen)
    "cto_technology": [
        "poolside/laguna-m.1:free",
        "qwen/qwen3-coder:free",
        "openai/gpt-oss-120b:free",
    ],
    # CRO — risk/reasoning, MiniMax productivity-tuned
    "cro_risk": [
        "minimax/minimax-m2.5:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "openai/gpt-oss-120b:free",
    ],
    # CLO — legal/precedent, 1T param deep reasoner
    "clo_legal": [
        "inclusionai/ling-2.6-1t:free",
        "tencent/hy3-preview:free",
        "openai/gpt-oss-120b:free",
    ],
    # CPO — product/vision, NVIDIA vision-language
    "cpo_product": [
        "nvidia/nemotron-nano-12b-v2-vl:free",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "google/gemma-4-26b-a4b-it:free",
    ],
    # COO — ops tempo, NVIDIA Nano 30B (different model class than CISO/CRO)
    "coo_operations": [
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "nvidia/nemotron-nano-9b-v2:free",
        "openai/gpt-oss-120b:free",
    ],
}

PROBE_PROMPT = (
    "You are casting a vote on a routine boardroom directive. "
    "Reply with exactly one word: APPROVE, REJECT, or ABSTAIN. "
    "Directive: 'Schedule the next dream cycle 30 minutes from now.'"
)


class TokenBucket:
    """Async token-bucket rate limiter — no aiolimiter dep.

    Enforces both an RPS floor (max_per_sec) and a sliding-window minute cap
    (max_per_minute). Acquire blocks until both windows have headroom.
    """

    def __init__(self, max_per_sec: float = 8.0, max_per_minute: int = 18):
        self.max_per_sec = max_per_sec
        self.min_interval = 1.0 / max_per_sec
        self.max_per_minute = max_per_minute
        self._last_release = 0.0
        self._minute_window: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            # Drop minute-window entries older than 60s
            while self._minute_window and now - self._minute_window[0] > 60.0:
                self._minute_window.popleft()
            # Wait for minute-window headroom
            if len(self._minute_window) >= self.max_per_minute:
                sleep_for = 60.0 - (now - self._minute_window[0]) + 0.05
                await asyncio.sleep(sleep_for)
                now = time.monotonic()
                while self._minute_window and now - self._minute_window[0] > 60.0:
                    self._minute_window.popleft()
            # RPS spacing
            elapsed = now - self._last_release
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
                now = time.monotonic()
            self._last_release = now
            self._minute_window.append(now)


def load_openrouter_key() -> str:
    """Read OPENROUTER_API_KEY from BANKON Vault. Hard-fail if absent."""
    vault = BankonVault()
    provider = CredentialProvider(vault)
    results = provider.load_from_vault()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        stored = [k for k, v in results.items() if v]
        sys.stderr.write(
            "ERROR: openrouter_api_key not in BANKON Vault.\n"
            "Run: .mindx_env/bin/python manage_credentials.py store openrouter_api_key 'sk-or-v1-...'\n"
            f"Currently vaulted: {sorted(stored)}\n"
        )
        sys.exit(2)
    return key


async def fetch_models(client: httpx.AsyncClient, key: str) -> dict:
    """Fetch live OpenRouter model catalogue. Returns {slug: model_record}."""
    r = await client.get(
        f"{OPENROUTER_BASE}/models",
        headers={"Authorization": f"Bearer {key}"},
        timeout=30.0,
    )
    r.raise_for_status()
    data = r.json().get("data", [])
    return {m["id"]: m for m in data}


async def fetch_account(client: httpx.AsyncClient, key: str) -> dict:
    """Fetch /api/v1/key — usage, free-tier flag, daily cap."""
    r = await client.get(
        f"{OPENROUTER_BASE}/key",
        headers={"Authorization": f"Bearer {key}"},
        timeout=15.0,
    )
    r.raise_for_status()
    return r.json().get("data", {})


async def probe_slug(
    client: httpx.AsyncClient,
    key: str,
    slug: str,
    bucket: TokenBucket,
) -> dict:
    """Probe one slug with a tiny prompt; return result dict.

    Distinguishes 200 OK, 404 (no endpoints / deprecated), 429 (rate-limited),
    402 (insufficient credits), 5xx (upstream), and timeout.
    """
    await bucket.acquire()
    started = time.monotonic()
    try:
        r = await client.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": "https://mindx.pythai.net",
                "X-Title": "mindX-boardroom-probe",
            },
            json={
                "model": slug,
                "messages": [{"role": "user", "content": PROBE_PROMPT}],
                "max_tokens": 16,
                "temperature": 0.2,
            },
            timeout=45.0,
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        if r.status_code == 200:
            body = r.json()
            choice = body.get("choices", [{}])[0]
            text = (choice.get("message", {}) or {}).get("content", "") or ""
            return {
                "slug": slug,
                "ok": True,
                "status": 200,
                "latency_ms": latency_ms,
                "finish_reason": choice.get("finish_reason"),
                "provider": body.get("provider"),
                "actual_model": body.get("model"),
                "preview": text.strip()[:60],
                "usage": body.get("usage", {}),
            }
        # OpenRouter wraps errors in {"error": {...}}
        err = {}
        try:
            err = r.json().get("error", {})
        except Exception:
            err = {"raw": r.text[:200]}
        return {
            "slug": slug,
            "ok": False,
            "status": r.status_code,
            "latency_ms": latency_ms,
            "error_code": err.get("code"),
            "error_message": err.get("message"),
            "error_metadata": err.get("metadata"),
        }
    except httpx.TimeoutException:
        return {
            "slug": slug,
            "ok": False,
            "status": 0,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "error_message": "timeout",
        }
    except Exception as e:
        return {
            "slug": slug,
            "ok": False,
            "status": 0,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "error_message": f"{type(e).__name__}: {e}",
        }


def has_tools(model: dict) -> bool:
    sp = model.get("supported_parameters") or []
    return "tools" in sp


def is_free(model: dict) -> bool:
    p = model.get("pricing") or {}
    return p.get("prompt") == "0" and p.get("completion") == "0"


def context_len(model: dict) -> int:
    return int(model.get("context_length") or 0)


async def probe_seat(
    client: httpx.AsyncClient,
    key: str,
    seat: str,
    candidates: list[str],
    catalog: dict,
    bucket: TokenBucket,
) -> dict:
    """Walk the candidate list for one seat. First reachable + tool-capable wins."""
    attempts = []
    for slug in candidates:
        model = catalog.get(slug)
        if model is None:
            attempts.append({"slug": slug, "skipped": "not in live catalog"})
            continue
        attempts.append(
            {
                "slug": slug,
                "in_catalog": True,
                "is_free": is_free(model),
                "has_tools": has_tools(model),
                "context": context_len(model),
            }
        )
        result = await probe_slug(client, key, slug, bucket)
        attempts[-1].update(result)
        if result.get("ok"):
            return {"seat": seat, "chosen": slug, "attempts": attempts}
    return {"seat": seat, "chosen": None, "attempts": attempts}


def render_report(account: dict, results: list[dict], catalog_size: int) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("  OPENROUTER BOARDROOM PROBE")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"  Key label:      {account.get('label', '?')}")
    lines.append(f"  Free tier:      {account.get('is_free_tier')}")
    lines.append(f"  Daily cap:      {account.get('limit') or 'unlimited (paid)'}")
    lines.append(f"  Used today:     {account.get('usage_daily', '?')}")
    lines.append(f"  Live catalog:   {catalog_size} models")
    lines.append("")
    lines.append("  Per-seat result:")
    lines.append("")
    for r in results:
        seat = r["seat"]
        chosen = r["chosen"]
        if chosen:
            attempt = next(a for a in r["attempts"] if a.get("slug") == chosen)
            latency = attempt.get("latency_ms", "?")
            preview = attempt.get("preview", "")
            lines.append(f"  ✓ {seat:<18} {chosen}")
            lines.append(f"    {latency}ms   tools={attempt.get('has_tools')} ctx={attempt.get('context')}")
            if preview:
                lines.append(f"    reply: {preview}")
        else:
            lines.append(f"  ✗ {seat:<18} NO REACHABLE SLUG")
            for a in r["attempts"]:
                if "skipped" in a:
                    lines.append(f"      {a['slug']}: {a['skipped']}")
                else:
                    lines.append(
                        f"      {a['slug']}: {a.get('status')} {a.get('error_message') or ''}"
                    )
        lines.append("")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write data/config/board_openrouter_map.json with the empirical map",
    )
    parser.add_argument(
        "--soldier",
        type=str,
        default=None,
        help="Probe only one seat (e.g. 'ciso_security')",
    )
    parser.add_argument(
        "--rps",
        type=float,
        default=8.0,
        help="Max requests per second (default 8 — well below OR's 20 RPM cap)",
    )
    parser.add_argument(
        "--rpm",
        type=int,
        default=18,
        help="Max requests per minute window (default 18, OR cap is 20)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit full JSON report to stdout"
    )
    args = parser.parse_args()

    key = load_openrouter_key()
    bucket = TokenBucket(max_per_sec=args.rps, max_per_minute=args.rpm)

    seats = (
        {args.soldier: CANDIDATES[args.soldier]}
        if args.soldier
        else CANDIDATES
    )
    if args.soldier and args.soldier not in CANDIDATES:
        sys.stderr.write(
            f"Unknown seat: {args.soldier}\nValid: {sorted(CANDIDATES.keys())}\n"
        )
        return 2

    async with httpx.AsyncClient() as client:
        try:
            account = await fetch_account(client, key)
        except httpx.HTTPStatusError as e:
            sys.stderr.write(f"Auth check failed: {e.response.status_code} — key invalid?\n")
            return 3

        catalog = await fetch_models(client, key)
        results = []
        for seat, candidates in seats.items():
            r = await probe_seat(client, key, seat, candidates, catalog, bucket)
            results.append(r)

    report = render_report(account, results, len(catalog))
    print(report)

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps({"account": account, "results": results}, indent=2))

    # Build empirical map
    final_map = {r["seat"]: r["chosen"] for r in results}
    missing = [s for s, slug in final_map.items() if slug is None]
    if missing:
        sys.stderr.write(f"\nWARN: {len(missing)} seat(s) had no reachable slug: {missing}\n")

    if args.write and not missing:
        BOARD_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        BOARD_MAP_PATH.write_text(json.dumps(final_map, indent=2) + "\n")
        print(f"\nWrote: {BOARD_MAP_PATH}")
    elif args.write and missing:
        sys.stderr.write(
            "REFUSING to write incomplete map — fix candidates and re-run.\n"
        )
        return 1

    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
