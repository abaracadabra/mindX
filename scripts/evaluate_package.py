#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""evaluate_package.py — drive a sandboxed external package through the
SimpleCoder audit + Strategic Evolution Agent (SEA) adoption decision.

Flow (reusable for ANY package, not just LLMFIT):

    1. SimpleCoderAgent.execute("audit_package", archive=...) — safely inspect,
       extract (zip-bomb guarded) and statically scan the package in its sandbox.
    2. SEA.evaluate_external_package_adoption(...) — LLM-reasoned ADOPT/REJECT/DEFER
       with rationale, logged as a Gödel choice + belief. On ADOPT (and unless
       --no-stage) the audited members are staged into the live tree.

Usage:
    python scripts/evaluate_package.py                         # LLMFIT.zip, decision-only
    python scripts/evaluate_package.py --stage                 # ADOPT -> stage into tree
    python scripts/evaluate_package.py projects/Foo.zip --stage

The staging map (extracted member -> live destination) is derived from the
package's own descriptor where possible; for LLMFIT it is the known 4-file layout.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.simple_coder_agent import SimpleCoderAgent
from agents.learning.strategic_evolution_agent import StrategicEvolutionAgent
from agents.memory_agent import MemoryAgent
from agents.core.belief_system import BeliefSystem
from agents.orchestration.coordinator_agent import get_coordinator_agent_mindx_async
from llm.model_registry import get_model_registry_async
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Known staging layout for the LLMFIT package (matches its advisor.agent +
# container + hook contract). Other packages fall back to a heuristic below.
LLMFIT_TARGETS = {
    "llmfit_tool.py": "tools/inference/llmfit_tool.py",
    "llmfit.advisor.agent": "agents/llmfit.advisor.agent",
    "llmfit.container": "tools/inference/llmfit.container",
    "inference_discovery_llmfit_hook.py": "llm/inference_discovery_llmfit_hook.py",
}


def derive_targets(package_name: str, audit_summary: dict) -> dict:
    """Map each extracted member to a live destination."""
    if package_name == "llmfit":
        return dict(LLMFIT_TARGETS)
    # Generic heuristic: .agent files -> agents/, everything else -> tools/<pkg>/.
    targets = {}
    for f in audit_summary.get("files", []):
        name = f["name"]
        if name.endswith(".agent"):
            targets[name] = f"agents/{name}"
        else:
            targets[name] = f"tools/{package_name}/{name}"
    return targets


async def main() -> int:
    ap = argparse.ArgumentParser(description="Audit + adopt-decide an external package.")
    ap.add_argument("archive", nargs="?", default="projects/LLMFIT.zip",
                    help="sandbox-relative path to the package zip (default: projects/LLMFIT.zip)")
    ap.add_argument("--stage", action="store_true",
                    help="on ADOPT, stage the audited files into the live tree")
    ap.add_argument("--context", default="Node-capability-aware inference routing for mindX.",
                    help="narrative context handed to SEA's reasoning prompt")
    args = ap.parse_args()

    config = Config()

    # ── Step 1: SimpleCoder audits + extracts the package (sandboxed) ────────
    coder = SimpleCoderAgent()
    print(f"\n[1/2] SimpleCoder auditing {args.archive} …")
    audit = await coder.execute("audit_package", archive=args.archive)
    if audit.get("status") != "SUCCESS":
        print("AUDIT FAILED:", json.dumps(audit, indent=2, default=str))
        return 1
    summary = audit["audit_summary"]
    print(f"      package={summary['package_name']} members={summary['member_count']} "
          f"aggregate_risk={summary['aggregate_risk']} sev={summary['severity_counts']}")
    print(f"      license={summary['declared_license']}")
    print(f"      deps={summary['declared_dependencies']}")

    # ── Step 2: SEA renders the adoption decision ────────────────────────────
    print("\n[2/2] Wiring SEA and rendering adoption decision …")
    memory_agent = MemoryAgent(config=config)
    belief_system = BeliefSystem()
    model_registry = await get_model_registry_async(config=config)
    coordinator = await get_coordinator_agent_mindx_async(
        config_override=config, memory_agent=memory_agent, belief_system=belief_system,
    )
    sea = StrategicEvolutionAgent(
        agent_id="strategic_evolution_agent",
        belief_system=belief_system,
        coordinator_agent=coordinator,
        model_registry=model_registry,
        memory_agent=memory_agent,
        config_override=config,
    )
    await sea._async_init()

    targets = derive_targets(summary["package_name"], summary)
    decision = await sea.evaluate_external_package_adoption(
        package_name=summary["package_name"],
        audit_summary=summary,
        proposed_targets=targets,
        campaign_context=args.context,
        stage_on_adopt=args.stage,
    )

    print("\n" + "=" * 70)
    print(f"  SEA DECISION: {decision['decision']}  (confidence {decision['confidence']:.2f})")
    print("=" * 70)
    print(f"  rationale: {decision['rationale']}")
    if decision.get("validation_plan"):
        print("  validation plan:")
        for step in decision["validation_plan"]:
            print(f"    - {step}")
    print(f"  godel_logged: {decision['godel_logged']}  cycle_id: {decision['cycle_id']}")
    if decision.get("staged_files"):
        print("  staged files:")
        for s in decision["staged_files"]:
            print(f"    - {s.get('member')} -> {s.get('destination')} [{s.get('status')}]")
    elif args.stage and decision["decision"] != "ADOPT":
        print("  (no staging — decision was not ADOPT)")
    elif not args.stage:
        print("  (decision-only run; re-run with --stage to wire an ADOPT into the tree)")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
