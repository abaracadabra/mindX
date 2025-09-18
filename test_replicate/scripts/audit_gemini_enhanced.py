# mindx/scripts/audit_gemini_enhanced.py (c) 2025 PYTHAI MIT license
"""
Enhanced Gemini Model Auditor with TokenCalculatorTool Integration

This enhanced version of the Gemini auditor includes comprehensive cost tracking,
pricing integration, and token usage analysis using the new TokenCalculatorTool.
It provides real-time cost estimates and updates model configurations with
accurate pricing information from the centralized pricing database.

Usage (from project root):
- To audit with cost tracking:   `python3 scripts/audit_gemini_enhanced.py --test-all --track-costs`
- To update configs with pricing: `python3 scripts/audit_gemini_enhanced.py --update-config --sync-pricing`
- To analyze token usage:        `python3 scripts/audit_gemini_enhanced.py --analyze-usage`
"""
import sys
import asyncio
import argparse
import logging
import os
import json
from pathlib import Path
from time import strftime, gmtime
from typing import Dict, Any, List, Optional, Tuple
from io import BytesIO

# --- Global Imports & Prerequisite Checks ---
try:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    from llm.rate_limiter import RateLimiter
    import google.generativeai as genai
    from dotenv import load_dotenv
    from PIL import Image
    import yaml
    from agents.memory_agent import MemoryAgent
    from tools.token_calculator_tool import TokenCalculatorTool
    from utils.config import Config
except ImportError as e:
    print(f"FATAL: Required libraries are missing. Please run: 'pip install google-genai python-dotenv Pillow numpy scipy pyyaml'. Error: {e}", file=sys.stderr)
    sys.exit(1)

# --- ANSI Color Codes for Professional Output ---
class Colors:
    HEADER = '\033[95m'; OKGREEN = '\033[92m'; OKBLUE = '\033[94m'
    FAIL = '\033[91m'; WARN = '\033[93m'; ENDC = '\033[0m'; BOLD = '\033[1m'; GREY = '\033[90m'

# --- UI Status Box Management ---
_status_lines = ["", "", ""]

def print_status_box(line1: str = "", line2: str = "", line3: str = ""):
    """Manages a 3-line status box at the top of the script, overwriting it in place."""
    global _status_lines
    _status_lines = [line1 or _status_lines[0], line2 or _status_lines[1], line3 or _status_lines[2]]
    sys.stdout.write("\033[F\033[K" * 3)
    sys.stdout.write(f"{_status_lines[0]}\n{_status_lines[1]}\n{_status_lines[2]}\n")
    sys.stdout.flush()

def rate_limiter_ui_callback(attempt: int, max_retries: int, wait_time: float):
    """This function is passed to the RateLimiter to handle UI updates."""
    if attempt == 0:
        print_status_box(line3="")
    elif attempt > max_retries:
        status = f"RATE LIMITER FAILED: Max retries ({max_retries}) exceeded."
        print_status_box(line3=f"{Colors.BOLD}{Colors.FAIL}{status}{Colors.ENDC}")
    else:
        status = f"RateLimit Backoff: Waiting {wait_time:.2f}s (Attempt {attempt}/{max_retries})"
        print_status_box(line3=f"{Colors.FAIL}{status}{Colors.ENDC}")

