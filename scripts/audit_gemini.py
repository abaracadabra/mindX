# mindx/scripts/audit_gemini.py (c) 2025 PYTHAI MIT license
"""
Definitive, Multimodal Capability-Aware Auditing and Configuration Tool for
Google Gemini models in the mindX Augmentic Intelligence Framework.

This tool discovers all available models, assesses each for its true operational
capabilities, and produces professional, machine-readable reports and clean
configurations for deployment. It features a clean, professional UI with a
contained, single-line status indicator that updates sequentially for each model.

Usage (from project root):
- To audit:   `python3 scripts/audit_gemini.py --test-all`
- To update:  `python3 scripts/audit_gemini.py --update-config`
"""
import sys
import asyncio
import argparse
import logging
import os
import ast
import json
from pathlib import Path
from time import strftime, gmtime
from typing import Dict, Any, List, Optional
from io import BytesIO

# --- Global Imports & Prerequisite Checks ---
try:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    from llm.rate_limiter import RateLimiter
    import google.generativeai as genai
    from dotenv import load_dotenv
    from PIL import Image
    import numpy as np
    from scipy.io.wavfile import write as write_wav
    import yaml
    from agents.memory_agent import MemoryAgent
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
    parser = argparse.ArgumentParser(description="MindX Gemini Model Auditor", formatter_class=argparse.RawTextHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--test-all", action="store_true", help="Assess all available models and produce a JSON report.")
    group.add_argument("--update-config", action="store_true", help="Merge live audit results with existing gemini.yaml and update it.")
    args = parser.parse_args(argv)
    
    memory_agent = MemoryAgent()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [GeminiAuditTool] - %(levelname)s - %(message)s')
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.ERROR)

    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: logging.critical("Error: GEMINI_API_KEY not found."); return 1

    genai.configure(api_key=api_key)
    try:
        print("\n\n\n")
        audit_results = asyncio.run(_perform_full_audit())
        if not audit_results: logging.critical("Audit failed. Aborting."); return 1
        if args.test_all:
            generate_json_report(audit_results)
            asyncio.run(memory_agent.log_process(
        process_name="gemini_audit",
        data={"action": "test-all", "report_generated": True, "operational_models": len([r for r in audit_results if any(v["status"] == "OPERATIONAL" for v in r["assessed_capabilities"].values())])},
        metadata={"agent_id": "audit_gemini_script"}
    ))
        elif args.update_config:
            update_yaml_config(audit_results)
            asyncio.run(memory_agent.log_process("gemini_audit", {"action": "update-config", "config_updated": True, "operational_models": len([r for r in audit_results if any(v["status"] == "OPERATIONAL" for v in r["assessed_capabilities"].values())])}))
    except KeyboardInterrupt: print("\nAudit interrupted by user."); return 1
    except Exception as e: logging.critical(f"A critical error occurred: {e}", exc_info=True); return 1
    return 0

def load_yaml_config(config_path: Path) -> Dict[str, Any]:
    try:
        if not config_path.exists(): return {}
        with open(config_path, "r") as f: return yaml.safe_load(f) or {}
    except Exception as e: logging.error(f"Error parsing existing gemini.yaml: {e}"); return {}

async def _run_test(test_func, *args, **kwargs) -> Dict[str, Any]:
    try:
        await asyncio.to_thread(test_func, *args, **kwargs)
        return {"status": "OPERATIONAL"}
    except Exception as e:
        error_str = str(e).strip().split('\n')[0]
        if "404" in error_str or "400" in error_str or "method is not supported" in error_str.lower():
            return {"status": "UNSUPPORTED"}
        return {"status": "ERROR", "details": error_str}

async def _perform_full_audit() -> List[Dict[str, Any]]:
    limiter = RateLimiter(requests_per_minute=25, status_callback=rate_limiter_ui_callback)
    
    print_status_box(f"{Colors.OKGREEN}Discovering models from Google API...{Colors.ENDC}")
    try:
        live_models = list(genai.list_models())
    except Exception as e:
        logging.critical(f"Could not retrieve model list from API: {e}"); return []

    audit_results = []
    total_models = len(live_models)
    
    for i, model in enumerate(live_models):
        sdk_model_name = model.name.replace("models/", "")
        progress_bar = f"[{int(((i+1)/total_models)*20)*'='}>{(20-int(((i+1)/total_models)*20))*' '}]"
        print_status_box(f"Progress: {progress_bar} {i+1}/{total_models}", f"Assessing: {sdk_model_name}")

        result = await _assess_single_model(model, limiter)
        audit_results.append(result)

    print_status_box(f"{Colors.OKGREEN}Assessment Complete.{Colors.ENDC}", f"Processed {total_models} models.", "")
    sys.stdout.write("\033[F\033[K" * 4) # Clean up the status box area
    
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'Model API Name':<45} {'Text':<12} {'Vision':<12} {'Embedding':<12}{Colors.ENDC}")
    print("-" * 85)
    for result in sorted(audit_results, key=lambda x: x['api_name']):
        print(f"{Colors.BOLD}{result['api_name']:<45}{Colors.ENDC}", end="", flush=True)
        for cap in ["text", "vision", "embedding"]:
            status = result["assessed_capabilities"][cap]['status']
            color = Colors.OKGREEN if status == 'OPERATIONAL' else Colors.FAIL if status == 'ERROR' else Colors.GREY
            print(f"{color}{status:<12}{Colors.ENDC}", end="", flush=True)
        print()

    return audit_results

