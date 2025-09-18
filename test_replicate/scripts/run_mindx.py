# scripts/run_mindx.py
import asyncio
import json
import sys
from pathlib import Path
import readline
from typing import Optional, Dict, Any
from datetime import datetime
import time

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from orchestration.mastermind_agent import MastermindAgent
from orchestration.coordinator_agent import get_coordinator_agent_mindx_async, InteractionType, InteractionStatus
from agents.memory_agent import MemoryAgent
from agents.guardian_agent import GuardianAgent
from agents.automindx_agent import AutoMINDXAgent
from core.id_manager_agent import IDManagerAgent
from core.belief_system import BeliefSystem
from llm.model_registry import get_model_registry_async
from utils.logging_config import get_logger, setup_logging
from utils.config import Config, PROJECT_ROOT as CONFIG_PROJECT_ROOT

logger = None

async def main_cli_loop(mastermind: MastermindAgent):
    global logger
    if not logger: logger = get_logger(__name__)
    
    memory_agent = mastermind.memory_agent # Get the memory agent instance from mastermind

    logger.info("mindX Mastermind Agent (Augmentic Intelligence) ready for CLI interaction.")
    print("\nWelcome to the mindX Command Line Interface (Mastermind Edition - Augmentic Intelligence).")
    print("Your wish is mind command.")
    print("This system operates on the principles of Augmentic Intelligence.")
    print(f"Project Root (calculated by script): {project_root}")
    print(f"Project Root (from utils.config): {CONFIG_PROJECT_ROOT}")
    print("Type 'help' for a list of commands, or 'quit'/'exit' to stop.")

    while True:
        try:
            user_input_str = await asyncio.to_thread(input, "mindX (Mastermind) > ")
            await memory_agent.log_terminal_output(f"USER_INPUT: {user_input_str}")
        except (EOFError, KeyboardInterrupt):
            logger.info("EOF or KeyboardInterrupt received. Exiting mindX CLI gracefully.")
            await memory_agent.log_terminal_output("EVENT: EOF or KeyboardInterrupt received.")
            break
        if not user_input_str.strip(): continue
        if user_input_str.lower() in ["quit", "exit"]:
            logger.info("Exit command received. Shutting down mindX.")
            await memory_agent.log_terminal_output("EVENT: User requested exit.")
            break

        if user_input_str.lower() == "help":
            print_help()
            continue

        parts = user_input_str.strip().split(" ", 1)
        command_verb = parts[0].lower()
        args_str = parts[1] if len(parts) > 1 else ""

        if command_verb == "evolve":
            if not args_str: print("Error: 'evolve' command requires a <directive> string."); continue
            print(f"\nmindX Mastermind: Initiating evolution campaign with directive: '{args_str}'...")
            try:
                result = await mastermind.manage_mindx_evolution(top_level_directive=args_str)
                result_str = json.dumps(result, indent=2, default=str)
                print("\n=== mindX Mastermind Evolution Campaign Outcome ===")
                print(result_str)
                await memory_agent.log_terminal_output(f"SYSTEM_OUTPUT: {result_str}")
            except Exception as e:
                logger.error(f"Error during Mastermind evolution: {e}", exc_info=True)
                error_str = f"CLI Error: {e}"
                print(error_str)
                await memory_agent.log_terminal_output(f"SYSTEM_ERROR: {error_str}")
        elif command_verb == "mastermind_status":
            print("\n--- mindX Mastermind Status (Augmentic Intelligence) ---")
            print("High-Level Objectives:")
            for objective in mastermind.high_level_objectives:
                print(f"  - {objective}")
            print("\nCampaign History:")
            for campaign in mastermind.strategic_campaigns_history:
                print(f"  - {campaign}")
            print("-" * 30)
        elif command_verb == "show_agent_registry":
            print("\n--- mindX Agent Registry (via Coordinator) ---")
            if mastermind.coordinator_agent:
                print(json.dumps(mastermind.coordinator_agent.agent_registry, indent=2, default=lambda o: f"<Object {type(o).__name__}>"))
            else:
                 print("Coordinator agent not available to show tool registry.")
            print("-" * 30)
        elif command_verb == "analyze_codebase":
            code_path_parts = args_str.split(" ", 1)
            if not code_path_parts or not code_path_parts[0]: print("Error: analyze_codebase requires a <path_to_code>."); continue
            target_code_path = code_path_parts[0]
            focus = code_path_parts[1] if len(code_path_parts) > 1 else "General strategic analysis and tool extrapolation opportunities."
            print(f"\nMastermind: Initiating codebase analysis for '{target_code_path}' with focus: '{focus}'")
            directive = f"Analyze codebase at '{target_code_path}' focusing on '{focus}', and store results. Then, assess tool suite based on new findings."
            result = await mastermind.manage_mindx_evolution(top_level_directive=directive)
            print("\n=== Mastermind Codebase Analysis Campaign Outcome ===")
            print(json.dumps(result, indent=2, default=str))
        elif command_verb == "deploy":
            if not args_str: print("Error: 'deploy' command requires a <directive> string."); continue
            print(f"\nAutoMINDX: Initiating dynamic agent deployment with directive: '{args_str}'...")
            try:
                result = await mastermind.manage_agent_deployment(top_level_directive=args_str)
                result_str = json.dumps(result, indent=2, default=str)
                print("\n=== AutoMINDX Deployment Campaign Outcome ===")
                print(result_str)
                await memory_agent.log_terminal_output(f"SYSTEM_OUTPUT: {result_str}")
            except Exception as e:
                logger.error(f"Error during AutoMINDX deployment: {e}", exc_info=True)
                error_str = f"CLI Error: {e}"
                print(error_str)
                await memory_agent.log_terminal_output(f"SYSTEM_ERROR: {error_str}")
        elif command_verb == "introspect":
            if not args_str: print("Error: 'introspect' command requires a <role_description> string."); continue
            print(f"\nAutoMINDX: Generating a new persona for role: '{args_str}'...")
            if not mastermind.automindx_agent:
                print("Error: AutoMINDX agent is not available."); continue
            try:
                new_persona = await mastermind.automindx_agent.generate_new_persona(args_str)
                print("\n=== AutoMINDX Generated Persona ===")
                print(new_persona)
            except Exception as e:
                logger.error(f"Error during persona introspection: {e}", exc_info=True)
                print(f"CLI Error: {e}")
        elif command_verb == "basegen":
            if not mastermind.code_base_analyzer:
                print("Error: Mastermind's CodeBaseGenerator (BaseGenAgent) is not available."); continue
            if not args_str:
                print("Error: 'basegen' command requires a <path_to_generate_docs_for>."); continue
            target_path = args_str.strip()
            print(f"\nMastermind: Running BaseGenAgent documentation generation for path: '{target_path}'...")
            try:
                # BaseGenAgent's main method is synchronous, so we run it in a thread
                report = await asyncio.to_thread(
                    mastermind.code_base_analyzer.generate_markdown_summary,
                    root_path_str=target_path
                )
                print("\n=== BaseGenAgent Documentation Generation Report ===")
                print(json.dumps(report, indent=2, default=str))
            except Exception as e:
                logger.error(f"Error during BaseGenAgent execution: {e}", exc_info=True)
                print(f"CLI Error: {e}")

        # <<< NEW: Command block for Identity Manager >>>
        elif command_verb.startswith("id_"):
            if not mastermind.id_manager_agent:
                print("Error: Mastermind's IDManagerAgent is not available."); continue
            
            id_manager = mastermind.id_manager_agent
            
            if command_verb == "id_list":
                print("\n--- Managed Identities ---")
                identities = await id_manager.list_managed_identities()
                if not identities:
                    print("No identities found.")
                else:
                    for identity in identities:
                        print(f"- Entity ID: {identity.get('entity_id', 'N/A')}, Public Address: {identity.get('public_address', 'N/A')}")
            
            elif command_verb == "id_create":
                if not args_str: print("Error: 'id_create' command requires an <entity_id> string."); continue
                entity_id = args_str.strip()
                print(f"Creating new identity for entity: '{entity_id}'...")
                public_address, env_var_name = await id_manager.create_new_wallet(entity_id=entity_id)
                print(f"Success! New Identity Created:")
                print(f"  Public Address: {public_address}")
                print(f"  Private Key stored in .env as: {env_var_name}")
                
            elif command_verb == "id_deprecate":
                dep_parts = args_str.strip().split(" ")
                if not dep_parts or not dep_parts[0]: print("Error: 'id_deprecate' command requires a <public_address>."); continue
                public_address = dep_parts[0]
                entity_id_hint = dep_parts[1] if len(dep_parts) > 1 else None
                print(f"Attempting to deprecate identity with Public Address: {public_address} (Hint: {entity_id_hint})...")
                success = id_manager.deprecate_identity(public_address=public_address, entity_id_hint=entity_id_hint)
                if success:
                    print("Identity successfully deprecated (key removed from .env file).")
                else:
                    print("Failed to find and deprecate identity.")
            else:
                print(f"Unknown 'id_*' command: '{command_verb}'. Type 'help'.")
        elif command_verb == "audit_gemini":
            print("\n--- Auditing Gemini Models (via Mastermind) ---")
            try:
                from scripts import audit_gemini
                # Check for arguments
                if "--test-all" in args_str:
                    result = await asyncio.to_thread(audit_gemini.main, ["--test-all"])
                elif "--update-config" in args_str:
                    result = await asyncio.to_thread(audit_gemini.main, ["--update-config"])
                else:
                    print("Error: audit_gemini requires either --test-all or --update-config argument.")
                    continue

                print("\n=== Gemini Audit Outcome ===")
                print(json.dumps(result, indent=2, default=str))
            except Exception as e:
                logger.error(f"Error during Gemini audit: {e}", exc_info=True)
                print(f"CLI Error: Failed to run Gemini audit - {e}")
        elif command_verb.startswith("coord_"):
            if not mastermind.coordinator_agent: print("Error: Mastermind's CoordinatorAgent is not available."); continue
            coordinator = mastermind.coordinator_agent
            interaction_type: Optional[InteractionType] = None
            content_for_interaction = args_str
            metadata_for_interaction: Dict[str, Any] = {"cli_source_command": user_input_str, "routed_via_mastermind_cli_for_mindX": True}
            if command_verb == "coord_query":
                interaction_type = InteractionType.QUERY
                if not args_str: print("Error: 'coord_query' command requires a question."); continue
                content_for_interaction = f"Query for mindX Coordinator (Augmentic Intelligence): {args_str}"
            elif command_verb == "coord_analyze":
                interaction_type = InteractionType.SYSTEM_ANALYSIS
                content_for_interaction = "System analysis of mindX requested via Mastermind CLI."
                if args_str: metadata_for_interaction["analysis_context"] = f"mindX analysis context: {args_str}"
            elif command_verb == "coord_improve":
                interaction_type = InteractionType.COMPONENT_IMPROVEMENT
                improve_args_parts = args_str.split(" ", 1)
                if not improve_args_parts or not improve_args_parts[0]: print("Error: 'coord_improve' command requires a <component_id>."); continue
                metadata_for_interaction["target_component"] = improve_args_parts[0]
                context_detail = f"General improvement request for mindX component {metadata_for_interaction['target_component']} from Mastermind CLI."
                if len(improve_args_parts) > 1: context_detail = improve_args_parts[1]
                metadata_for_interaction["analysis_context"] = context_detail
                content_for_interaction = f"CLI Request (via Mastermind for mindX): Improve component {metadata_for_interaction['target_component']}"
            elif command_verb == "coord_backlog":
                print("\n--- mindX Coordinator Improvement Backlog (via Mastermind) ---")
                if coordinator.improvement_backlog:
                    for i, item in enumerate(coordinator.improvement_backlog):
                        added_ts = item.get('added_at', 0); added_dt = datetime.fromtimestamp(added_ts).strftime('%Y-%m-%d %H:%M') if added_ts else "N/A"
                        print(f"{i+1}. ID: {item.get('id', 'N/A')[:8]} | Prio: {item.get('priority', '?')} | Status: {item.get('status', 'unknown')} | Target: {item.get('target_component_path', 'N/A')}\n   Suggestion: {item.get('suggestion', 'N/A')[:100]}...\n   Source: {item.get('source', 'N/A')} | Added: {added_dt}")
                else: print("mindX Coordinator's improvement backlog is currently empty.")
                print("-" * 30); continue
            elif command_verb == "coord_process_backlog":
                logger.info("CLI (via Mastermind for mindX): User requested Coordinator processing of one backlog item.")
                actionable_item: Optional[Dict[str, Any]] = None
                for item in coordinator.improvement_backlog:
                    if item.get("status") == InteractionType.PENDING.value:
                        is_critical_target = item.get("is_critical_target", False) or any(crit_stem in item.get("target_component_path","") for crit_stem in getattr(coordinator, "require_human_approval_for_critical", []))
                        if getattr(coordinator, "require_human_approval_for_critical", False) and is_critical_target and item.get("approved_at") is None: continue
                        actionable_item = item; break
                if actionable_item:
                    print(f"Attempting to process mindX Coordinator backlog item ID: {actionable_item.get('id','N/A')[:8]} for target: {actionable_item['target_component_path']}")
                    interaction_type = InteractionType.COMPONENT_IMPROVEMENT
                    metadata_for_interaction = {"target_component": actionable_item["target_component_path"], "analysis_context": actionable_item["suggestion"], "source": "cli_manual_backlog_process_via_mastermind_for_mindX", "original_priority": actionable_item.get("priority"), "backlog_item_id": actionable_item.get("id")}
                    content_for_interaction = f"CLI (via Mastermind for mindX): Process backlog item '{actionable_item.get('id','N/A')[:8]}': {actionable_item['suggestion'][:100]}"
                    actionable_item["status"] = InteractionStatus.IN_PROGRESS.value; actionable_item["last_attempted_at"] = time.time(); actionable_item["attempt_count"] = actionable_item.get("attempt_count", 0) + 1
                    if hasattr(coordinator, "_save_backlog") and callable(coordinator._save_backlog): coordinator._save_backlog()
                    else: logger.warning("mindX Coordinator instance does not have _save_backlog method.")
                else: print("No actionable items found in mindX Coordinator's backlog to process."); continue
            elif command_verb == "coord_approve":
                interaction_type = InteractionType.APPROVE_IMPROVEMENT
                if not args_str.strip(): print("Error: 'coord_approve' command requires a <mindx_backlog_item_id>."); continue
                metadata_for_interaction["backlog_item_id"] = args_str.strip()
                content_for_interaction = f"CLI Request (via Mastermind for mindX): Approve backlog item {metadata_for_interaction['backlog_item_id']}"
            elif command_verb == "coord_reject":
                interaction_type = InteractionType.REJECT_IMPROVEMENT
                if not args_str.strip(): print("Error: 'coord_reject' command requires a <mindx_backlog_item_id>."); continue
                metadata_for_interaction["backlog_item_id"] = args_str.strip()
                content_for_interaction = f"CLI Request (via Mastermind for mindX): Reject backlog item {metadata_for_interaction['backlog_item_id']}"
            else: print(f"Unknown 'coord_*' command for mindX: '{command_verb}'. Type 'help'."); continue

            if interaction_type and hasattr(coordinator, "handle_user_input"):
                try:
                    result_dict = await coordinator.handle_user_input(content=content_for_interaction, user_id="cli_user_mastermind_edition_mindX", interaction_type=interaction_type, metadata=metadata_for_interaction)
                    print("\n=== mindX Coordinator Response (via Mastermind) ==="); print(json.dumps(result_dict, indent=2, default=str)); print("=" * 30)
                except Exception as e_handle:
                    if logger: logger.error(f"Error during mindX coordinator.handle_user_input: {e_handle}", exc_info=True)
                    print(f"CLI Error: Failed to handle mindX Coordinator input - {e_handle}")
            elif not hasattr(coordinator, "handle_user_input"):
                 print("Error: mindX Mastermind's Coordinator instance does not have 'handle_user_input' method.")
        elif command_verb.startswith("agent_"):
            if command_verb == "agent_create":
                # Parse command with strict format validation
                parts = args_str.split(" ", 2)
                
                if len(parts) < 2:
                    print("❌ Error: Missing required parameters for agent creation.")
                    print()
                    print("📋 Usage: agent_create <agent_type> <agent_id> [description_or_config]")
                    print()
                    print("📝 Examples:")
                    print("  agent_create hash_tool file_hasher")
                    print("  agent_create hash_tool file_hasher for file integrity checking")
                    print("  agent_create hash_tool file_hasher '{\"description\": \"Custom hash tool\"}'")
                    print()
                    print("⚠️  Note: Both agent_type and agent_id are required parameters.")
                    print("💡 Tip: Use descriptive agent_ids like 'file_hasher', 'data_validator', etc.")
                    continue
                
                agent_type = parts[0].strip()
                agent_id = parts[1].strip()
                
                # Validate agent_id is not a common description word
                description_words = ['for', 'to', 'that', 'which', 'with', 'a', 'an', 'the', 'and', 'or', 'but', 'so', 'as', 'if', 'when', 'where', 'how', 'why', 'what', 'who', 'create', 'creating', 'make', 'making']
                if agent_id.lower() in description_words:
                    print(f"❌ Error: '{agent_id}' appears to be a description word, not a valid agent_id.")
                    print()
                    print("📋 Correct format: agent_create <agent_type> <agent_id> [description]")
                    print()
                    print("📝 Example for your command:")
                    print(f"  agent_create {agent_type} {agent_type}_tool {' '.join(parts[1:])}")
                    print("  OR")
                    print(f"  agent_create {agent_type} file_processor {' '.join(parts[1:])}")
                    print()
                    print("💡 Tip: Choose a descriptive agent_id that identifies the specific instance.")
                    continue
                
                # Handle optional description/config
                config = {}
                if len(parts) > 2:
                    config_str = parts[2].strip()
                    
                    # Check if it looks like JSON
                    if config_str.startswith(('{', '[')):
                        try:
                            config = json.loads(config_str)
                        except json.JSONDecodeError as e:
                            print(f"❌ Error: Invalid JSON configuration: {e}")
                            print()
                            print("📋 JSON format example:")
                            print('  {"description": "My custom agent", "capabilities": ["hash", "verify"]}')
                            print()
                            print("💡 Tip: Use double quotes inside JSON, single quotes around the entire JSON.")
                            continue
                    else:
                        # Treat as description
                        print(f"📝 Using '{config_str}' as agent description...")
                        config = {
                            "description": config_str,
                            "created_via": "cli_natural_language"
                        }
                else:
                    # No description provided - use default
                    config = {
                        "description": f"Agent of type {agent_type} with ID {agent_id}",
                        "created_via": "cli_minimal"
                    }
                
                print(f"🚀 Creating agent: type='{agent_type}', id='{agent_id}'")
                
                try:
                    # Use the AugmenticIntelligenceTool for proper agent creation
                    augmentic_tool = mastermind.bdi_agent.available_tools.get("augmentic_intelligence")
                    if augmentic_tool:
                        # Use the enhanced agent creation workflow
                        success, result = await augmentic_tool.execute(
                            capability="agent_management",
                            action="create_agent",
                            parameters={
                                "agent_type": agent_type,
                                "agent_id": agent_id,
                                "agent_config": config
                            }
                        )
                        
                        if success:
                            print("✅ Agent creation successful!")
                            print("📋 Agent creation details:")
                            print(json.dumps(result, indent=2, default=str))
                        else:
                            print(f"❌ Agent creation failed: {result}")
                    else:
                        # Fallback to original method if AugmenticIntelligenceTool not available
                        print("⚠️  Using fallback agent creation method...")
                        result = await mastermind.bdi_agent._internal_action_handlers["CREATE_AGENT"]({"params": {"agent_type": agent_type, "agent_id": agent_id, "config": config}})
                        print("✅ Agent creation result:")
                        print(json.dumps(result, indent=2, default=str))
                        
                except Exception as e:
                    print(f"❌ Error creating agent: {e}")
                    print()
                    print("🔧 Troubleshooting tips:")
                    print("  • Check if the agent_type is supported by the system")
                    print("  • Ensure the agent_id is unique and descriptive")
                    print("  • Verify your configuration parameters")
                    print("  • Make sure the AugmenticIntelligenceTool is properly initialized")
                    logger.error(f"Agent creation failed: {e}", exc_info=True)
            elif command_verb == "agent_delete":
                if not args_str:
                    print("Usage: agent_delete <agent_id>")
                    continue
                result = await mastermind.bdi_agent._internal_action_handlers["DELETE_AGENT"]({"params": {"agent_id": args_str}})
                print(json.dumps(result, indent=2, default=str))
            elif command_verb == "agent_list":
                if mastermind.coordinator_agent:
                    print("\n--- Registered Agents ---")
                    registry = mastermind.coordinator_agent.agent_registry
                    if not registry:
                        print("No agents are currently registered with the Coordinator.")
                    else:
                        for agent_id, details in registry.items():
                            print(f"- ID: {agent_id:<30} Type: {details.get('agent_type', 'N/A')}")
                else:
                    print("Error: CoordinatorAgent not available.")
            elif command_verb == "agent_evolve":
                parts = args_str.split(" ", 1)
                if len(parts) < 2:
                    print("Usage: agent_evolve <agent_id> <directive>")
                    continue
                agent_id, directive = parts[0], parts[1]
                result = await mastermind.bdi_agent._internal_action_handlers["EVOLVE_AGENT"]({"params": {"agent_id": agent_id, "directive": directive}})
                print(json.dumps(result, indent=2, default=str))
            elif command_verb == "agent_sign":
                parts = args_str.split(" ", 1)
                if len(parts) < 2:
                    print("Usage: agent_sign <agent_id> <message>")
                    continue
                agent_id, message = parts[0], parts[1]
                if not mastermind.id_manager_agent:
                    print("Error: IDManagerAgent not available.")
                    continue
                signature = mastermind.id_manager_agent.sign_message(agent_id, message)
                print(f"Signature: {signature}")
            else:
                print(f"Unknown 'agent_*' command: '{command_verb}'. Type 'help'.")
        else:
            if command_verb not in ["help", "quit", "exit"]:
                 print(f"Unknown command for mindX: '{command_verb}'. Type 'help'.")
        print("-" * 60)

