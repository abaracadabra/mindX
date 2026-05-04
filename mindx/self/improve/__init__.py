"""mindx.self.improve — self-improvement primitives."""

from mindx.self.improve.model_selector import (
    ModelSelector,
    ModelChoice,
    TaskProfile,
    ScoredCandidate,
)

__all__ = ["ModelSelector", "ModelChoice", "TaskProfile", "ScoredCandidate"]


async def choose_model(task_profile: "TaskProfile") -> "ModelChoice":
    """Top-level convenience — `from mindx.self.improve import choose_model`.

    Lazy-instantiates a process-singleton ModelSelector. For per-call control
    (custom Aware, custom config paths), instantiate ModelSelector directly.
    """
    selector = await ModelSelector.get_instance()
    return await selector.choose_model(task_profile)