# --- Main Script Logic ---
def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Enhanced MindX Gemini Model Auditor with Cost Tracking", 
                                    formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--test-all", action="store_true", 
                       help="Assess all available models and produce a JSON report.")
    parser.add_argument("--update-config", action="store_true", 
                       help="Merge live audit results with existing gemini.yaml and update it.")
    parser.add_argument("--track-costs", action="store_true", 
                       help="Track token usage and costs during testing.")
    parser.add_argument("--sync-pricing", action="store_true", 
                       help="Sync model configurations with centralized pricing database.")
    parser.add_argument("--analyze-usage", action="store_true", 
                       help="Analyze recent token usage and generate cost report.")
    parser.add_argument("--budget-check", action="store_true", 
                       help="Check current budget status and spending.")
    
    args = parser.parse_args(argv)
    
    # Validate argument combinations
    if not any([args.test_all, args.update_config, args.analyze_usage, args.budget_check]):
        parser.error("Must specify at least one action: --test-all, --update-config, --analyze-usage, or --budget-check")
    
    # Initialize components
    config = Config()
    memory_agent = MemoryAgent(config=config)
    token_calculator = TokenCalculatorTool(memory_agent=memory_agent, config=config)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [GeminiAuditEnhanced] - %(levelname)s - %(message)s')
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.ERROR)

    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: 
        logging.critical("Error: GEMINI_API_KEY not found.")
        return 1

    genai.configure(api_key=api_key)
    
    try:
        print("\n\n\n")
        
        # Execute requested actions
        if args.analyze_usage:
            asyncio.run(analyze_token_usage(token_calculator))
        
        if args.budget_check:
            asyncio.run(check_budget_status(token_calculator))
        
        if args.test_all or args.update_config:
            audit_results = asyncio.run(_perform_enhanced_audit(token_calculator, args.track_costs))
            if not audit_results: 
                logging.critical("Audit failed. Aborting.")
                return 1
            
            if args.test_all:
                generate_enhanced_json_report(audit_results, token_calculator)
                asyncio.run(memory_agent.log_process(
                    process_name="gemini_audit_enhanced",
                    data={
                        "action": "test-all", 
                        "report_generated": True, 
                        "operational_models": len([r for r in audit_results if any(v["status"] == "OPERATIONAL" for v in r["assessed_capabilities"].values())]),
                        "cost_tracking_enabled": args.track_costs
                    },
                    metadata={"agent_id": "audit_gemini_enhanced_script"}
                ))
            
            if args.update_config:
                await_result = asyncio.run(update_yaml_config_enhanced(audit_results, token_calculator, args.sync_pricing))
                asyncio.run(memory_agent.log_process(
                    "gemini_audit_enhanced", 
                    {
                        "action": "update-config", 
                        "config_updated": True, 
                        "operational_models": len([r for r in audit_results if any(v["status"] == "OPERATIONAL" for v in r["assessed_capabilities"].values())]),
                        "pricing_synced": args.sync_pricing
                    }
                ))
                
    except KeyboardInterrupt: 
        print("\nAudit interrupted by user.")
        return 1
    except Exception as e: 
        logging.critical(f"A critical error occurred: {e}", exc_info=True)
        return 1
    
    return 0

async def analyze_token_usage(token_calculator: TokenCalculatorTool):
    """Analyze recent token usage and generate comprehensive cost report."""
    print(f"{Colors.HEADER}{Colors.BOLD}=== Token Usage Analysis ==={Colors.ENDC}")
    
    # Get 7-day usage report
    success, report = await token_calculator.execute("get_usage_report", days_back=7)
    
    if not success:
        print(f"{Colors.FAIL}Failed to generate usage report: {report}{Colors.ENDC}")
        return
    
    print(f"\n{Colors.OKGREEN}📊 Usage Report (Last 7 Days):{Colors.ENDC}")
    print(f"  Total Operations: {report.get('total_operations', 0)}")
    print(f"  Total Cost: ${report.get('total_cost_usd', 0):.6f}")
    print(f"  Total Tokens: {report.get('total_tokens', 0):,}")
    print(f"  Avg Cost/Operation: ${report.get('average_cost_per_operation', 0):.6f}")
    print(f"  Daily Average Cost: ${report.get('daily_average_cost', 0):.6f}")
    
    # Show top models by cost
    by_model = report.get('by_model', {})
    if by_model:
        print(f"\n{Colors.OKBLUE}💰 Top Models by Cost:{Colors.ENDC}")
        sorted_models = sorted(by_model.items(), key=lambda x: x[1]['cost'], reverse=True)
        for model, stats in sorted_models[:5]:
            print(f"  {model}: ${stats['cost']:.6f} ({stats['operations']} ops)")
    
    # Show optimization recommendations
    recommendations = report.get('optimization_recommendations', [])
    if recommendations:
        print(f"\n{Colors.WARN}🎯 Cost Optimization Recommendations:{Colors.ENDC}")
        for i, rec in enumerate(recommendations, 1):
            if rec['type'] == 'model_substitution':
                print(f"  {i}. Consider switching from {rec['current_model']} to cheaper alternatives")
                print(f"     Current avg cost: ${rec['current_avg_cost']:.6f}")
                print(f"     Suggested models: {', '.join(rec['suggested_models'][:3])}")
            elif rec['type'] == 'prompt_optimization':
                print(f"  {i}. {rec['description']}")
                print(f"     {rec['operations_count']} operations, avg {rec['average_tokens']} tokens")

