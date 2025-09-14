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
from utils.logging_config import get_logger, setup_logging
from utils.config import Config, PROJECT_ROOT as CONFIG_PROJECT_ROOT
from agents.memory_agent import MemoryAgent

logger = None

async def main_cli_loop(mastermind: MastermindAgent):
    global logger
    if not logger: logger = get_logger(__name__)

    logger.info("mindX Mastermind Agent (Augmentic Intelligence) ready for CLI interaction.")
    print("\nWelcome to the mindX Command Line Interface (Mastermind Edition - Augmentic Intelligence).")
    print("This system operates on the principles of Augmentic Intelligence.")
    print(f"Project Root (calculated by script): {project_root}")
    print(f"Project Root (from utils.config): {CONFIG_PROJECT_ROOT}")
    print("Type 'help' for a list of commands, or 'quit'/'exit' to stop.")

    while True:
        try:
            user_input_str = await asyncio.to_thread(input, "mindX (Mastermind) > ")
        except (EOFError, KeyboardInterrupt):
            logger.info("EOF or KeyboardInterrupt received. Exiting mindX CLI gracefully.")
            break
        if not user_input_str.strip(): continue
        if user_input_str.lower() in ["quit", "exit"]: logger.info("Exit command received. Shutting down mindX."); break

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
                print("\n=== mindX Mastermind Evolution Campaign Outcome ===")
                print(json.dumps(result, indent=2, default=str))
            except Exception as e: logger.error(f"Error during Mastermind evolution: {e}", exc_info=True); print(f"CLI Error: {e}")
        elif command_verb == "mastermind_status":
            print("\n--- mindX Mastermind Status (Augmentic Intelligence) ---")
            print("(Note: Status display may be deprecated; functionality now resides in AGInt/BDI layers)")
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

        # <<< NEW: Command block for Identity Manager >>>
        elif command_verb.startswith("id_"):
            if not mastermind.id_manager_agent:
                print("Error: Mastermind's IDManagerAgent is not available."); continue
            
            id_manager = mastermind.id_manager_agent
            
            if command_verb == "id_list":
                print("\n--- Managed Identities ---")
                identities = id_manager.list_managed_identities()
                if not identities:
                    print("No identities found in the manager's .env file.")
                else:
                    for identity in identities:
                        print(f"- Entity Hint: {identity['entity_id_part']}, PubAddr Suffix: ...{identity['address_suffix_in_env_var'][-6:]}, EnvVar: {identity['env_var_name']}")
            
            elif command_verb == "id_create":
                if not args_str: print("Error: 'id_create' command requires an <entity_id> string."); continue
                entity_id = args_str.strip()
                print(f"Creating new identity for entity: '{entity_id}'...")
                public_address, env_var_name = id_manager.create_new_wallet(entity_id=entity_id)
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
        else:
            if command_verb not in ["help", "quit", "exit"]:
                 print(f"Unknown command for mindX: '{command_verb}'. Type 'help'.")
        print("-" * 60)

def print_help():
    """Prints the help message for the CLI."""
    commands = {
        "Core Commands": {
            "evolve <directive>": "Task Mastermind with a high-level evolutionary directive.",
            "mastermind_status": "Display Mastermind's objectives and campaign history.",
            "show_agent_registry": "Display the agents registered with the Coordinator.",
            "show_tool_registry": "Display the official tool registry content.",
            "analyze_codebase <path_to_code> [focus_prompt]": "Mastermind: Analyze codebase using BaseGenAgent.",
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
        # Centralized setup now handled by MemoryAgent
        app_config = Config()
        memory_agent = MemoryAgent(config=app_config, log_level=app_config.get("logging.level", "INFO"))
        
        logger = get_logger(__name__) # Get logger after setup
        logger.info(f"mindX CLI (Mastermind Edition - Augmentic Intelligence). Project Root (calculated): {project_root}")
        logger.info(f"mindX CLI trying to use Project Root (from config defined in utils.config): {CONFIG_PROJECT_ROOT}")
        
        # --- Corrected Initialization ---
        # 1. Get the CoordinatorAgent instance first.
        coordinator_instance = await get_coordinator_agent_mindx_async(config_override=app_config)
        if not coordinator_instance:
            logger.critical("Failed to initialize CoordinatorAgent. Mastermind cannot be started.")
            print("Fatal Error: Could not start CoordinatorAgent. Check logs.")
            return

        # 2. Pass the Coordinator and Memory agents to the MastermindAgent.
        mastermind_instance = await MastermindAgent.get_instance(
            config_override=app_config,
            coordinator_agent_instance=coordinator_instance,
            memory_agent=memory_agent
        )
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
