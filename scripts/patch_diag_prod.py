#!/usr/bin/env python
"""Surgically patch /diagnostics/live on the prod main_service.py to serve a
cached snapshot + refresh in the background (never block under CPU load).
Idempotent-ish: asserts each anchor appears exactly once before replacing."""
P = "/home/mindx/mindX/mindx_backend_service/main_service.py"
s = open(P).read()

A_OLD = '''@app.get("/diagnostics/live", tags=["diagnostics"])
async def diagnostics_live_endpoint():
    global _diag_last_probe, _diag_cache, _diag_cache_ts
    now = time.time()

    # Serve cached response if fresh (prevents worker exhaustion from 6s polling)
    if _diag_cache and (now - _diag_cache_ts) < _DIAG_CACHE_TTL:
        return _diag_cache

    up_s = int(now - _diag_start)'''
A_NEW = '''async def _diag_compute():
    """Heavy diagnostics gather - run from the endpoint (cold cache only) or a
    background refresher, so the endpoint never blocks on it under CPU load."""
    global _diag_last_probe, _diag_cache, _diag_cache_ts
    now = time.time()
    up_s = int(now - _diag_start)'''

B_OLD = '''    # Cache response for subsequent polls
    _diag_cache = response
    _diag_cache_ts = time.time()

    return response'''
B_NEW = '''    # Cache response for subsequent polls
    _diag_cache = response
    _diag_cache_ts = time.time()
    return response


_diag_refreshing = False


async def _diag_bg_refresh():
    global _diag_refreshing
    try:
        await _diag_compute()
    except Exception:
        pass
    finally:
        _diag_refreshing = False


@app.get("/diagnostics/live", tags=["diagnostics"])
async def diagnostics_live_endpoint():
    """Always serve the cached snapshot; refresh in the BACKGROUND when stale, so
    the page never blocks on the heavy gather under CPU saturation. Only the very
    first (cold-cache) call kicks a background compute and returns a placeholder."""
    global _diag_refreshing
    now = time.time()
    if (not _diag_cache or (now - _diag_cache_ts) >= _DIAG_CACHE_TTL) and not _diag_refreshing:
        _diag_refreshing = True
        asyncio.create_task(_diag_bg_refresh())
    if _diag_cache:
        return _diag_cache
    return {"warming_up": True, "uptime_seconds": int(now - _diag_start)}'''

C_OLD = "    data = await diagnostics_live_endpoint()"
C_NEW = "    data = _diag_cache or await _diag_compute()"

for name, old in [("A", A_OLD), ("B", B_OLD), ("C", C_OLD)]:
    n = s.count(old)
    assert n == 1, f"anchor {name} count={n} (expected 1) — aborting"
s = s.replace(A_OLD, A_NEW, 1).replace(B_OLD, B_NEW, 1).replace(C_OLD, C_NEW, 1)
open(P, "w").write(s)
print("patched diagnostics endpoint (serve-cache + background refresh)")