def print_help():
    """Prints the help message for the CLI."""
    commands = {
        "Core Commands": {
            "evolve <directive>": "Task Mastermind to EVOLVE its own codebase.",
            "deploy <directive>": "Task AutoMINDX/Mastermind to DEPLOY new agents to achieve a goal.",
            "introspect <role>": "Ask AutoMINDX to generate a new persona for a given role.",
            "mastermind_status": "Display Mastermind's objectives and campaign history.",
            "show_agent_registry": "Display the agents registered with the Coordinator.",
            "show_tool_registry": "Display the official tool registry content.",
            "analyze_codebase <path_to_code> [focus_prompt]": "Mastermind: Analyze codebase using its internal analyzer.",
            "basegen <path>": "Run the BaseGenAgent to generate Markdown docs for a path.",
        },
        "Identity Manager Commands": {
            "id_list": "List all identities managed by Mastermind's IDManager.",
            "id_create <entity_id>": "Create a new cryptographic identity for an entity.",
            "id_deprecate <public_address> [entity_id_hint]": "Deprecate (remove) a managed identity.",
        },
        "Coordinator Commands": {
            "coord_query <your question>": "Send query to Coordinator's LLM.",
            "coord_analyze [optional context]": "Trigger Coordinator's system analysis.",
            "coord_improve <component_id> [optional context]": "Request Coordinator improve a component.",
            "coord_backlog": "Display Coordinator's improvement backlog.",
            "coord_process_backlog": "Trigger Coordinator to process one backlog item.",
            "coord_approve <backlog_item_id>": "Approve a Coordinator backlog item.",
            "coord_reject <backlog_item_id>": "Reject a Coordinator backlog item.",
        },
        "Utility Commands": {
            "audit_gemini --test-all|--update-config": "Audit Gemini models and update configuration.",
            "help": "Show this help message.",
            "quit / exit": "Shut down mindX and exit CLI.",
        },
        "Agent Lifecycle Commands": {
            "agent_create <type> [id] [description]": "Create agent. Supports: 'type description' or 'type id description'",
            "agent_delete <id>": "Delete an agent.",
            "agent_list": "List all registered agents.",
            "agent_evolve <id> <directive>": "Evolve a specific agent.",
            "agent_sign <id> <message>": "Sign a message with an agent's identity.",
        },
    }

    print("\nAvailable mindX CLI Commands (Mastermind Edition - Augmentic Intelligence):")
    for category, cmds in commands.items():
        print(f"\n  --- {category} ---")
        for cmd, desc in cmds.items():
            print(f"  {cmd:<48} - {desc}")
    print("-" * 60)

