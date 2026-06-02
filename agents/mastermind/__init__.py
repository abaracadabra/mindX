# SPDX-License-Identifier: Apache-2.0
"""MASTERMIND-adjacent substrate.

Pieces that belong conceptually to the MASTERMIND orchestrator but ship as
small, independently-testable modules so they can be wired in without
touching the existing ``agents/orchestration/mastermind_agent.py`` hot path.
"""
from agents.mastermind.taskboard import (
    COLUMNS,
    DEFAULT_TTL_S,
    CompletionGateResult,
    Task,
    TaskBoard,
    TaskBoardError,
)

__all__ = [
    "TaskBoard",
    "Task",
    "CompletionGateResult",
    "TaskBoardError",
    "COLUMNS",
    "DEFAULT_TTL_S",
]
