# Portions adapted from confident-ai/deepeval (Apache-2.0). See NOTICE.
"""
GEval — criteria-based LLM-as-judge metric for mindX.

Algorithm follows Liu et al. 2023 (arXiv:2303.16634), implemented in
the shape of deepeval/metrics/g_eval/g_eval.py with these mindX-specific
adaptations:

  - Async-only (a_measure). No sync measure().
  - Judge LLM goes through MindXJudgeLLM → llm/llm_factory.
  - JSON parsing is permissive (small CPU-pillar models often wrap
    output in code fences); see metrics_utils.trim_and_load_json.
  - Log-probability reweighting is a stub today (Ollama doesn't
    expose top_logprobs the OpenAI shape). The integer score is used
    directly. The hook is in place for cloud judges later.
  - No pytest harness, no Confident-AI cloud upload, no tracing.

Score normalization: (raw_score - score_range[0]) / score_range_span,
landing in [0, 1] for the BaseMetric contract.
"""
from __future__ import annotations

import logging
import textwrap
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .base import BaseMetric
from .llm_adapter import MindXJudgeLLM
from .metrics_utils import trim_and_load_json
from .test_case import G_EVAL_PARAM_NAMES, LLMTestCase, SingleTurnParams

logger = logging.getLogger(__name__)


@dataclass
class Rubric:
    """Mapping a sub-range of the score scale to an expected outcome description."""
    score_range: Tuple[int, int]
    expected_outcome: str

    def __post_init__(self) -> None:
        s, e = self.score_range
        if not (0 <= s <= 10 and 0 <= e <= 10):
            raise ValueError("Rubric score_range values must be between 0 and 10 inclusive")
        if s > e:
            raise ValueError("Rubric score_range start must be <= end")


# ── Prompt templates (adapted from deepeval/metrics/g_eval/template.py) ──

def _build_steps_prompt(criteria: str, parameters: str) -> str:
    return textwrap.dedent(
        f"""\
        Given an evaluation criteria which outlines how you should judge the {parameters}, generate 3-4 concise evaluation steps based on the criteria below. You MUST make it clear how to evaluate {parameters} in relation to one another.

        Evaluation Criteria:
        {criteria}

        **
        IMPORTANT: Please make sure to only return in JSON format, with the "steps" key as a list of strings. No words or explanation is needed.
        Example JSON:
        {{
            "steps": ["step one", "step two", "step three"]
        }}
        **

        JSON:
        """
    )


def _build_results_prompt(
    evaluation_steps_numbered: str,
    test_case_content: str,
    parameters: str,
    rubric_str: Optional[str],
    score_range: Tuple[int, int],
) -> str:
    rubric_text = f"Rubric:\n{rubric_str}\n" if rubric_str else ""
    dependencies = "evaluation steps and rubric" if rubric_str else "evaluation steps"
    score_explanation = (
        "based on the rubric provided"
        if rubric_str
        else f"with {score_range[1]} indicating strong alignment with the evaluation steps and {score_range[0]} indicating no alignment"
    )
    reasoning_expectation = (
        "Be specific and grounded in the evaluation steps and rubric."
        if rubric_str
        else "Be specific and grounded in the evaluation steps."
    )
    return textwrap.dedent(
        f"""\
        You are an evaluator. Given the following {dependencies}, assess the response below and return a JSON object with two fields:

        - `"score"`: an integer between {score_range[0]} and {score_range[1]}, {score_explanation}.
        - `"reason"`: a brief explanation for why the score was given. This must mention specific strengths or shortcomings, referencing relevant details from the input. Do **not** quote the score itself in the explanation.

        Your explanation should:
        - {reasoning_expectation}
        - Mention key details from the test case parameters.
        - Be concise, clear, and focused on the evaluation logic.

        Only return valid JSON. Do **not** include any extra commentary or text.

        ---

        Evaluation Steps:
        {evaluation_steps_numbered}

        {rubric_text}
        Test Case:
        {test_case_content}

        Parameters:
        {parameters}

        ---
        **Example JSON:**
        {{
            "reason": "your concise and informative reason here",
            "score": {score_range[0]}
        }}

        JSON:
        """
    )


# ── Helpers ────────────────────────────────────────────────────────────

def _params_phrase(params: List[SingleTurnParams]) -> str:
    names = [G_EVAL_PARAM_NAMES[p] for p in params]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + ", and " + names[-1]


def _test_case_content(params: List[SingleTurnParams], tc: LLMTestCase) -> str:
    body = ""
    for param in params:
        value = getattr(tc, param.value, None)
        body += f"{G_EVAL_PARAM_NAMES[param]}:\n{value}\n\n"
    return body


def _format_rubrics(rubrics: Optional[List[Rubric]]) -> Optional[str]:
    if not rubrics:
        return None
    lines = []
    for r in rubrics:
        s, e = r.score_range
        if s == e:
            lines.append(f"{s}: {r.expected_outcome}")
        else:
            lines.append(f"{s}-{e}: {r.expected_outcome}")
    return "\n".join(lines)


