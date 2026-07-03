"""mindX self-improvement SENTINEL target.

This module is a deliberately safe, self-contained target for the autonomous
self-improvement loop to exercise end-to-end (P1 effector → P2 apply → P3 judge
→ P4 substrate) WITHOUT risk. It imports nothing from the production system, has
no side effects, and is not imported by any production code path — so the loop
may rewrite, evaluate, and persist changes to it freely. If a campaign breaks
this file, nothing in production is affected.

It is an *external* improvement target (not the self-agent), so a successful
improvement persists in place and never triggers a service restart.

`SENTINEL_VERSION` and the simple functions below give the loop obvious,
low-risk room to improve (clarity, docstrings, edge cases). `verify()` lets the
status endpoint confirm the module still parses and runs after any change.
"""

SENTINEL_VERSION = 1


def describe_status() -> str:
    """Return a short human-readable status string for the sentinel."""
    return f"sentinel target alive (v{SENTINEL_VERSION})"


def add(a, b):
    # A deliberately under-documented helper — an easy, safe improvement target.
    return a + b


def verify() -> dict:
    """Self-check used by the status endpoint to confirm the sentinel is healthy.

    Returns a small dict; raising here would signal a broken sentinel.
    """
    ok = (add(2, 2) == 4) and isinstance(describe_status(), str)
    return {"healthy": bool(ok), "version": SENTINEL_VERSION}
