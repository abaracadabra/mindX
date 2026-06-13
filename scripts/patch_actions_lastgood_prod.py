#!/usr/bin/env python
"""Surgically patch prod main_service.py so the diagnostics 'actions' array retains
its last non-empty value through transient pgvector stalls (CPU-load timeouts that
return [] and zero the Recent Actions panel). Asserts each anchor appears once."""
P = "/home/mindx/mindX/mindx_backend_service/main_service.py"
s = open(P).read()

A_OLD = '''_diag_cache_ts: float = 0.0   # When the cache was last populated'''
A_NEW = '''_diag_cache_ts: float = 0.0   # When the cache was last populated
_diag_last_actions: list = []  # Last non-empty recent-actions (survives DB stalls)'''

B_OLD = '''        actions_data = await _safe_await(_mpg2.get_recent_actions(limit=10), default=[])
    except Exception:
        pass'''
B_NEW = '''        actions_data = await _safe_await(_mpg2.get_recent_actions(limit=10), default=[])
    except Exception:
        pass
    # Retain last-good: a transient pgvector stall under CPU load returns [] and
    # would zero the "Recent Actions" panel. Keep the previous non-empty result
    # until a fresh one lands, so the panel stays populated through serving stalls.
    global _diag_last_actions
    if actions_data:
        _diag_last_actions = actions_data
    elif _diag_last_actions:
        actions_data = _diag_last_actions'''

for name, old in [("A", A_OLD), ("B", B_OLD)]:
    n = s.count(old)
    assert n == 1, f"anchor {name} count={n} (expected 1) — aborting"
assert "_diag_last_actions" not in s.replace(A_OLD, ""), "already patched?"
s = s.replace(A_OLD, A_NEW, 1).replace(B_OLD, B_NEW, 1)
open(P, "w").write(s)
print("patched: actions last-good retention")
