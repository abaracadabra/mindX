#!/usr/bin/env python3
"""
THOT dimension math auditor.

Reads the 11 valid THOT dimensions from `mindx_backend_service/main_service.py`
(the source of truth) and prints, for each, the precise mathematical
expressions a cypherpunk-aware audience would expect:

    decimal       — the integer value
    binary log2   — exact only when value is a power of two
    powers-of-2   — k·2^n decomposition (k smallest odd factor)
    decimal SI    — value / 1e6 with 6 digits of fraction (no rounding lies)
    binary IEC    — value / 2^20 with IEC suffix (Ki / Mi)
    1024-base K   — value / 1024 (cypherpunk-pure)

Compares each row's `display` label and `purpose` (which may claim "(2^N)")
against the true math, and reports any inconsistency.

This is a read-only auditor. It does not modify code.
"""
from __future__ import annotations
import math
import re
from pathlib import Path
from typing import Optional

SRC = Path(__file__).resolve().parent.parent / "mindx_backend_service" / "main_service.py"


def parse_thot_dimensions(src_path: Path = SRC) -> list[dict]:
    """Pull THOT_DIMENSIONS out of main_service.py without importing the FastAPI app.

    Walks the source as text, finds the THOT_DIMENSIONS = [...] block, and
    parses it with ast.literal_eval — safe (no execution) and no FastAPI
    side effects.
    """
    import ast
    text = src_path.read_text()
    m = re.search(r"^THOT_DIMENSIONS\s*=\s*(\[)", text, re.MULTILINE)
    if not m:
        raise SystemExit(f"THOT_DIMENSIONS not found in {src_path}")
    # Walk forward from the opening bracket, balanced brackets.
    start = m.start(1)
    depth = 0
    end = -1
    for i, ch in enumerate(text[start:], start=start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit("Unterminated THOT_DIMENSIONS list")
    return ast.literal_eval(text[start:end])


def is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def factor_2(n: int) -> tuple[int, int]:
    """Return (k, e) such that n = k * 2^e with k odd. For powers of two k=1."""
    if n <= 0:
        return (n, 0)
    e = 0
    k = n
    while k % 2 == 0:
        k //= 2
        e += 1
    return (k, e)


def decimal_si(n: int) -> str:
    """Exact decimal rendering with the largest fitting SI prefix.
    Uses up to 6 fractional digits, then strips trailing zeros."""
    if abs(n) < 1_000:
        return f"{n}"
    units = [(1e9, "G"), (1e6, "M"), (1e3, "K")]
    for div, unit in units:
        if abs(n) >= div:
            val = n / div
            s = f"{val:.6f}".rstrip("0").rstrip(".")
            return f"{s}{unit}"
    return f"{n}"


def iec_binary(n: int) -> str:
    """IEC binary prefixes (Ki=1024, Mi=1024^2, Gi=1024^3). Exact for powers of 1024."""
    if abs(n) < 1024:
        return f"{n}"
    units = [(1024**3, "Gi"), (1024**2, "Mi"), (1024, "Ki")]
    for div, unit in units:
        if abs(n) >= div:
            val = n / div
            if val == int(val):
                return f"{int(val)}{unit}"
            s = f"{val:.6f}".rstrip("0").rstrip(".")
            return f"{s}{unit}"
    return f"{n}"


def thousand_24_base(n: int) -> str:
    """Cypherpunk-pure: express as multiples of 1024 (K)."""
    if n < 1024:
        return f"{n}"
    val = n / 1024
    if val == int(val):
        return f"{int(val)}K"
    s = f"{val:.6f}".rstrip("0").rstrip(".")
    return f"{s}K"


def claimed_exponent(purpose: str) -> Optional[int]:
    """If the purpose string claims '(2^N)', extract N. Else None."""
    m = re.search(r"\(2\^(\d+)\)", purpose)
    return int(m.group(1)) if m else None


def audit(rows: list[dict]) -> None:
    print(f"{'dim':>10}  {'display':<10}  {'purpose':<48}  {'2^?':>6}  decimal-SI    binary-IEC   1024-base   verdict")
    print("─" * 130)
    issues: list[str] = []
    for row in rows:
        dim: int = row["dim"]
        display: str = row.get("display") or ""
        purpose: str = row.get("purpose", "")
        # Math
        pow2 = is_power_of_two(dim)
        k, e = factor_2(dim)
        log2 = f"2^{e}" if pow2 else f"{k}·2^{e}"
        si = decimal_si(dim)
        iec = iec_binary(dim)
        b1024 = thousand_24_base(dim)
        # Claim check
        claim = claimed_exponent(purpose)
        verdict = "ok"
        if claim is not None and 2 ** claim != dim:
            issues.append(f"  • dim={dim} purpose claims (2^{claim}) but 2^{claim}={2**claim}")
            verdict = "MISMATCH"
        if display:
            # Check display label is consistent with the dim
            consistent_options = {
                decimal_si(dim),                 # e.g. 1.048576M
                f"{dim/1e6:.2f}M".rstrip("0").rstrip(".") if dim >= 1e6 else "",  # 1.05M
                iec_binary(dim),                 # 1Mi
                thousand_24_base(dim),           # 1024K
                str(dim),                        # raw
            }
            if display not in consistent_options and display.upper() not in {x.upper() for x in consistent_options}:
                issues.append(f"  • dim={dim} display='{display}' does not equal any precise label "
                              f"(decimal={si}, IEC={iec}, 1024-base={b1024})")
                verdict = "DISPLAY-IMPRECISE"
        print(f"{dim:>10}  {display:<10}  {purpose:<48}  {log2:>6}  {si:<13} {iec:<12} {b1024:<10}  {verdict}")
    print()
    if issues:
        print("ISSUES FOUND:")
        for i in issues:
            print(i)
        print()
        print("RECOMMENDED LABELS (precise):")
        for row in rows:
            d = row["dim"]
            print(f"  dim={d:<8}  decimal-SI={decimal_si(d):<12}  IEC={iec_binary(d):<8}  1024-base={thousand_24_base(d)}")
    else:
        print("✓ all 11 rows: math claims and display labels are consistent.")


def main() -> int:
    rows = parse_thot_dimensions()
    print(f"Source: {SRC}\n")
    print(f"Loaded {len(rows)} THOT dimensions.\n")
    audit(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