async def check_budget_status(token_calculator: TokenCalculatorTool):
    """Check current budget status and alert if needed."""
    print(f"{Colors.HEADER}{Colors.BOLD}=== Budget Status Check ==={Colors.ENDC}")
    
    success, budget_status = await token_calculator.execute("check_budget")
    
    if not success:
        print(f"{Colors.FAIL}Failed to check budget: {budget_status}{Colors.ENDC}")
        return
    
    status_color = Colors.OKGREEN if budget_status['status'] == 'OK' else Colors.FAIL
    print(f"\n{status_color}💼 Budget Status: {budget_status['status']}{Colors.ENDC}")
    print(f"  Daily Budget: ${budget_status['daily_budget']:.2f}")
    print(f"  Daily Spent: ${budget_status['daily_spent']:.6f}")
    print(f"  Daily Remaining: ${budget_status['daily_remaining']:.6f}")
    print(f"  Daily Utilization: {budget_status['daily_utilization']:.1%}")
    print(f"  Weekly Spent: ${budget_status['weekly_spent']:.6f}")
    print(f"  Monthly Spent: ${budget_status['monthly_spent']:.6f}")

async def _perform_enhanced_audit(token_calculator: TokenCalculatorTool, track_costs: bool = False) -> List[Dict[str, Any]]:
    """Enhanced audit that includes cost tracking and token usage analysis."""
    limiter = RateLimiter(requests_per_minute=25, status_callback=rate_limiter_ui_callback)
    
    print_status_box(f"{Colors.OKGREEN}Discovering models from Google API...{Colors.ENDC}")
    try:
        live_models = list(genai.list_models())
    except Exception as e:
        logging.critical(f"Could not retrieve model list from API: {e}")
        return []

    audit_results = []
    total_models = len(live_models)
    total_cost = 0.0
    
    for i, model in enumerate(live_models):
        sdk_model_name = model.name.replace("models/", "")
        progress_bar = f"[{int(((i+1)/total_models)*20)*'='}>{(20-int(((i+1)/total_models)*20))*' '}]"
        
        cost_info = ""
        if track_costs:
            cost_info = f" | Tracking costs..."
        
        print_status_box(
            f"Progress: {progress_bar} {i+1}/{total_models}", 
            f"Assessing: {sdk_model_name}{cost_info}"
        )

        result = await _assess_single_model_enhanced(model, limiter, token_calculator, track_costs)
        audit_results.append(result)
        
        if track_costs and 'cost_analysis' in result:
            total_cost += result['cost_analysis'].get('total_cost', 0)

    print_status_box(f"{Colors.OKGREEN}Assessment Complete.{Colors.ENDC}", f"Processed {total_models} models.", "")
    if track_costs:
        print_status_box(f"{Colors.OKGREEN}Assessment Complete.{Colors.ENDC}", f"Processed {total_models} models.", f"Total audit cost: ${total_cost:.6f}")
    
    sys.stdout.write("\033[F\033[K" * 4)  # Clean up the status box area
    
    # Enhanced output with cost information
    if track_costs:
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'Model API Name':<45} {'Text':<12} {'Vision':<12} {'Embedding':<12} {'Est. Cost':<12}{Colors.ENDC}")
        print("-" * 97)
    else:
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'Model API Name':<45} {'Text':<12} {'Vision':<12} {'Embedding':<12}{Colors.ENDC}")
        print("-" * 85)
    
    for result in sorted(audit_results, key=lambda x: x['api_name']):
        print(f"{Colors.BOLD}{result['api_name']:<45}{Colors.ENDC}", end="", flush=True)
        for cap in ["text", "vision", "embedding"]:
            status = result["assessed_capabilities"][cap]['status']
            color = Colors.OKGREEN if status == 'OPERATIONAL' else Colors.FAIL if status == 'ERROR' else Colors.GREY
            print(f"{color}{status:<12}{Colors.ENDC}", end="", flush=True)
        
        if track_costs and 'cost_analysis' in result:
            cost = result['cost_analysis'].get('total_cost', 0)
            print(f"${cost:.6f}".ljust(12), end="", flush=True)
        
        print()

    if track_costs:
        print(f"\n{Colors.OKBLUE}💰 Total Audit Cost: ${total_cost:.6f}{Colors.ENDC}")

    return audit_results

