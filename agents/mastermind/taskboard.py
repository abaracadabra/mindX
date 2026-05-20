# SPDX-License-Identifier: Apache-2.0
"""Kanban-style durable task board for MASTERMIND.

Sixth absorption from the Hermes/OpenClaw research stack (Hermes integration
doc §8.3). Hermes v0.13.0 "Tenacity" introduced a Kanban subsystem with a
SQLite-backed durable task board, per-task heartbeat monitoring, zombie
detection at the dispatcher, and a hallucination gate at completion. mindX
inherits the same operational primitive at the cognitive tier — a task here
is a BDI Intention with explicit pre/postconditions, a retry budget, and a
worker assignment. The hallucination gate verifies the worker's claim of
completion against actual Belief state + the postconditions declared on the
task.

Six columns (matches Hermes verbatim so the dashboard pattern is familiar):

    Triage → Todo → Ready → InProgress → Blocked → Done

Default backing store: ``$MINDX_MASTERMIND_DB`` or
``~/.mindx/mastermind.db``. WAL mode. ``PRAGMA integrity_check`` on first
open per process — the mindX improvement over Hermes (§10 of the Hermes
integration doc).

Hallucination gate:
  When a worker calls ``complete(task_id, claim, belief_state)``:
    * Each declared postcondition is checked against ``belief_state``.
      A truthy entry in ``belief_state[key]`` means the postcondition holds.
    * Each entry in ``claim`` is also verified — if the worker says
      "done" but the belief state contradicts the claim, the task is
      bounced back to ``Triage`` with the gate findings appended to
      ``task.notes`` so the next worker sees the prior attempt + reason.
    * On match: task transitions to ``Done``.

No LLM, no external dep beyond Python's stdlib sqlite3. The implementation
is intentionally substrate-only — scheduling, dispatch, and worker
processes are operator-wired (a future MASTERMIND change can drive this).
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("agents.mastermind.taskboard")

# Column order = the workflow. Anything earlier can transition forward to
# anything later; the reverse is allowed only for Triage (via the gate's
# bounce).
COLUMNS = ("Triage", "Todo", "Ready", "InProgress", "Blocked", "Done")

# Default heartbeat TTL — if a worker hasn't pinged within this window the
# dispatcher reclaims the task. Matches the Hermes default (the doc cites
# "every N seconds" without a number; 90 s is a sensible mindX default).
DEFAULT_TTL_S = 90


@dataclass
class Task:
    """One row in the task board."""
    id: str
    title: str
    column: str = "Triage"
    intention_template: Optional[str] = None
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    worker: Optional[str] = None
    retry_budget: int = 3
    retries_used: int = 0
    ttl_s: int = DEFAULT_TTL_S
    heartbeat_at: Optional[float] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    notes: str = ""
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "column": self.column,
            "intention_template": self.intention_template,
            "preconditions": list(self.preconditions),
            "postconditions": list(self.postconditions),
            "worker": self.worker,
            "retry_budget": self.retry_budget, "retries_used": self.retries_used,
            "ttl_s": self.ttl_s,
            "heartbeat_at": self.heartbeat_at,
            "started_at": self.started_at, "finished_at": self.finished_at,
            "notes": self.notes,
            "created_at": self.created_at, "updated_at": self.updated_at,
        }


@dataclass
class CompletionGateResult:
    """Outcome of the hallucination gate at task completion."""
    accepted: bool
    matched_postconditions: list[str] = field(default_factory=list)
    missing_postconditions: list[str] = field(default_factory=list)
    contradicting_claims: list[str] = field(default_factory=list)


def _new_id() -> str:
    return f"task-{int(time.time())}-{secrets.token_hex(3)}"


class TaskBoardError(Exception):
    pass


class TaskBoard:
    """SQLite-backed Kanban task board with heartbeat + hallucination gate."""

    def __init__(self, db_path: Optional[Path | str] = None):
        if db_path is None:
            env = os.environ.get("MINDX_MASTERMIND_DB")
            db_path = Path(env) if env else Path.home() / ".mindx" / "mastermind.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    # ─── schema ────────────────────────────────────────────────
    def _init_schema(self) -> None:
        with self._lock:
            c = self._conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id                  TEXT PRIMARY KEY,
                title               TEXT NOT NULL,
                column_name         TEXT NOT NULL,
                intention_template  TEXT,
                preconditions_json  TEXT NOT NULL DEFAULT '[]',
                postconditions_json TEXT NOT NULL DEFAULT '[]',
                worker              TEXT,
                retry_budget        INTEGER NOT NULL DEFAULT 3,
                retries_used        INTEGER NOT NULL DEFAULT 0,
                ttl_s               INTEGER NOT NULL DEFAULT 90,
                heartbeat_at        REAL,
                started_at          REAL,
                finished_at         REAL,
                notes               TEXT NOT NULL DEFAULT '',
                created_at          REAL NOT NULL,
                updated_at          REAL NOT NULL
            )""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_column ON tasks(column_name)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker)")
            # PRAGMA integrity_check — mindX improvement over Hermes (§10).
            try:
                row = c.execute("PRAGMA integrity_check").fetchone()
                if row and row[0] != "ok":
                    logger.warning(f"taskboard integrity: {row[0]}")
            except Exception:
                pass
            self._conn.commit()

    # ─── CRUD ──────────────────────────────────────────────────
    def add(self, *, title: str, intention_template: Optional[str] = None,
            preconditions: Optional[list[str]] = None,
            postconditions: Optional[list[str]] = None,
            retry_budget: int = 3, ttl_s: int = DEFAULT_TTL_S,
            column: str = "Triage", notes: str = "") -> Task:
        if column not in COLUMNS:
            raise TaskBoardError(f"unknown column {column!r}")
        t = Task(
            id=_new_id(), title=title.strip() or "untitled",
            column=column,
            intention_template=intention_template,
            preconditions=list(preconditions or []),
            postconditions=list(postconditions or []),
            retry_budget=int(retry_budget), ttl_s=int(ttl_s),
            notes=notes,
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO tasks (id,title,column_name,intention_template,preconditions_json,postconditions_json,worker,retry_budget,retries_used,ttl_s,heartbeat_at,started_at,finished_at,notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (t.id, t.title, t.column, t.intention_template,
                 json.dumps(t.preconditions), json.dumps(t.postconditions),
                 t.worker, t.retry_budget, t.retries_used, t.ttl_s,
                 t.heartbeat_at, t.started_at, t.finished_at, t.notes,
                 t.created_at, t.updated_at),
            )
            self._conn.commit()
        return t

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            row = self._conn.execute(
                "SELECT id,title,column_name,intention_template,preconditions_json,postconditions_json,worker,retry_budget,retries_used,ttl_s,heartbeat_at,started_at,finished_at,notes,created_at,updated_at FROM tasks WHERE id=?",
                (task_id,)).fetchone()
        if not row:
            return None
        return Task(
            id=row[0], title=row[1], column=row[2], intention_template=row[3],
            preconditions=json.loads(row[4] or "[]"),
            postconditions=json.loads(row[5] or "[]"),
            worker=row[6], retry_budget=int(row[7]), retries_used=int(row[8]),
            ttl_s=int(row[9]), heartbeat_at=row[10],
            started_at=row[11], finished_at=row[12], notes=row[13] or "",
            created_at=float(row[14]), updated_at=float(row[15]),
        )

    def list(self, *, column: Optional[str] = None) -> list[Task]:
        out: list[Task] = []
        with self._lock:
            if column:
                sql = "SELECT id FROM tasks WHERE column_name=? ORDER BY created_at"
                params: tuple = (column,)
            else:
                sql = "SELECT id FROM tasks ORDER BY column_name, created_at"
                params = ()
            ids = [r[0] for r in self._conn.execute(sql, params).fetchall()]
        for tid in ids:
            t = self.get(tid)
            if t:
                out.append(t)
        return out

    def board(self) -> dict[str, list[dict]]:
        """Group tasks by column for the dashboard. {column: [task_dict, ...]}."""
        cols: dict[str, list[dict]] = {c: [] for c in COLUMNS}
        for t in self.list():
            cols.setdefault(t.column, []).append(t.to_dict())
        return cols

    # ─── transitions ───────────────────────────────────────────
    def transition(self, task_id: str, *, to: str, by: Optional[str] = None,
                   note: Optional[str] = None) -> Task:
        if to not in COLUMNS:
            raise TaskBoardError(f"unknown column {to!r}")
        t = self.get(task_id)
        if not t:
            raise TaskBoardError(f"no task {task_id}")
        now = time.time()
        if to == "InProgress" and t.column in ("Todo", "Ready", "Blocked", "Triage"):
            t.worker = by or t.worker
            t.started_at = t.started_at or now
            t.heartbeat_at = now
        if to == "Triage":
            # Bounce: drop worker, increment retries, append note.
            t.worker = None
            t.retries_used += 1
            t.heartbeat_at = None
        if to == "Done":
            t.finished_at = now
            t.worker = t.worker
        t.column = to
        t.updated_at = now
        if note:
            t.notes = (t.notes + ("\n" if t.notes else "") + note).strip()
        with self._lock:
            self._conn.execute(
                "UPDATE tasks SET column_name=?, worker=?, retries_used=?, heartbeat_at=?, started_at=?, finished_at=?, notes=?, updated_at=? WHERE id=?",
                (t.column, t.worker, t.retries_used, t.heartbeat_at,
                 t.started_at, t.finished_at, t.notes, t.updated_at, t.id),
            )
            self._conn.commit()
        return t

    def claim(self, task_id: str, worker: str) -> Task:
        """Move Todo/Ready → InProgress and stamp the worker."""
        return self.transition(task_id, to="InProgress", by=worker)

    def heartbeat(self, task_id: str, worker: str) -> bool:
        """Worker ping. Returns False if the task was reclaimed or is gone."""
        t = self.get(task_id)
        if not t or t.column != "InProgress" or t.worker != worker:
            return False
        now = time.time()
        with self._lock:
            self._conn.execute(
                "UPDATE tasks SET heartbeat_at=?, updated_at=? WHERE id=?",
                (now, now, t.id))
            self._conn.commit()
        return True

    # ─── zombie detection ─────────────────────────────────────
    def reclaim_zombies(self, *, now: Optional[float] = None) -> list[str]:
        """Move InProgress tasks whose heartbeat is older than ttl_s back to Triage.

        Returns the list of reclaimed task ids. Increments ``retries_used`` and
        appends a note explaining why."""
        now = now if now is not None else time.time()
        reclaimed: list[str] = []
        for t in self.list(column="InProgress"):
            stale = (t.heartbeat_at or t.started_at or t.updated_at)
            if not stale:
                continue
            if now - stale > t.ttl_s:
                gone_for = int(now - stale)
                self.transition(
                    t.id, to="Triage",
                    note=f"zombie reclaim: worker {t.worker!r} silent for {gone_for}s (ttl={t.ttl_s}s)",
                )
                reclaimed.append(t.id)
        return reclaimed

    # ─── hallucination gate at completion ────────────────────
    def complete(self, task_id: str, *, claim: dict[str, Any],
                 belief_state: dict[str, Any]) -> CompletionGateResult:
        """Worker reports done. Run the hallucination gate.

        ``claim`` is the worker's stated outcomes (e.g. ``{"verified": True}``).
        ``belief_state`` is the agent's actual Belief snapshot at completion.
        Every declared postcondition is checked against ``belief_state``;
        every claim is checked against ``belief_state`` for contradictions.

        On accept (all postconditions hold + no claim contradicts state):
          transition → Done.
        On reject:
          transition → Triage with gate findings appended to notes; the next
          worker sees the prior attempt and why it bounced.

        If retries exhausted (``retries_used >= retry_budget``) the task
        goes to ``Blocked`` instead of ``Triage`` so a human can intervene.
        """
        t = self.get(task_id)
        if not t:
            raise TaskBoardError(f"no task {task_id}")
        if t.column != "InProgress":
            raise TaskBoardError(f"task {task_id} not InProgress (column={t.column})")

        belief_state = belief_state or {}
        claim = claim or {}

        matched: list[str] = []
        missing: list[str] = []
        for pc in t.postconditions:
            if _condition_holds(pc, belief_state):
                matched.append(pc)
            else:
                missing.append(pc)

        contradicting: list[str] = []
        for k, v in claim.items():
            bv = belief_state.get(k)
            if v and not bv:
                contradicting.append(f"claim['{k}']={v!r} but belief['{k}']={bv!r}")
            if (v is False) and bv:
                contradicting.append(f"claim['{k}']=False but belief['{k}']={bv!r}")

        accepted = (not missing) and (not contradicting)

        if accepted:
            self.transition(task_id, to="Done",
                            note=f"completion gate ✓ — {len(matched)} postconditions matched")
        else:
            next_col = "Blocked" if (t.retries_used + 1) >= t.retry_budget else "Triage"
            findings: list[str] = []
            if missing:
                findings.append("missing postconditions: " + ", ".join(missing))
            if contradicting:
                findings.append("contradicting claims: " + "; ".join(contradicting))
            self.transition(task_id, to=next_col,
                            note=f"hallucination gate ✗ — {' | '.join(findings)}")

        return CompletionGateResult(
            accepted=accepted,
            matched_postconditions=matched,
            missing_postconditions=missing,
            contradicting_claims=contradicting,
        )

    # ─── reporting ────────────────────────────────────────────
    def stats(self) -> dict:
        """Counts by column + last-heartbeat lag. For /insight/mastermind/board."""
        out: dict = {"columns": {}, "now": time.time()}
        with self._lock:
            for c in COLUMNS:
                n = self._conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE column_name=?", (c,)
                ).fetchone()[0]
                out["columns"][c] = int(n)
            zombies = 0
            now = time.time()
            for t in self.list(column="InProgress"):
                stale = t.heartbeat_at or t.started_at or t.updated_at
                if stale and (now - stale) > t.ttl_s:
                    zombies += 1
            out["zombies"] = zombies
            out["total"] = self._conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        return out

    # ─── cleanup ──────────────────────────────────────────────
    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass


def _condition_holds(condition: str, belief_state: dict) -> bool:
    """Lightweight evaluator for postcondition strings.

    Supported forms:
      * ``belief.key=true``   → ``bool(belief_state.get('key'))`` is True
      * ``belief.key=false``  → ``bool(belief_state.get('key'))`` is False
      * ``belief.key``        → truthy presence check
      * ``key``               → truthy presence check (bare keys)

    Anything else: treat as a bare key and return truthy-presence. Future
    iterations can layer a richer expression language."""
    cond = (condition or "").strip()
    if not cond:
        return False
    key = cond
    expected: Optional[bool] = None
    if "=" in cond:
        key, _, raw_val = cond.partition("=")
        key = key.strip()
        val = raw_val.strip().lower()
        if val in ("true", "1", "yes"):
            expected = True
        elif val in ("false", "0", "no"):
            expected = False
    if key.startswith("belief."):
        key = key[len("belief."):]
    actual = bool(belief_state.get(key))
    return actual if expected is None else (actual == expected)


__all__ = [
    "TaskBoard", "Task", "CompletionGateResult", "TaskBoardError",
    "COLUMNS", "DEFAULT_TTL_S",
]
