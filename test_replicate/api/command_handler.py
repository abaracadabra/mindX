# mindx/orchestration/api/command_handler.py

import json
from typing import Dict, Any, Optional

from orchestration.mastermind_agent import MastermindAgent
from orchestration.coordinator_agent import InteractionType

class CommandHandler:
    def __init__(self, mastermind: MastermindAgent):
        self.mastermind = mastermind

    async def handle_evolve(self, directive: str) -> Dict[str, Any]:
        return await self.mastermind.manage_mindx_evolution(top_level_directive=directive)

    async def handle_deploy(self, directive: str) -> Dict[str, Any]:
        return await self.mastermind.manage_agent_deployment(top_level_directive=directive)

    async def handle_introspect(self, role_description: str) -> str:
        if not self.mastermind.automindx_agent:
            return "Error: AutoMINDX agent is not available."
        return await self.mastermind.automindx_agent.generate_new_persona(role_description)

    async def handle_mastermind_status(self) -> Dict[str, Any]:
        return {"status": "Not implemented"}

    async def handle_show_agent_registry(self) -> Dict[str, Any]:
        if self.mastermind.coordinator_agent:
            return self.mastermind.coordinator_agent.agent_registry
        return {"error": "Coordinator agent not available."}

    async def handle_show_tool_registry(self) -> Dict[str, Any]:
        return self.mastermind.bdi_agent.tools_registry

    async def handle_analyze_codebase(self, path: str, focus: str) -> Dict[str, Any]:
        directive = f"Analyze codebase at '{path}' focusing on '{focus}', and store results. Then, assess tool suite based on new findings."
        return await self.mastermind.manage_mindx_evolution(top_level_directive=directive)

    async def handle_basegen(self, path: str) -> Dict[str, Any]:
        if not self.mastermind.code_base_analyzer:
            return {"error": "Mastermind's CodeBaseGenerator (BaseGenAgent) is not available."}
        return await self.mastermind.code_base_analyzer.generate_markdown_summary(root_path_str=path)

    async def handle_id_list(self) -> Dict[str, Any]:
        if not self.mastermind.id_manager_agent:
            return {"error": "Mastermind's IDManagerAgent is not available."}
        return await self.mastermind.id_manager_agent.list_managed_identities()

    async def handle_id_create(self, entity_id: str) -> Dict[str, Any]:
        if not self.mastermind.id_manager_agent:
            return {"error": "Mastermind's IDManagerAgent is not available."}
        public_address, env_var_name = await self.mastermind.id_manager_agent.create_new_wallet(entity_id=entity_id)
        return {"public_address": public_address, "env_var_name": env_var_name}

    async def handle_id_deprecate(self, public_address: str, entity_id_hint: Optional[str] = None) -> Dict[str, Any]:
        if not self.mastermind.id_manager_agent:
            return {"error": "Mastermind's IDManagerAgent is not available."}
        success = self.mastermind.id_manager_agent.deprecate_identity(public_address=public_address, entity_id_hint=entity_id_hint)
        return {"success": success}

    async def handle_audit_gemini(self, test_all: bool, update_config: bool) -> Dict[str, Any]:
        from scripts import audit_gemini
        if test_all:
            return await audit_gemini.main(["--test-all"])
        elif update_config:
            return await audit_gemini.main(["--update-config"])
        else:
            return {"error": "audit_gemini requires either --test-all or --update-config argument."}

    async def handle_coord_query(self, query: str) -> Dict[str, Any]:
        if not self.mastermind.coordinator_agent:
            return {"error": "Coordinator agent not available."}
        content = f"Query for mindX Coordinator (Augmentic Intelligence): {query}"
        return await self.mastermind.coordinator_agent.handle_user_input(content=content, user_id="api_user", interaction_type=InteractionType.QUERY)

    async def handle_coord_analyze(self, context: Optional[str] = None) -> Dict[str, Any]:
        if not self.mastermind.coordinator_agent:
            return {"error": "Coordinator agent not available."}
        content = "System analysis of mindX requested via API."
        metadata = {"api_source_command": "coord_analyze"}
        if context:
            metadata["analysis_context"] = f"mindX analysis context: {context}"
        return await self.mastermind.coordinator_agent.handle_user_input(content=content, user_id="api_user", interaction_type=InteractionType.SYSTEM_ANALYSIS, metadata=metadata)

    async def handle_coord_improve(self, component_id: str, context: Optional[str] = None) -> Dict[str, Any]:
        if not self.mastermind.coordinator_agent:
            return {"error": "Coordinator agent not available."}
        metadata = {"target_component": component_id}
        content = f"API Request: Improve component {component_id}"
        if context:
            metadata["analysis_context"] = context
        return await self.mastermind.coordinator_agent.handle_user_input(content=content, user_id="api_user", interaction_type=InteractionType.COMPONENT_IMPROVEMENT, metadata=metadata)

    async def handle_coord_backlog(self) -> Dict[str, Any]:
        if not self.mastermind.coordinator_agent:
            return {"error": "Coordinator agent not available."}
        return self.mastermind.coordinator_agent.improvement_backlog

    async def handle_coord_process_backlog(self) -> Dict[str, Any]:
        if not self.mastermind.coordinator_agent:
            return {"error": "Coordinator agent not available."}
        return await self.mastermind.coordinator_agent.process_backlog_item()

    async def handle_coord_approve(self, backlog_item_id: str) -> Dict[str, Any]:
        if not self.mastermind.coordinator_agent:
            return {"error": "Coordinator agent not available."}
        metadata = {"backlog_item_id": backlog_item_id}
        content = f"API Request: Approve backlog item {backlog_item_id}"
        return await self.mastermind.coordinator_agent.handle_user_input(content=content, user_id="api_user", interaction_type=InteractionType.APPROVE_IMPROVEMENT, metadata=metadata)

    async def handle_coord_reject(self, backlog_item_id: str) -> Dict[str, Any]:
        if not self.mastermind.coordinator_agent:
            return {"error": "Coordinator agent not available."}
        metadata = {"backlog_item_id": backlog_item_id}
        content = f"API Request: Reject backlog item {backlog_item_id}"
        return await self.mastermind.coordinator_agent.handle_user_input(content=content, user_id="api_user", interaction_type=InteractionType.REJECT_IMPROVEMENT, metadata=metadata)

    async def handle_agent_create(self, agent_type: str, agent_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        return await self.mastermind.bdi_agent._internal_action_handlers["CREATE_AGENT"]({"params": {"agent_type": agent_type, "agent_id": agent_id, "config": config}})

    async def handle_agent_delete(self, agent_id: str) -> Dict[str, Any]:
        return await self.mastermind.bdi_agent._internal_action_handlers["DELETE_AGENT"]({"params": {"agent_id": agent_id}})

    async def handle_agent_list(self) -> Dict[str, Any]:
        if self.mastermind.coordinator_agent:
            return self.mastermind.coordinator_agent.agent_registry
        return {"error": "Coordinator agent not available."}

    async def handle_agent_evolve(self, agent_id: str, directive: str) -> Dict[str, Any]:
        return await self.mastermind.bdi_agent._internal_action_handlers["EVOLVE_AGENT"]({"params": {"agent_id": agent_id, "directive": directive}})

    async def handle_agent_sign(self, agent_id: str, message: str) -> Dict[str, Any]:
        if not self.mastermind.id_manager_agent:
            return {"error": "IDManagerAgent not available."}
        signature = await self.mastermind.id_manager_agent.sign_message(agent_id, message)
        return {"signature": signature}

    async def handle_get_runtime_logs(self) -> Dict[str, Any]:
        if not self.mastermind.memory_agent:
            return {"error": "MemoryAgent not available."}
        try:
            logs = await self.mastermind.memory_agent.get_runtime_logs()
            return {"logs": logs}
        except Exception as e:
            return {"error": f"Failed to retrieve logs: {e}"}