async def _assess_single_model_enhanced(model, limiter, token_calculator: TokenCalculatorTool, track_costs: bool) -> Dict[str, Any]:
    """Enhanced model assessment with cost tracking."""
    sdk_model_name = model.name.replace("models/", "")
    await limiter.wait()
    
    result_entry = {
        "internal_id": f"gemini/{sdk_model_name}", 
        "api_name": sdk_model_name, 
        "display_name": model.display_name, 
        "version": model.version, 
        "assessed_capabilities": {}
    }
    
    # Test prompts for different capabilities
    test_prompts = {
        "text": "What is artificial intelligence?",
        "vision": "Describe this image.",
        "embedding": "test content for embedding"
    }
    
    cost_analysis = {"total_cost": 0.0, "by_capability": {}} if track_costs else None
    
    # Text capability test
    text_result = await _run_test_with_cost_tracking(
        lambda: genai.GenerativeModel(sdk_model_name).generate_content(test_prompts["text"]),
        token_calculator if track_costs else None,
        sdk_model_name,
        test_prompts["text"],
        "text_capability_test"
    )
    result_entry["assessed_capabilities"]["text"] = {"status": text_result["status"]}
    if track_costs and cost_analysis:
        cost_analysis["by_capability"]["text"] = text_result.get("cost", 0)
        cost_analysis["total_cost"] += text_result.get("cost", 0)
    
    # Vision capability test
    vision_result = await _run_test_with_cost_tracking(
        lambda: genai.GenerativeModel(sdk_model_name).generate_content([Image.new('RGB', (1,1)), test_prompts["vision"]]),
        token_calculator if track_costs else None,
        sdk_model_name,
        test_prompts["vision"],
        "vision_capability_test"
    )
    result_entry["assessed_capabilities"]["vision"] = {"status": vision_result["status"]}
    if track_costs and cost_analysis:
        cost_analysis["by_capability"]["vision"] = vision_result.get("cost", 0)
        cost_analysis["total_cost"] += vision_result.get("cost", 0)
    
    # Embedding capability test
    embedding_result = await _run_test_with_cost_tracking(
        lambda: genai.embed_content(model=model.name, content=test_prompts["embedding"]),
        token_calculator if track_costs else None,
        sdk_model_name,
        test_prompts["embedding"],
        "embedding_capability_test"
    )
    result_entry["assessed_capabilities"]["embedding"] = {"status": embedding_result["status"]}
    if track_costs and cost_analysis:
        cost_analysis["by_capability"]["embedding"] = embedding_result.get("cost", 0)
        cost_analysis["total_cost"] += embedding_result.get("cost", 0)
    
    if track_costs:
        result_entry["cost_analysis"] = cost_analysis
    
    return result_entry