async def _assess_single_model(model, limiter) -> Dict[str, Any]:
    sdk_model_name = model.name.replace("models/", "")
    await limiter.wait()
    result_entry = {"internal_id": f"gemini/{sdk_model_name}", "api_name": sdk_model_name, "display_name": model.display_name, "version": model.version, "assessed_capabilities": {}}
    
    # Use the correct methods for testing
    text_test = _run_test(genai.GenerativeModel(sdk_model_name).generate_content, "test")
    vision_test = _run_test(genai.GenerativeModel(sdk_model_name).generate_content, [Image.new('RGB', (1,1)), "test"])
    embedding_test = _run_test(genai.embed_content, model=model.name, content="test")

    tests = {"text": text_test, "vision": vision_test, "embedding": embedding_test}
    results = await asyncio.gather(*tests.values())
    result_entry["assessed_capabilities"] = dict(zip(tests.keys(), results))
    return result_entry

def generate_json_report(audit_results: List[Dict[str, Any]]):
    op_models = [r for r in audit_results if any(v["status"] == "OPERATIONAL" for v in r["assessed_capabilities"].values())]
    final_report = {"report_metadata": {"timestamp_utc": strftime("%Y-%m-%dT%H:%M:%SZ", gmtime()), "total_models_discovered": len(audit_results), "total_operational_models": len(op_models)}, "full_audit_results": audit_results}
    output_dir = project_root / "data" / "gemini"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{strftime('%Y%m%d-%H%M%S')}.gemini_audit_report.json"
    with open(report_path, "w", encoding="utf-8") as f: json.dump(final_report, f, indent=2)
    print(f"\n--- Audit Complete ---")
    print(f" {Colors.OKGREEN}✅  {len(op_models)} models are OPERATIONAL for at least one capability.{Colors.ENDC}")
    print(f" 📄  A detailed, machine-readable report has been saved to: {Colors.OKBLUE}{report_path}{Colors.ENDC}")

def update_yaml_config(audit_results: List[Dict[str, Any]]):
    logging.info("Starting configuration update process...")
    config_path = project_root / "models" / "gemini.yaml"
    existing_config = load_yaml_config(config_path)
    operational_models = sorted([r for r in audit_results if any(v["status"] == "OPERATIONAL" for v in r["assessed_capabilities"].values())], key=lambda x: len([c for c in x["assessed_capabilities"].values() if c["status"] == "OPERATIONAL"]), reverse=True)
    if not operational_models: logging.error("No operational models found. Cannot update YAML config."); return
    new_config = {}
    for model_data in operational_models:
        model_id = model_data["internal_id"]
        new_config[model_id] = existing_config.get(model_id, {'task_scores': {'reasoning': 0.7, 'code_generation': 0.7, 'writing': 0.7, 'simple_chat': 0.7, 'data_analysis': 0.7, 'speed_sensitive': 0.7}, 'cost_per_kilo_input_tokens': 0.0, 'cost_per_kilo_output_tokens': 0.0})
        new_config[model_id]['api_name'] = model_data['api_name']
        new_config[model_id]['assessed_capabilities'] = [k for k,v in model_data['assessed_capabilities'].items() if v['status'] == 'OPERATIONAL']
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f: yaml.dump(new_config, f, sort_keys=False, default_flow_style=False, width=120)
        logging.info(f"Successfully updated mindX configuration at {config_path}")
        print(f"\n{Colors.OKGREEN}✅ `gemini.yaml` has been successfully updated with {len(new_config)} operational models.{Colors.ENDC}")
    except Exception as e:
        logging.error(f"Failed to write updated config to {config_path}: {e}", exc_info=True)

if __name__ == "__main__":
    sys.exit(main())
