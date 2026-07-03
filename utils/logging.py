"""
utils/logging.py — the public-transparency layer over mindX logging.

In mindX, logs are memories and memories are logs: every log line the system
writes is also catalogued as a memory (`memory.write` events), machine.dreaming
consolidates those memories into long-term knowledge, and AuthorAgent delivers
that knowledge to rage.pythai.net. This module widens the FIRST link of that
chain for the public: it taps the live Python logging stream, classifies each
record into a public "lane", redacts secrets, and keeps a bounded, public-safe
activity feed that the landing page (mindx.pythai.net) renders via
`/insight/public/activity`.

Lanes mirror the knowledge flow:
    memory      logs becoming memories (memory_agent, catalogue, pgvector, offload)
    dreaming    machine.dreaming gleaning wisdom from information
    knowledge   knowledge delivery to rage.pythai.net (author/editor/artist/wordpress)
    improvement self-improvement (SEA, BDI, AGInt, godel, eval)
    governance  boardroom / mastermind / coordinator / CEO
    system      everything else, WARNING and above only

Safety properties (these are the contract — see tests/test_public_activity_logging.py):
  * every headline passes `redact()` (API keys, ETH private keys, JWTs,
    key=value secrets, absolute /home paths) before it is stored anywhere;
  * loggers whose name matches the denylist (vault, credential, identity,
    wallet, key-manager) are never published, at any level;
  * unmatched loggers only surface at WARNING+ so the public feed shows the
    cognitive loop, not framework noise;
  * the handler can never raise into the host application;
  * `MINDX_PUBLIC_ACTIVITY_DISABLE=1` is a cold kill switch.

This module is intentionally backend-agnostic (no imports from
mindx_backend_service) so any mindX process — backend, scripts, agents run
standalone — feeds the same public stream at data/logs/public_activity.jsonl.

NOTE: this is `utils.logging`, not the stdlib `logging`; absolute imports keep
the stdlib module reachable everywhere, including inside this file.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from .logging_config import LOG_DIR, get_logger, setup_logging  # noqa: F401  (re-export)

PUBLIC_ACTIVITY_FILENAME = "public_activity.jsonl"
PUBLIC_ACTIVITY_PATH = LOG_DIR / PUBLIC_ACTIVITY_FILENAME
ROTATE_BYTES = 5 * 1024 * 1024   # small file: headlines only, rotate at 5 MB
RING_SIZE = 600                  # in-process ring the insight endpoint reads
HEADLINE_MAX_LEN = 140           # matches /insight/agentic/activity headline width
PER_LOGGER_MIN_INTERVAL = 2.0    # seconds between INFO rows from one logger

# ── Secret redaction ──────────────────────────────────────────────────────
# Kept in lockstep with mindx_backend_service.text_render._SECRET_PATTERNS
# (utils must not import the backend; the backend keeps its own copy for
# non-log surfaces). Anything shown on a public page goes through redact().

_SECRET_PATTERNS: tuple = (
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), "<key>"),                 # OpenAI-style
    (re.compile(r"\bAIza[A-Za-z0-9_-]{20,}"), "<key>"),                # Google
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "<key>"),            # GitHub
    (re.compile(r"\bxox[bap]-[A-Za-z0-9-]{10,}"), "<key>"),            # Slack
    (re.compile(r"\b0x[a-fA-F0-9]{64}\b"), "<privkey>"),               # ETH private key
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}"), "<jwt>"),
    (re.compile(
        r"(?i)\b(api[_-]?key|secret|password|passwd|token|bearer|private[_-]?key|"
        r"mnemonic|seed[_-]?phrase)\b\s*[=:]\s*[\"']?[^\s\"',;]{6,}"
    ), r"\1=<redacted>"),
    (re.compile(r"/home/[A-Za-z0-9_.-]+"), "~"),                       # absolute home paths
)


def redact(s: Any, max_len: int = HEADLINE_MAX_LEN) -> str:
    """Redact secrets + collapse whitespace + truncate. Safe for public HTML.

    ETH wallet *addresses* (0x + 40 hex) are intentionally kept — the wallet
    address is the agent's public identity. Only 64-hex private keys are
    scrubbed.
    """
    if not s:
        return ""
    out = str(s)
    for pat, repl in _SECRET_PATTERNS:
        out = pat.sub(repl, out)
    out = " ".join(out.split())
    if len(out) > max_len:
        out = out[: max_len - 1].rstrip() + "…"
    return out


# ── Lane classification ───────────────────────────────────────────────────

LANES: Dict[str, str] = {
    "memory":      "logs becoming memories — every log mindX writes is also a memory",
    "dreaming":    "machine.dreaming — wisdom gleaned from information on the lunar cycle",
    "knowledge":   "knowledge delivery — AuthorAgent publishing to rage.pythai.net",
    "improvement": "self-improvement — SEA / BDI / AGInt / Gödel choices / eval",
    "governance":  "governance — boardroom, mastermind, coordinator, CEO",
    "system":      "system — warnings and errors from everything else",
}

# Logger-name patterns, first match wins. Names are module __name__s.
_LANE_RULES: tuple = (
    ("memory", re.compile(
        r"(memory_agent|memory_pgvector|catalogue|storage\.(offload|eligibility|car_bundle|anchor)"
        r"|offload_projector)", re.I)),
    ("dreaming", re.compile(r"machine_dreaming|dream", re.I)),
    ("knowledge", re.compile(
        r"(author_agent|author_composition|publication_orchestrator|wordpress_agent"
        r"|editor_agent|artist_agent|github_awareness)", re.I)),
    ("improvement", re.compile(
        r"(strategic_evolution|self_improve|bdi_agent|agint|godel|agents\.eval"
        r"|blueprint_agent|simple_coder)", re.I)),
    ("governance", re.compile(
        r"(boardroom|mastermind|coordinator_agent|ceo|dojo|guardian)", re.I)),
)

# Never published, at any level: anything that handles raw key material.
_DENY_LOGGER_RE = re.compile(
    r"(vault|credential|secret|id_manager|identity|wallet|keys?_manager|bankon_vault)", re.I)


def classify_logger(name: str) -> Optional[str]:
    """Map a logger name to a public lane; None when it has no dedicated lane."""
    for lane, pat in _LANE_RULES:
        if pat.search(name or ""):
            return lane
    return None


def _disabled() -> bool:
    return os.environ.get("MINDX_PUBLIC_ACTIVITY_DISABLE", "").strip().lower() in (
        "1", "true", "yes")


# ── The handler ───────────────────────────────────────────────────────────

class PublicActivityHandler(logging.Handler):
    """logging.Handler that mirrors qualifying records into the public feed.

    Each accepted record becomes one small JSON row:
        {"ts": <epoch>, "lane": <lane>, "logger": <tail>, "level": <name>,
         "headline": <redacted message>}
    appended to data/logs/public_activity.jsonl (rotating) and to an
    in-process ring buffer that `recent_public_activity()` serves from.
    """

    def __init__(self, path: Path = PUBLIC_ACTIVITY_PATH, level: int = logging.INFO):
        super().__init__(level=level)
        self.path = Path(path)
        self.ring: Deque[Dict[str, Any]] = deque(maxlen=RING_SIZE)
        self._file_lock = threading.Lock()
        self._last_emit: Dict[str, float] = {}   # logger name → monotonic ts (throttle)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    def emit(self, record: logging.LogRecord) -> None:  # never raises
        try:
            if _disabled():
                return
            name = record.name or ""
            if _DENY_LOGGER_RE.search(name):
                return
            lane = classify_logger(name)
            if lane is None:
                # No dedicated lane → only warnings/errors surface, as "system".
                if record.levelno < logging.WARNING:
                    return
                lane = "system"
            now = time.monotonic()
            if record.levelno < logging.WARNING:
                # Light per-logger throttle so a chatty INFO loop can't flood
                # the public feed; warnings and errors always pass.
                last = self._last_emit.get(name, 0.0)
                if now - last < PER_LOGGER_MIN_INTERVAL:
                    return
            self._last_emit[name] = now
            headline = redact(record.getMessage())
            if not headline:
                return
            row = {
                "ts": round(record.created, 3),
                "lane": lane,
                "logger": name.rsplit(".", 1)[-1][:48],
                "level": record.levelname,
                "headline": headline,
            }
            self.ring.append(row)
            self._append_file(row)
        except Exception:
            # The public mirror must never break the thing it mirrors.
            pass

    def _append_file(self, row: Dict[str, Any]) -> None:
        line = json.dumps(row, separators=(",", ":")) + "\n"
        with self._file_lock:
            try:
                if self.path.exists() and self.path.stat().st_size >= ROTATE_BYTES:
                    stamp = time.strftime("%Y%m%d-%H%M%S")
                    rotated = self.path.with_name(
                        f"{self.path.stem}.{stamp}{self.path.suffix}")
                    n = 1
                    while rotated.exists():
                        rotated = self.path.with_name(
                            f"{self.path.stem}.{stamp}-{n}{self.path.suffix}")
                        n += 1
                    os.rename(self.path, rotated)
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(line)
            except OSError:
                pass  # ring still serves in-process reads


# ── Install / read API ────────────────────────────────────────────────────

_handler: Optional[PublicActivityHandler] = None
_install_lock = threading.Lock()


def enable_public_activity(level: int = logging.INFO,
                           path: Path = PUBLIC_ACTIVITY_PATH) -> Optional[PublicActivityHandler]:
    """Attach the public-activity mirror to the root logger. Idempotent.

    Call after `setup_logging()`. Returns the handler (or None when disabled
    via MINDX_PUBLIC_ACTIVITY_DISABLE).
    """
    global _handler
    if _disabled():
        return None
    with _install_lock:
        if _handler is not None:
            return _handler
        _handler = PublicActivityHandler(path=path, level=level)
        logging.getLogger().addHandler(_handler)
        return _handler


def disable_public_activity() -> None:
    """Detach the mirror (tests / emergency)."""
    global _handler
    with _install_lock:
        if _handler is not None:
            logging.getLogger().removeHandler(_handler)
            _handler = None


def recent_public_activity(limit: int = 40, lane: Optional[str] = None,
                           path: Path = PUBLIC_ACTIVITY_PATH) -> List[Dict[str, Any]]:
    """Newest-first public activity rows, optionally filtered to one lane.

    Serves from the in-process ring when the handler is installed (the normal
    backend case); falls back to a bounded tail-read of the JSONL file so the
    feed survives restarts and works cross-process.
    """
    limit = max(1, min(int(limit or 40), 200))
    rows: List[Dict[str, Any]] = []
    if _handler is not None and _handler.ring:
        src: List[Dict[str, Any]] = list(_handler.ring)
        for row in reversed(src):
            if lane and row.get("lane") != lane:
                continue
            rows.append(row)
            if len(rows) >= limit:
                return rows
        if rows:
            return rows
    # File fallback — bounded tail so it stays O(1) on file size.
    try:
        p = Path(path)
        if not p.exists():
            return rows
        TAIL_BYTES = 256 * 1024
        with open(p, "rb") as f:
            f.seek(0, 2)
            sz = f.tell()
            start = max(0, sz - TAIL_BYTES)
            f.seek(start)
            chunk = f.read()
        lines = chunk.splitlines()
        if start > 0 and lines:
            lines = lines[1:]
        for raw in reversed(lines):
            if len(rows) >= limit:
                break
            try:
                row = json.loads(raw.decode("utf-8", errors="replace"))
            except Exception:
                continue
            if lane and row.get("lane") != lane:
                continue
            rows.append(row)
    except OSError:
        pass
    return rows


def lane_summary(limit: int = 200, path: Path = PUBLIC_ACTIVITY_PATH) -> Dict[str, int]:
    """Row counts per lane over the most recent window — landing-page chips."""
    counts: Dict[str, int] = {lane: 0 for lane in LANES}
    for row in recent_public_activity(limit=limit, path=path):
        lane = row.get("lane")
        if lane in counts:
            counts[lane] += 1
    return counts


def get_public_logger(name: str) -> logging.Logger:
    """`get_logger` that also guarantees the public mirror is installed.

    Use from agents whose work should be publicly visible by default — the
    returned logger is a normal stdlib logger; publication happens at the
    root handler, subject to lane rules, redaction and the denylist.
    """
    logger = get_logger(name)
    enable_public_activity()
    return logger