async def _run_test_with_cost_tracking(test_func, token_calculator: Optional[TokenCalculatorTool], 
                                     model: str, prompt: str, operation: str) -> Dict[str, Any]:
    """Run a test with optional cost tracking."""
    try:
        # Estimate cost before running
        estimated_cost = 0.0
        if token_calculator:
            success, cost_estimate = await token_calculator.execute(
                "estimate_cost",
                text=prompt,
                model=model,
                operation_type="text_generation"
            )
            if success:
                estimated_cost = cost_estimate["total_cost_usd"]
        
        # Run the actual test
        await asyncio.to_thread(test_func)
        
        # Track usage if cost tracking is enabled
        if token_calculator:
            # Use estimated values since we don't have access to actual token counts from Gemini API
            estimated_input_tokens = len(prompt) // 4  # Rough estimation
            estimated_output_tokens = 10  # Minimal response for capability test
            
            await token_calculator.execute(
                "track_usage",
                agent_id="audit_gemini_enhanced",
                operation=operation,
                model=model,
                input_tokens=estimated_input_tokens,
                output_tokens=estimated_output_tokens,
                cost_usd=estimated_cost
            )
        
        return {"status": "OPERATIONAL", "cost": estimated_cost}
        
    except Exception as e:
        error_str = str(e).strip().split('\n')[0]
        if "404" in error_str or "400" in error_str or "method is not supported" in error_str.lower():
            return {"status": "UNSUPPORTED", "cost": 0.0}
        return {"status": "ERROR", "details": error_str, "cost": 0.0}

def generate_enhanced_json_report(audit_results: List[Dict[str, Any]], token_calculator: TokenCalculatorTool):
    """Generate enhanced JSON report with cost analysis."""
    op_models = [r for r in audit_results if any(v["status"] == "OPERATIONAL" for v in r["assessed_capabilities"].values())]
    
    # Calculate total audit costs if available
    total_audit_cost = sum(
        r.get("cost_analysis", {}).get("total_cost", 0) 
        for r in audit_results
    )
    
    final_report = {
        "report_metadata": {
            "timestamp_utc": strftime("%Y-%m-%dT%H:%M:%SZ", gmtime()), 
            "total_models_discovered": len(audit_results), 
            "total_operational_models": len(op_models),
            "total_audit_cost_usd": round(total_audit_cost, 6),
            "cost_tracking_enabled": any("cost_analysis" in r for r in audit_results),
            "generated_by": "audit_gemini_enhanced"
        }, 
        "full_audit_results": audit_results
    }
    
    output_dir = project_root / "data" / "gemini"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{strftime('%Y%m%d-%H%M%S')}.gemini_audit_enhanced_report.json"
    
    with open(report_path, "w", encoding="utf-8") as f: 
        json.dump(final_report, f, indent=2)
    
    print(f"\n--- Enhanced Audit Complete ---")
    print(f" {Colors.OKGREEN}✅  {len(op_models)} models are OPERATIONAL for at least one capability.{Colors.ENDC}")
    if total_audit_cost > 0:
        print(f" 💰  Total audit cost: ${total_audit_cost:.6f}")
    print(f" 📄  Detailed report saved to: {Colors.OKBLUE}{report_path}{Colors.ENDC}")