async def main_entry():
    global logger
    mastermind_instance: Optional[MastermindAgent] = None
    try:
        app_config = Config()
        memory_agent = MemoryAgent(config=app_config, log_level=app_config.get("logging.level", "INFO"))
        
        setup_logging()
        logger = get_logger(__name__)
        logger.info(f"mindX CLI (Mastermind Edition - Augmentic Intelligence). Project Root (calculated): {project_root}")
        logger.info(f"mindX CLI trying to use Project Root (from config defined in utils.config): {CONFIG_PROJECT_ROOT}")
        
        # --- Corrected Initialization ---
        # 1. Get the CoordinatorAgent instance first, passing the memory agent to it.
        belief_system = BeliefSystem()
        id_manager = await IDManagerAgent.get_instance(config_override=app_config, belief_system=belief_system)
        # Initialize AutoMINDX, the keeper of prompts
        automindx_instance = await AutoMINDXAgent.get_instance(memory_agent=memory_agent, config_override=app_config)
        guardian_agent = await GuardianAgent.get_instance(id_manager=id_manager, config_override=app_config)
        model_registry = await get_model_registry_async(config=app_config)
        
        coordinator_instance = await get_coordinator_agent_mindx_async(
            config_override=app_config,
            memory_agent=memory_agent,
            belief_system=belief_system
        )
        if not coordinator_instance:
            logger.critical("Failed to initialize CoordinatorAgent. Mastermind cannot be started.")
            print("Fatal Error: Could not start CoordinatorAgent. Check logs.")
            return

        # 2. Pass the Coordinator, Memory, and Guardian agents to the MastermindAgent.
        mastermind_instance = await MastermindAgent.get_instance(
            config_override=app_config,
            coordinator_agent_instance=coordinator_instance,
            memory_agent=memory_agent,
            guardian_agent=guardian_agent,
            model_registry=model_registry
        )
        
        # Create wallets for core agents and register them
        print("\n--- Initializing and Registering Core Agents ---")
        core_agents_to_register = {
            "mastermind": mastermind_instance,
            "coordinator": coordinator_instance,
            "guardian": guardian_agent,
            "automindx": automindx_instance,
            "memory": memory_agent,
            "strategic_evolution": mastermind_instance.strategic_evolution_agent if mastermind_instance else None,
            "blueprint": mastermind_instance.strategic_evolution_agent.blueprint_agent if mastermind_instance and mastermind_instance.strategic_evolution_agent else None
        }

        for name, instance in core_agents_to_register.items():
            if instance and hasattr(instance, 'agent_id'):
                # 1. Register the agent with the coordinator
                if name != "coordinator": # Coordinator is already self-registered
                    coordinator_instance.register_agent(
                        agent_id=instance.agent_id,
                        agent_type="core_service" if name != "mastermind" else "orchestrator",
                        description=f"Core {name.capitalize()} Agent",
                        instance=instance
                    )
                # 2. Ensure identity is created (or retrieved)
                public_address, env_var_name = await id_manager.create_new_wallet(entity_id=instance.agent_id)
                print(f"Identity for '{instance.agent_id}':")
                print(f"  Public Address: {public_address}")
                print(f"  Private Key stored as: {env_var_name}")
                agent_data_dir = memory_agent.get_agent_data_directory(instance.agent_id)
                print(f"  Data Directory: {agent_data_dir}")
        print("-" * 30)

        # --- End Correction ---

        if not mastermind_instance:
            logger.critical("Failed to initialize mindX MastermindAgent instance. CLI cannot start.")
            print("Fatal Error: Could not start mindX Mastermind. Check logs.")
            return
        await main_cli_loop(mastermind_instance)
    except ModuleNotFoundError as e_mod:
        print(f"FATAL: A module was not found: {e_mod}")
        print("This usually means that the primary package (e.g., 'orchestration', 'utils') is not discoverable or `__init__.py` files are missing within them.")
        print(f"Please ensure you are running this script from the project root (e.g., {Path.cwd()}) and that your package directories (like 'orchestration', 'utils', etc., directly under the project root) contain an `__init__.py` file.")
        print(f"Current sys.path (Python's search path for modules):")
        for p_item in sys.path: print(f"  - {p_item}")
        if logger: logger.critical(f"ModuleNotFoundError during mindX CLI startup: {e_mod}", exc_info=True)
    except Exception as e:
        if logger: logger.critical(f"Critical error during mindX CLI startup or main loop: {e}", exc_info=True)
        else: print(f"Critical error (logger not initialized): {e}")
        print(f"A critical error occurred with mindX. Check logs. Error: {e}")
    finally:
        if mastermind_instance:
            if logger: logger.info("Shutting down mindX Mastermind Agent from CLI...")
            await mastermind_instance.shutdown()
            if logger: logger.info("mindX Mastermind Agent shutdown complete.")
        else:
            if logger: logger.info("mindX CLI (Mastermind Edition - Augmentic Intelligence) finished. MastermindAgent was not initialized or failed.")
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    try: asyncio.run(main_entry())
    except KeyboardInterrupt:
        print("\nmindX CLI terminated by user.")
    finally:
        print("mindX CLI (mastermind Edition - Augmentic Intelligence) exited.")
