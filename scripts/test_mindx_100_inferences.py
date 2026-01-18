#!/usr/bin/env python3
"""
Test mindX with 100+ Input Responses

This script:
1. Tests Ollama connection
2. Starts mindX system
3. Generates 100+ inference requests
4. Tests inference optimization system
5. Collects comprehensive metrics
"""

import asyncio
import os
import sys
import time
import random
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.config import Config
from utils.logging_config import setup_logging, get_logger
from agents.memory_agent import MemoryAgent
from agents.core.belief_system import BeliefSystem
from agents.orchestration.coordinator_agent import get_coordinator_agent_mindx_async
from agents.orchestration.startup_agent import StartupAgent
from agents.core.mindXagent import MindXAgent
from api.ollama_url import create_ollama_api

# Setup logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)

# Ollama configuration
OLLAMA_HOST = "10.0.0.155"
OLLAMA_PORT = 18080
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# Test configuration
MIN_INFERENCES = 100
MAX_CONCURRENT = 5  # Number of concurrent requests


async def test_ollama_connection():
    """Test connection to Ollama server"""
    logger.info("="*70)
    logger.info("Testing Ollama Connection")
    logger.info("="*70)
    
    try:
        ollama_api = create_ollama_api(base_url=OLLAMA_BASE_URL)
        models = await ollama_api.list_models()
        
        if models:
            logger.info(f"✓ Ollama connection successful: {OLLAMA_BASE_URL}")
            logger.info(f"✓ Found {len(models)} available models")
            return {
                "connected": True,
                "base_url": OLLAMA_BASE_URL,
                "models": [m.get("name") for m in models],
                "models_count": len(models)
            }
        else:
            logger.warning("⚠ Ollama connected but no models found")
            return {
                "connected": True,
                "base_url": OLLAMA_BASE_URL,
                "models": [],
                "models_count": 0
            }
    except Exception as e:
        logger.error(f"✗ Ollama connection failed: {e}")
        return {
            "connected": False,
            "base_url": OLLAMA_BASE_URL,
            "error": str(e),
            "models": [],
            "models_count": 0
        }


async def initialize_agents():
    """Initialize all required agents"""
    logger.info("="*70)
    logger.info("Initializing Agents")
    logger.info("="*70)
    
    config = Config()
    memory_agent = MemoryAgent(config=config)
    belief_system = BeliefSystem()
    
    # Initialize Coordinator
    coordinator = await get_coordinator_agent_mindx_async(
        memory_agent=memory_agent,
        config_override=config,
        belief_system=belief_system
    )
    logger.info("✓ Coordinator initialized")
    
    # Initialize Startup Agent
    startup_agent = StartupAgent(
        coordinator_agent=coordinator,
        memory_agent=memory_agent,
        config=config
    )
    logger.info("✓ Startup Agent initialized")
    
    # Initialize MindXAgent
    mindx_agent = await MindXAgent.get_instance(
        agent_id="mindx_meta_agent",
        config=config,
        memory_agent=memory_agent,
        belief_system=belief_system
    )
    logger.info("✓ MindXAgent initialized")
    
    # Link startup_agent to mindXagent
    startup_agent.mindxagent = mindx_agent
    logger.info("✓ Startup Agent linked to MindXAgent")
    
    return {
        "config": config,
        "memory_agent": memory_agent,
        "coordinator": coordinator,
        "startup_agent": startup_agent,
        "mindx_agent": mindx_agent
    }


def generate_test_messages(count: int) -> List[str]:
    """Generate diverse test messages for inference"""
    base_messages = [
        "Analyze the current state of the mindX system.",
        "What are the key components of the mindX architecture?",
        "Explain how the BDI agent works.",
        "Describe the memory system architecture.",
        "What is the purpose of the Coordinator Agent?",
        "How does the inference optimization system work?",
        "What are the main features of mindX?",
        "Explain the autonomous improvement cycle.",
        "Describe the agent registry system.",
        "What is the role of the Guardian Agent?",
        "How does mindX handle identity management?",
        "Explain the strategic evolution pipeline.",
        "What is THOT knowledge?",
        "Describe the Ollama integration.",
        "How does the belief system work?",
        "What are the monitoring capabilities?",
        "Explain the tool ecosystem.",
        "Describe the API architecture.",
        "What is the purpose of the Mastermind Agent?",
        "How does mindX ensure security?",
    ]
    
    messages = []
    for i in range(count):
        base = random.choice(base_messages)
        variation = f"Request {i+1}: {base}"
        messages.append(variation)
    
    return messages


