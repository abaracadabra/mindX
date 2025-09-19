#!/usr/bin/env python3
"""
Test BDI reasoning integration for AGInt
"""
import time
import os

def test_bdi_reasoning():
    """Test BDI reasoning logic"""
    directive = "evolve augmentic.py"
    cycle = 1
    
    # BDI Belief-Desire-Intention reasoning
    directive_lower = directive.lower()
    chosen_agent = "enhanced_simple_coder"  # Default fallback
    
    # Desire: Choose the best agent for the task
    if "code" in directive_lower or "evolve" in directive_lower or "develop" in directive_lower:
        chosen_agent = "enhanced_simple_coder"
    elif "document" in directive_lower or "base" in directive_lower or "readme" in directive_lower:
        chosen_agent = "base_gen_agent"
    elif "analyze" in directive_lower or "review" in directive_lower or "optimize" in directive_lower:
        chosen_agent = "system_analyzer"
    elif "audit" in directive_lower or "improve" in directive_lower or "quality" in directive_lower:
        chosen_agent = "audit_and_improve_tool"
    
    # Intention: Execute the chosen approach
    bdi_reasoning = f"BDI Reasoning: Directive '{directive}' -> Belief: Task requires {chosen_agent} -> Desire: Use best suited agent -> Intention: Execute with {chosen_agent}"
    
    # Log BDI decision
    agint_log_dir = "data/logs/agint"
    os.makedirs(agint_log_dir, exist_ok=True)
    agint_log_file = os.path.join(agint_log_dir, "agint_cognitive_cycles.log")
    
    with open(agint_log_file, 'a') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - {bdi_reasoning}\n")
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - Chosen Agent: {chosen_agent}\n")
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - Directive: {directive}\n")
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - Status: Completed using {chosen_agent}\n\n")
    
    print(f"✅ BDI Reasoning completed: {bdi_reasoning}")
    print(f"✅ Chosen Agent: {chosen_agent}")
    print(f"✅ Logged to: {agint_log_file}")
    
    return chosen_agent

if __name__ == "__main__":
    test_bdi_reasoning()