async def update_yaml_config_enhanced(audit_results: List[Dict[str, Any]], 
                                    token_calculator: TokenCalculatorTool, 
                                    sync_pricing: bool = False):
    """Enhanced YAML config update with pricing synchronization."""
    logging.info("Starting enhanced configuration update process...")
    config_path = project_root / "models" / "gemini.yaml"
    existing_config = load_yaml_config(config_path)
    
    operational_models = sorted(
        [r for r in audit_results if any(v["status"] == "OPERATIONAL" for v in r["assessed_capabilities"].values())], 
        key=lambda x: len([c for c in x["assessed_capabilities"].values() if c["status"] == "OPERATIONAL"]), 
        reverse=True
    )
    
    if not operational_models: 
        logging.error("No operational models found. Cannot update YAML config.")
        return
    
    new_config = {}
    for model_data in operational_models:
        model_id = model_data["internal_id"]
        api_name = model_data['api_name']
        
        # Start with existing configuration or defaults
        model_config = existing_config.get(model_id, {
            'task_scores': {
                'reasoning': 0.7, 'code_generation': 0.7, 'writing': 0.7, 
                'simple_chat': 0.7, 'data_analysis': 0.7, 'speed_sensitive': 0.7
            }, 
            'cost_per_kilo_input_tokens': 0.0, 
            'cost_per_kilo_output_tokens': 0.0
        })
        
        # Update with audit results
        model_config['api_name'] = api_name
        model_config['assessed_capabilities'] = [
            k for k,v in model_data['assessed_capabilities'].items() 
            if v['status'] == 'OPERATIONAL'
        ]
        
        # Sync pricing from centralized database if requested
        if sync_pricing:
            pricing_info = await _get_pricing_for_model(token_calculator, api_name)
            if pricing_info:
                # Convert from per-million to per-thousand tokens
                if 'input' in pricing_info:
                    model_config['cost_per_kilo_input_tokens'] = pricing_info['input'] / 1000
                elif 'input_standard' in pricing_info:
                    model_config['cost_per_kilo_input_tokens'] = pricing_info['input_standard'] / 1000
                
                if 'output' in pricing_info:
                    model_config['cost_per_kilo_output_tokens'] = pricing_info['output'] / 1000
                elif 'output_standard' in pricing_info:
                    model_config['cost_per_kilo_output_tokens'] = pricing_info['output_standard'] / 1000
                
                # Add pricing metadata
                model_config['pricing_source'] = 'centralized_database'
                model_config['pricing_last_updated'] = strftime("%Y-%m-%d")
        
        new_config[model_id] = model_config
    
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f: 
            yaml.dump(new_config, f, sort_keys=False, default_flow_style=False, width=120)
        
        logging.info(f"Successfully updated mindX configuration at {config_path}")
        sync_message = " with synchronized pricing" if sync_pricing else ""
        print(f"\n{Colors.OKGREEN}✅ `gemini.yaml` has been successfully updated with {len(new_config)} operational models{sync_message}.{Colors.ENDC}")
        
        if sync_pricing:
            updated_models = sum(1 for config in new_config.values() if config.get('cost_per_kilo_input_tokens', 0) > 0)
            print(f"   💰 Pricing synchronized for {updated_models} models")
            
    except Exception as e:
        logging.error(f"Failed to write updated config to {config_path}: {e}", exc_info=True)

async def _get_pricing_for_model(token_calculator: TokenCalculatorTool, model_name: str) -> Optional[Dict[str, Any]]:
    """Get pricing information for a model from the token calculator."""
    try:
        # Use the token calculator's internal pricing lookup
        provider = token_calculator._detect_provider(model_name)
        return token_calculator._get_model_pricing(provider, model_name)
    except Exception as e:
        logging.warning(f"Could not get pricing for {model_name}: {e}")
        return None

def load_yaml_config(config_path: Path) -> Dict[str, Any]:
    """Load existing YAML configuration."""
    try:
        if not config_path.exists(): 
            return {}
        with open(config_path, "r") as f: 
            return yaml.safe_load(f) or {}
    except Exception as e: 
        logging.error(f"Error parsing existing gemini.yaml: {e}")
        return {}

if __name__ == "__main__":
    sys.exit(main()) 