# Portions adapted from confident-ai/deepeval (Apache-2.0). See NOTICE.
"""
LLMTestCase — input contract for mindX evaluation metrics.

A slim subset of deepeval/test_case/llm_test_case.py. Drops MCP,
multimodal, tool-call, dataset, and conversational machinery that
mindX does not need for Phase 1. Keeps the field shape that the
GEval prompt builder reads from.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class SingleTurnParams(str, Enum):
    """Which fields of an LLMTestCase the metric should expose to the judge.

    Mirrors deepeval's SingleTurnParams. The string values match LLMTestCase
    attribute names so getattr(test_case, param.value) returns the field.
    """
    INPUT = "input"
    ACTUAL_OUTPUT = "actual_output"
    EXPECTED_OUTPUT = "expected_output"
    CONTEXT = "context"
    RETRIEVAL_CONTEXT = "retrieval_context"
    METADATA = "metadata"


# Display-name mapping for the judge prompt (matches upstream G_EVAL_PARAMS).
G_EVAL_PARAM_NAMES: Dict[SingleTurnParams, str] = {
    SingleTurnParams.INPUT: "Input",
    SingleTurnParams.ACTUAL_OUTPUT: "Actual Output",
    SingleTurnParams.EXPECTED_OUTPUT: "Expected Output",
    SingleTurnParams.CONTEXT: "Context",
    SingleTurnParams.RETRIEVAL_CONTEXT: "Retrieval Context",
    SingleTurnParams.METADATA: "Metadata",
}


@dataclass
class LLMTestCase:
    input: str
    actual_output: Optional[str] = None
    expected_output: Optional[str] = None
    context: Optional[List[str]] = None
    retrieval_context: Optional[List[str]] = None
    metadata: Optional[Dict] = None
    name: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.input, str):
            raise TypeError("'input' must be a string")
        if self.actual_output is not None and not isinstance(self.actual_output, str):
            raise TypeError("'actual_output' must be a string")
        if self.context is not None and not all(isinstance(c, str) for c in self.context):
            raise TypeError("'context' must be a list of strings")
        if self.retrieval_context is not None and not all(
            isinstance(c, str) for c in self.retrieval_context
        ):
            raise TypeError("'retrieval_context' must be a list of strings")