async def run_single_inference(
    mindx_agent: MindXAgent,
    message: str,
    request_id: int,
    results: List[Dict[str, Any]]
):
    """Run a single inference request"""
    start_time = time.time()
    try:
        result = await mindx_agent.chat_with_ollama(
            message=message,
            max_tokens=100,
            temperature=0.7
        )
        
        latency = time.time() - start_time
        success = result.get("success", False)
        
        results.append({
            "request_id": request_id,
            "success": success,
            "latency": latency,
            "model": result.get("model", "unknown"),
            "tokens": result.get("tokens", 0),
            "error": result.get("error") if not success else None
        })
        
        if success:
            logger.debug(f"Request {request_id}: ✓ {latency:.2f}s")
        else:
            logger.warning(f"Request {request_id}: ✗ {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        latency = time.time() - start_time
        logger.error(f"Request {request_id}: Exception - {e}")
        results.append({
            "request_id": request_id,
            "success": False,
            "latency": latency,
            "error": str(e)
        })


async def run_batch_inferences(
    mindx_agent: MindXAgent,
    messages: List[str],
    batch_size: int = MAX_CONCURRENT
):
    """Run inferences in batches with concurrency control"""
    results: List[Dict[str, Any]] = []
    total = len(messages)
    
    logger.info(f"Running {total} inferences in batches of {batch_size}")
    
    for i in range(0, total, batch_size):
        batch = messages[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size
        
        logger.info(f"Batch {batch_num}/{total_batches}: Processing {len(batch)} requests...")
        
        tasks = []
        for j, message in enumerate(batch):
            request_id = i + j + 1
            task = run_single_inference(mindx_agent, message, request_id, results)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Progress update
        completed = len(results)
        success_count = sum(1 for r in results if r.get("success"))
        logger.info(f"Progress: {completed}/{total} completed ({success_count} successful)")
        
        # Small delay between batches to avoid overwhelming the system
        if i + batch_size < total:
            await asyncio.sleep(0.5)
    
    return results


async def generate_100_inferences(mindx_agent: MindXAgent):
    """Generate 100+ inference requests"""
    logger.info("="*70)
    logger.info(f"Generating {MIN_INFERENCES}+ Inference Requests")
    logger.info("="*70)
    
    # Verify Ollama connection
    if not mindx_agent.ollama_chat_manager or not mindx_agent.ollama_chat_manager.connected:
        logger.warning("⚠ Ollama Chat Manager not connected, initializing...")
        if mindx_agent.ollama_chat_manager:
            await mindx_agent.ollama_chat_manager.initialize()
        else:
            await mindx_agent._init_ollama_chat_manager()
    
    # Generate test messages
    messages = generate_test_messages(MIN_INFERENCES)
    logger.info(f"Generated {len(messages)} test messages")
    
    # Run inferences
    start_time = time.time()
    results = await run_batch_inferences(mindx_agent, messages, batch_size=MAX_CONCURRENT)
    total_time = time.time() - start_time
    
    # Analyze results
    success_count = sum(1 for r in results if r.get("success"))
    failure_count = len(results) - success_count
    avg_latency = sum(r.get("latency", 0) for r in results) / len(results) if results else 0
    total_tokens = sum(r.get("tokens", 0) for r in results)
    
    # Get optimization metrics
    opt_metrics = mindx_agent.get_inference_optimization_metrics()
    
    logger.info("")
    logger.info("="*70)
    logger.info("Inference Test Results")
    logger.info("="*70)
    logger.info(f"Total requests: {len(results)}")
    logger.info(f"Successful: {success_count} ({success_count/len(results)*100:.1f}%)")
    logger.info(f"Failed: {failure_count} ({failure_count/len(results)*100:.1f}%)")
    logger.info(f"Total time: {total_time:.2f}s")
    logger.info(f"Average latency: {avg_latency:.2f}s")
    logger.info(f"Requests/second: {len(results)/total_time:.2f}")
    logger.info(f"Total tokens: {total_tokens}")
    logger.info("")
    
    if opt_metrics.get("status") != "no_data":
        logger.info("Optimization Metrics:")
        logger.info(f"  Current frequency: {opt_metrics.get('current_frequency', 'N/A')} rpm")
        logger.info(f"  Optimal frequency: {opt_metrics.get('optimal_frequency', 'N/A')} rpm")
        logger.info(f"  Total requests tracked: {opt_metrics.get('total_requests', 0)}")
        logger.info(f"  Recent success rate: {opt_metrics.get('recent_success_rate', 0)*100:.1f}%")
        logger.info(f"  Recent avg latency: {opt_metrics.get('recent_avg_latency_ms', 0):.0f}ms")
        logger.info(f"  Recent throughput: {opt_metrics.get('recent_throughput', 0):.2f} tokens/s")
    else:
        logger.info("Optimization: Data collection in progress...")
    
    logger.info("="*70)
    
    return {
        "total_requests": len(results),
        "success_count": success_count,
        "failure_count": failure_count,
        "total_time": total_time,
        "avg_latency": avg_latency,
        "total_tokens": total_tokens,
        "results": results,
        "optimization_metrics": opt_metrics
    }


async def main():
    """Main test execution"""
    logger.info("="*70)
    logger.info("MindX 100+ Inference Test")
    logger.info("="*70)
    
    try:
        # Step 1: Test Ollama connection
        ollama_result = await test_ollama_connection()
        
        if not ollama_result.get("connected"):
            logger.error("Cannot proceed without Ollama connection")
            return
        
        # Step 2: Initialize agents
        agents = await initialize_agents()
        
        # Step 3: Send startup information
        logger.info("="*70)
        logger.info("Sending Startup Information to MindXAgent")
        logger.info("="*70)
        
        startup_info = {
            "ollama_connected": ollama_result.get("connected", False),
            "ollama_base_url": ollama_result.get("base_url"),
            "ollama_models": ollama_result.get("models", []),
            "models_count": ollama_result.get("models_count", 0),
            "startup_timestamp": time.time(),
            "terminal_log_path": str(agents["startup_agent"].terminal_log_path)
        }
        
        terminal_log = await agents["startup_agent"].read_terminal_startup_log()
        if terminal_log.get("log_exists"):
            startup_info["terminal_log"] = {
                "errors_count": len(terminal_log.get("errors", [])),
                "warnings_count": len(terminal_log.get("warnings", [])),
            }
        
        await agents["mindx_agent"].receive_startup_information(startup_info)
        logger.info("✓ Startup information sent to MindXAgent")
        
        # Step 4: Verify inference connection
        if not agents["mindx_agent"].ollama_chat_manager:
            await agents["mindx_agent"]._init_ollama_chat_manager()
        
        if not agents["mindx_agent"].ollama_chat_manager.connected:
            await agents["mindx_agent"].ollama_chat_manager.initialize()
        
        models = await agents["mindx_agent"].get_available_ollama_models()
        if not models:
            logger.error("✗ No models available")
            return
        
        logger.info(f"✓ ML Inference ready: {len(models)} models available")
        
        # Step 5: Generate 100+ inferences
        test_results = await generate_100_inferences(agents["mindx_agent"])
        
        # Final summary
        logger.info("")
        logger.info("="*70)
        logger.info("Test Complete")
        logger.info("="*70)
        logger.info(f"✓ Total inferences: {test_results['total_requests']}")
        logger.info(f"✓ Success rate: {test_results['success_count']/test_results['total_requests']*100:.1f}%")
        logger.info(f"✓ Average latency: {test_results['avg_latency']:.2f}s")
        logger.info(f"✓ Total tokens: {test_results['total_tokens']}")
        logger.info("="*70)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
