"""curate — keep only wisdom worth training on.

Not every dream deserves to become weights. Curation is where the ataraxia
alignment floor (the BOTTOM sentinel from the utility function) and the
DreamInsight composite score gate the corpus. A row survives only if:

  1. it carries a composite score >= min_score (importance × novelty ×
     confidence × log(frequency+1)), and
  2. it passes the alignment floor (no row flagged unsafe/redacted), and
  3. it is well-formed (system+user+assistant turns, non-empty assistant).

This is the training-time analogue of the kernel's proof gate: the model is
never taught from experience that did not raise utility. Wireheading via the
training set is structurally blocked — a malicious/low-value dream simply
does not enter the curriculum.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

from .distill import DreamRow

# A row whose alignment is unknown is treated conservatively: kept only if its
# score clears a higher bar. A row explicitly flagged unsafe is always dropped.
DEFAULT_MIN_SCORE = 0.05
UNKNOWN_ALIGNMENT_MIN_SCORE = 0.15


@dataclass
class CurationStats:
    seen: int = 0
    kept: int = 0
    dropped_malformed: int = 0
    dropped_low_score: int = 0
    dropped_unaligned: int = 0

    def as_dict(self) -> dict:
        return {
            "seen": self.seen,
            "kept": self.kept,
            "kept_fraction": round(self.kept / self.seen, 4) if self.seen else 0.0,
            "dropped_malformed": self.dropped_malformed,
            "dropped_low_score": self.dropped_low_score,
            "dropped_unaligned": self.dropped_unaligned,
        }


def _well_formed(row: DreamRow) -> bool:
    roles = {m.get("role") for m in row.messages}
    assistant = next((m.get("content", "") for m in row.messages
                      if m.get("role") == "assistant"), "")
    return {"user", "assistant"} <= roles and bool(str(assistant).strip())


def _aligned(row: DreamRow) -> bool | None:
    """Tri-state: True (clean), False (flagged unsafe), None (unknown)."""
    flag = row.meta.get("alignment")
    if flag in ("unsafe", "redacted", "blocked", False):
        return False
    if flag in ("clean", "safe", True):
        return True
    return None


def curate(
    rows: Iterable[DreamRow],
    *,
    min_score: float = DEFAULT_MIN_SCORE,
    stats: CurationStats | None = None,
) -> Iterator[DreamRow]:
    """Filter the corpus down to trainable, aligned, high-value wisdom."""
    st = stats if stats is not None else CurationStats()
    for row in rows:
        st.seen += 1
        if not _well_formed(row):
            st.dropped_malformed += 1
            continue
        aligned = _aligned(row)
        if aligned is False:
            st.dropped_unaligned += 1
            continue
        score = row.meta.get("score")
        score = float(score) if isinstance(score, (int, float)) else 0.0
        bar = min_score if aligned is True else UNKNOWN_ALIGNMENT_MIN_SCORE
        if score < bar:
            st.dropped_low_score += 1
            continue
        st.kept += 1
        yield row
