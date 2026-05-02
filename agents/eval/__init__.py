# Portions adapted from confident-ai/deepeval (Apache-2.0). See NOTICE.
"""
mindX evaluation framework — GEval-style criteria-based scoring of
LLM outputs, wired through mindX's llm_factory.

Public surface:
  GEval, BaseMetric, LLMTestCase, SingleTurnParams, Rubric, MindXJudgeLLM

Default judge: CPU-pillar Ollama (qwen3:1.7b on localhost:11434), free.
Override via MINDX_EVAL_JUDGE_PROVIDER and MINDX_EVAL_JUDGE_MODEL env
vars or by passing a custom MindXJudgeLLM to a metric constructor.

See agents/eval/README.md for usage and the cost model.
See agents/eval/NOTICE for upstream attribution.
"""
from .base import BaseMetric
from .g_eval import GEval, Rubric
from .llm_adapter import MindXJudgeLLM
from .test_case import G_EVAL_PARAM_NAMES, LLMTestCase, SingleTurnParams

__all__ = [
    "BaseMetric",
    "GEval",
    "G_EVAL_PARAM_NAMES",
    "LLMTestCase",
    "MindXJudgeLLM",
    "Rubric",
    "SingleTurnParams",
]
