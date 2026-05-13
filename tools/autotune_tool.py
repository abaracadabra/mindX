# tools/autotune_tool.py
"""AutotuneTool — thin BaseTool wrapper around the agnostic `autotune` package.

Lets BDI / mastermind / the dream cycle run the ahead-of-time tuner and get a
reproducible `AutotunePlan` back (attention backend, GEMM heuristic, collective
topology) for whatever box mindX is running on. The heavy lifting lives in the
standalone `autotune/` package; this file is just the agent-facing surface.

Actions:
  * ``dry_run``  — return the per-vendor reference plan (no GPU touched). Default.
  * ``bench``    — run the real probe on ``device_index`` (falls back to the
                   reference plan automatically when no GPU/torch is present).
  * ``detect``   — return just the detected ``HardwareProfile``.

Pass ``out_path`` to also write the plan JSON to disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from agents.core.bdi_agent import BaseTool
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)


class AutotuneTool(BaseTool):
    """Agnostic ahead-of-time tuner: probes hardware, emits an AutotunePlan."""

    def __init__(
        self,
        config: Optional[Config] = None,
        llm_handler: Optional[Any] = None,
        bdi_agent_ref: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(config=config, llm_handler=llm_handler, bdi_agent_ref=bdi_agent_ref, **kwargs)

    async def execute(
        self,
        action: str = "dry_run",
        device_index: int = 0,
        out_path: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            from autotune import detect_hardware, run_autotune
        except Exception as e:  # pragma: no cover - autotune is in-repo, shouldn't happen
            return {"status": "ERROR", "message": f"autotune package unavailable: {e}"}

        action = (action or "dry_run").lower()
        try:
            if action == "detect":
                profile = detect_hardware(device_index)
                result = profile.model_dump()
            else:
                plan = run_autotune(device_index=device_index, dry_run=(action != "bench"))
                result = plan.model_dump()
                if out_path:
                    p = Path(out_path)
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(json.dumps(result, indent=2))
                    result["_written_to"] = str(p)
        except RuntimeError as e:
            # e.g. unsafe 2/4-GPU AMD collective topology — surface, don't crash.
            return {"status": "ERROR", "action": action, "message": str(e)}
        except Exception as e:
            self.logger.error(f"AutotuneTool {action} failed: {e}", exc_info=True)
            return {"status": "ERROR", "action": action, "message": str(e)}

        return {"status": "SUCCESS", "action": action, "result": result}

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "autotune",
            "description": (
                "Agnostic ahead-of-time tuner. Runs a short pre-flight micro-benchmark and "
                "returns a reproducible AutotunePlan (attention backend, GEMM heuristic, "
                "collective topology) for the current hardware (AMD/ROCm, NVIDIA/CUDA, or CPU)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["dry_run", "bench", "detect"],
                        "default": "dry_run",
                        "description": "dry_run = reference plan (no GPU); bench = real probe; detect = HardwareProfile only.",
                    },
                    "device_index": {"type": "integer", "default": 0, "description": "GPU/HIP device index."},
                    "out_path": {"type": "string", "description": "Optional path to write the plan JSON to."},
                },
                "required": [],
            },
        }