def _validate_and_sort_rubrics(rubrics: Optional[List[Rubric]]) -> Optional[List[Rubric]]:
    if not rubrics:
        return None
    s = sorted(rubrics, key=lambda r: r.score_range[0])
    for i in range(len(s)):
        a_end = s[i].score_range[1]
        for j in range(i + 1, len(s)):
            if a_end >= s[j].score_range[0]:
                raise ValueError(
                    f"Overlapping rubric ranges: {s[i].score_range} and {s[j].score_range}"
                )
    return s


def _score_range_from_rubrics(rubrics: Optional[List[Rubric]]) -> Tuple[int, int]:
    if not rubrics:
        return (0, 10)
    return rubrics[0].score_range[0], rubrics[-1].score_range[1]


def _number_steps(steps: List[str]) -> str:
    return "".join(f"{i}. {s}\n" for i, s in enumerate(steps, start=1))


# ── GEval ──────────────────────────────────────────────────────────────

class GEval(BaseMetric):
    """LLM-as-judge metric over user-supplied criteria.

    Args:
        name: Human-readable name (used in catalogue + logs).
        criteria: Plain-English description of what makes a good output.
                  Either `criteria` or `evaluation_steps` must be supplied.
        evaluation_steps: If given, skips auto-generation. List of 3-5
                          concrete checks the judge applies.
        evaluation_params: Which LLMTestCase fields the judge sees.
                           Defaults to [INPUT, ACTUAL_OUTPUT].
        rubric: Optional list of (score_range, outcome_description).
                If omitted, a 0-10 numeric scale is used.
        threshold: Score in [0, 1] above which is_successful() returns True.
        judge: Optional MindXJudgeLLM. If omitted, default CPU-pillar judge.
    """

    def __init__(
        self,
        name: str,
        criteria: Optional[str] = None,
        evaluation_steps: Optional[List[str]] = None,
        evaluation_params: Optional[List[SingleTurnParams]] = None,
        rubric: Optional[List[Rubric]] = None,
        threshold: float = 0.5,
        judge: Optional[MindXJudgeLLM] = None,
        verbose: bool = False,
    ) -> None:
        if criteria is None and evaluation_steps is None:
            raise ValueError("Either 'criteria' or 'evaluation_steps' must be provided.")
        if criteria is not None and not criteria.strip():
            raise ValueError("'criteria' cannot be empty.")
        if evaluation_steps is not None and len(evaluation_steps) == 0:
            raise ValueError("'evaluation_steps' must be a non-empty list when provided.")

        self.name = name
        self.criteria = criteria
        self.evaluation_steps = list(evaluation_steps) if evaluation_steps else None
        self.evaluation_params = evaluation_params or [
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
        ]
        self.rubric = _validate_and_sort_rubrics(rubric)
        self.score_range = _score_range_from_rubrics(self.rubric)
        self.score_range_span = self.score_range[1] - self.score_range[0] or 1
        self.threshold = threshold
        self.judge = judge or MindXJudgeLLM()
        self.evaluation_model = self.judge.get_model_name()
        self.verbose_mode = verbose

    @property
    def __name__(self) -> str:
        return f"{self.name} [GEval]"

    async def a_measure(self, test_case: LLMTestCase, **kwargs) -> float:
        try:
            if self.evaluation_steps is None:
                self.evaluation_steps = await self._generate_steps()
            score, reason = await self._evaluate(test_case)
            normalized = (float(score) - self.score_range[0]) / self.score_range_span
            normalized = max(0.0, min(1.0, normalized))
            self.score = normalized
            self.reason = reason
            self.success = normalized >= self.threshold
            self.error = None
            return normalized
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            self.score = None
            self.reason = None
            self.success = False
            logger.warning("GEval a_measure failed: %s", self.error)
            raise

    async def _generate_steps(self) -> List[str]:
        if not self.criteria:
            raise ValueError("Cannot auto-generate steps without criteria")
        params_phrase = _params_phrase(self.evaluation_params)
        prompt = _build_steps_prompt(self.criteria, params_phrase)
        text = await self.judge.a_generate(prompt, json_mode=True)
        data = trim_and_load_json(text)
        steps = data.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError(f"Judge returned no steps: {data!r}")
        return [str(s) for s in steps]

    async def _evaluate(self, test_case: LLMTestCase) -> Tuple[float, str]:
        params_phrase = _params_phrase(self.evaluation_params)
        prompt = _build_results_prompt(
            evaluation_steps_numbered=_number_steps(self.evaluation_steps or []),
            test_case_content=_test_case_content(self.evaluation_params, test_case),
            parameters=params_phrase,
            rubric_str=_format_rubrics(self.rubric),
            score_range=self.score_range,
        )
        text, _logprobs = await self.judge.a_generate_with_logprobs(prompt)
        data = trim_and_load_json(text)
        if "score" not in data or "reason" not in data:
            raise ValueError(f"Judge response missing score/reason: {data!r}")
        try:
            score = float(data["score"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Judge score is not numeric: {data['score']!r} ({exc})")
        reason = str(data["reason"])
        return score, reason
