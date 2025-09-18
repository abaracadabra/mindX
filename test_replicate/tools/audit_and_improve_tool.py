# mindx/tools/audit_and_improve_tool.py
"""
A tool for auditing and improving code, using a BaseGenAgent summary as context,
with a fallback to raw code for resilience.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

from core.bdi_agent import BaseTool
from llm.llm_interface import LLMHandlerInterface
from utils.config import Config
from agents.memory_agent import MemoryAgent
from agents.automindx_agent import AutoMINDXAgent
from .base_gen_agent import BaseGenAgent

class AuditAndImproveTool(BaseTool):
    """
    A tool for auditing and improving code, using a BaseGenAgent summary as context,
    with a fallback to raw code for resilience.
    """

    def __init__(self, memory_agent: MemoryAgent, base_gen_agent: BaseGenAgent, automindx_agent: AutoMINDXAgent, config: Optional[Config] = None, llm_handler: Optional[LLMHandlerInterface] = None, **kwargs):
        super().__init__(config=config, llm_handler=llm_handler, **kwargs)
        self.memory_agent = memory_agent
        self.base_gen_agent = base_gen_agent
        self.automindx_agent = automindx_agent
        if not self.llm_handler:
            raise ValueError("AuditAndImproveTool requires an LLMHandler.")

    async def execute(self, target_path: str, prompt: str) -> Dict[str, Any]:
        """
        Audits and improves the code at the given path using a resilient, multi-step process.
        """
        workspace_dir = self.memory_agent.get_agent_data_directory("audit_and_improve_tool")
        context_content = ""
        context_source = ""
        status_details = "OK" # New variable to track operational status

        # Step 1: Attempt to generate and use a documentation snapshot as the primary context.
        try:
            self.logger.info(f"Attempting to generate BaseGen summary for {target_path}")
            summary_report = self.base_gen_agent.generate_markdown_summary(
                root_path_str=target_path,
                output_file_str=str(workspace_dir / f"analysis_context_{Path(target_path).name}.md")
            )
            if summary_report["status"] != "SUCCESS":
                raise ValueError(f"BaseGenAgent failed: {summary_report['message']}")
            
            summary_file_path = Path(summary_report["output_file"])
            with open(summary_file_path, "r", encoding="utf-8") as f:
                context_content = f.read()
            context_source = f"BaseGen Summary: {summary_file_path.name}"
            self.logger.info(f"Successfully used BaseGen summary as context.")

        except Exception as e:
            # Step 2: Fallback to using raw file content if BaseGen fails.
            self.logger.warning(f"BaseGen step failed ('{e}'). Falling back to raw file content for resilience.")
            status_details = "DEGRADED_CONTEXT_FALLBACK" # Update status
            path = Path(target_path)
            if not path.exists() or path.is_dir():
                return {"status": "ERROR", "message": f"Target path does not exist or is a directory: {target_path}"}
            try:
                with open(path, "r", encoding="utf-8") as f:
                    context_content = f.read()
                context_source = f"Raw File Content (Fallback): {path.name}"
            except Exception as read_e:
                return {"status": "ERROR", "message": f"Fallback failed: Could not read raw file '{target_path}': {read_e}"}

        # Step 3: Use the acquired context and the persona from AutoMINDX to generate the improvement.
        persona = self.automindx_agent.get_persona("AUDIT_AND_IMPROVE")
        if not persona:
            return {"status": "ERROR", "message": "Could not retrieve AUDIT_AND_IMPROVE persona from AutoMINDX."}

        full_prompt = (
            f"{persona}\n\n"
            f"**Improvement Request:** {prompt}\n\n"
            f"**Context from {context_source}:**\n```\n{context_content}\n```"
        )

        # Step 4: Generate and save the improved code.
        try:
            response_str = await self.llm_handler.generate_text(full_prompt, json_mode=True)
            response_data = json.loads(response_str)

            updated_code = response_data.get("updated_code")
            summary = response_data.get("summary")
            limitations = response_data.get("limitations")

            if not updated_code:
                return {"status": "ERROR", "message": "LLM did not provide updated code."}

            output_path = workspace_dir / f"improved_{Path(target_path).name}"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(updated_code)

            # Step 5: Log the successful operation.
            log_data = {
                "target_path": target_path,
                "prompt": prompt,
                "summary": summary,
                "limitations": limitations,
                "context_source": context_source,
                "output_path": str(output_path)
            }
            await self.memory_agent.log_process("audit_and_improve_tool_execution", log_data, {"agent_id": "audit_and_improve_tool"})

            return {
                "status": "SUCCESS",
                "status_details": status_details, # Include the operational status
                "summary": summary,
                "limitations": limitations,
                "output_path": str(output_path),
                "context_used": context_source
            }
        except Exception as e:
            return {"status": "ERROR", "message": f"An error occurred during the LLM improvement step: {e}"}
