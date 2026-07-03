#!/usr/bin/env python
"""Add last-good retention for the diagnostics `database` (pgvector health) key, so a
slow health query can't blank the Memory & Knowledge + Storage panels. Mirrors the
existing _diag_last_actions / _diag_last_godel pattern. Asserts each anchor is unique;
no-op if already applied. Operates on the prod (divergent) main_service.py."""
P = "/home/mindx/mindX/mindx_backend_service/main_service.py"
s = open(P).read()

if "_diag_last_database" in s:
    print("already patched (found _diag_last_database) — aborting")
    raise SystemExit(0)

A_OLD = '_diag_last_godel: list = []    # Last non-empty Gödel choices (survives read stalls)'
A_NEW = A_OLD + '\n_diag_last_database: dict = {}  # Last connected pgvector health (survives query stalls)'

B_OLD = 'global _diag_last_probe, _diag_cache, _diag_cache_ts, _diag_last_godel'
B_NEW = 'global _diag_last_probe, _diag_cache, _diag_cache_ts, _diag_last_godel, _diag_last_database'

C_OLD = '''        db_health = await _safe_await(_mpg.health_check(), default={})
    except Exception:
        pass'''
C_NEW = '''        db_health = await _safe_await(_mpg.health_check(), default={})
    except Exception:
        pass
    # Retain last-good: a slow health query returns {} and would blank the Memory &
    # Knowledge + Storage panels. Keep the previous connected health until a fresh
    # connected one lands (only overwrite when we actually got a connected reading).
    if db_health.get("status") == "connected":
        _diag_last_database = db_health
    elif _diag_last_database:
        db_health = _diag_last_database'''

pairs = [("A", A_OLD, A_NEW), ("B", B_OLD, B_NEW), ("C", C_OLD, C_NEW)]
for name, old, _new in pairs:
    n = s.count(old)
    assert n == 1, f"anchor {name} count={n} (expected 1) — aborting, no changes written"
for name, old, new in pairs:
    s = s.replace(old, new, 1)
open(P, "w").write(s)
print("patched: database last-good retention (_diag_last_database)")
