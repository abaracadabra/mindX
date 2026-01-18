#!/usr/bin/env python3
"""
Test mindX Startup with Connection Test and Inference Optimization

This script:
1. Tests Ollama connection
2. Starts mindX system
3. Ensures startup_agent sends logs to mindXagent
4. Verifies ML inference connection
5. Starts sliding scale optimization for inference frequency
"""

import asyncio
import os
import sys
import time
from pathlib import Path

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


async def test_inference_connection(mindx_agent: MindXAgent):
    """Test that mindXagent is connected to ML inference"""
    logger.info("="*70)
    logger.info("Testing ML Inference Connection")
    logger.info("="*70)
    
    try:
        # Check if Ollama chat manager is initialized
        if not mindx_agent.ollama_chat_manager:
            logger.warning("⚠ Ollama Chat Manager not initialized, initializing now...")
            await mindx_agent._init_ollama_chat_manager()
        
        if not mindx_agent.ollama_chat_manager:
            logger.error("✗ Ollama Chat Manager not available")
            return False
        
        if not mindx_agent.ollama_chat_manager.connected:
            logger.warning("⚠ Ollama Chat Manager not connected, attempting connection...")
            connected = await mindx_agent.ollama_chat_manager.initialize()
            if not connected:
                logger.error("✗ Failed to connect Ollama Chat Manager")
                return False
        
        # Get available models
        models = await mindx_agent.get_available_ollama_models()
        if not models:
            logger.error("✗ No models available")
            return False
        
        logger.info(f"✓ ML Inference connected: {len(models)} models available")
        logger.info(f"  Models: {', '.join([m.get('name', 'unknown') for m in models[:5]])}")
        
        # Test a simple inference
        logger.info("Testing inference with simple message...")
        result = await mindx_agent.chat_with_ollama(
            message="Hello, this is a connection test. Please respond briefly.",
            max_tokens=50,
            temperature=0.7
        )
        
        if result.get("success"):
            logger.info(f"✓ Inference test successful")
            logger.info(f"  Model: {result.get('model')}")
            logger.info(f"  Latency: {result.get('latency', 0):.2f}s")
            logger.info(f"  Response: {result.get('content', '')[:100]}...")
            return True
        else:
            logger.error(f"✗ Inference test failed: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Inference connection test failed: {e}", exc_info=True)
        return False


async def start_optimization(mindx_agent: MindXAgent):
    """Start inference frequency optimization"""
    logger.info("="*70)
    logger.info("Starting Inference Frequency Optimization")
    logger.info("="*70)
    
    try:
        if not mindx_agent.ollama_chat_manager or not mindx_agent.ollama_chat_manager.inference_optimizer:
            logger.warning("⚠ Inference optimizer not initialized")
            return
        
        optimizer = mindx_agent.ollama_chat_manager.inference_optimizer
        
        # Get current frequency
        current_freq = optimizer.get_current_frequency()
        logger.info(f"✓ Optimization active")
        logger.info(f"  Current frequency: {current_freq:.1f} requests/minute")
        logger.info(f"  Range: {optimizer.min_frequency:.1f} - {optimizer.max_frequency:.1f} rpm")
        logger.info(f"  Window duration: {optimizer.window_duration}s")
        logger.info(f"  Optimization interval: {optimizer.optimization_interval}s")
        
        # Get metrics summary
        metrics = optimizer.get_metrics_summary()
        logger.info(f"  Metrics: {metrics}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to start optimization: {e}")
        return False


async def simulate_inference_load(mindx_agent: MindXAgent, duration: int = 60):
    """Simulate inference load to collect optimization data"""
    logger.info("="*70)
    logger.info(f"Simulating Inference Load ({duration}s)")
    logger.info("="*70)
    
    if not mindx_agent.ollama_chat_manager or not mindx_agent.ollama_chat_manager.inference_optimizer:
        logger.warning("⚠ Cannot simulate load: optimizer not available")
        return
    
    optimizer = mindx_agent.ollama_chat_manager.inference_optimizer
    start_time = time.time()
    request_count = 0
    
    try:
        while time.time() - start_time < duration:
            # Get current optimal frequency
            freq = optimizer.get_current_frequency()
            interval = 60.0 / freq  # Seconds between requests
            
            # Send test message
            result = await mindx_agent.chat_with_ollama(
                message=f"Test message {request_count + 1}",
                max_tokens=20,
                temperature=0.5
            )
            
            request_count += 1
            
            if result.get("success"):
                logger.debug(f"Request {request_count}: {result.get('latency', 0):.2f}s")
            else:
                logger.warning(f"Request {request_count} failed: {result.get('error')}")
            
            # Wait for next request based on frequency
            await asyncio.sleep(interval)
            
    except asyncio.CancelledError:
        logger.info("Load simulation cancelled")
    except Exception as e:
        logger.error(f"Load simulation error: {e}")
    
    logger.info(f"✓ Completed {request_count} requests in {time.time() - start_time:.1f}s")
    
    # Get final metrics
    metrics = optimizer.get_metrics_summary()
    logger.info(f"Final metrics: {metrics}")


async def main():
    """Main test execution"""
    logger.info("="*70)
    logger.info("MindX Startup Test with Inference Optimization")
    logger.info("="*70)
    
    try:
        # Step 1: Test Ollama connection
        ollama_result = await test_ollama_connection()
        
        if not ollama_result.get("connected"):
            logger.error("Cannot proceed without Ollama connection")
            return
        
        # Step 2: Initialize agents
        agents = await initialize_agents()
        
        # Step 3: Have startup_agent send startup info to mindXagent
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
        
        # Read terminal log if available
        terminal_log = await agents["startup_agent"].read_terminal_startup_log()
        if terminal_log.get("log_exists"):
            startup_info["terminal_log"] = {
                "errors_count": len(terminal_log.get("errors", [])),
                "warnings_count": len(terminal_log.get("warnings", [])),
                "sample_errors": terminal_log.get("errors", [])[:5],
                "sample_warnings": terminal_log.get("warnings", [])[:5]
            }
        
        # Send to mindXagent
        await agents["mindx_agent"].receive_startup_information(startup_info)
        logger.info("✓ Startup information sent to MindXAgent")
        
        # Step 4: Test ML inference connection
        inference_connected = await test_inference_connection(agents["mindx_agent"])
        
        if not inference_connected:
            logger.error("Cannot proceed without ML inference connection")
            return
        
        # Step 5: Start optimization
        optimization_started = await start_optimization(agents["mindx_agent"])
        
        if optimization_started:
            # Step 6: Run short load simulation to collect data
            logger.info("")
            logger.info("Running short load simulation to collect optimization data...")
            await simulate_inference_load(agents["mindx_agent"], duration=30)
        
        # Summary
        logger.info("")
        logger.info("="*70)
        logger.info("Test Summary")
        logger.info("="*70)
        logger.info(f"✓ Ollama connection: {ollama_result.get('connected')}")
        logger.info(f"✓ Agents initialized")
        logger.info(f"✓ Startup info sent to MindXAgent")
        logger.info(f"✓ ML inference connected: {inference_connected}")
        logger.info(f"✓ Optimization started: {optimization_started}")
        
        # Get optimization metrics
        opt_metrics = agents["mindx_agent"].get_inference_optimization_metrics()
        if opt_metrics.get("status") != "no_data":
            logger.info(f"✓ Current frequency: {opt_metrics.get('current_frequency', 'N/A')} rpm")
            logger.info(f"✓ Optimal frequency: {opt_metrics.get('optimal_frequency', 'N/A')} rpm")
            logger.info(f"✓ Total requests: {opt_metrics.get('total_requests', 0)}")
            logger.info(f"✓ Recent success rate: {opt_metrics.get('recent_success_rate', 0)*100:.1f}%")
            logger.info(f"✓ Recent avg latency: {opt_metrics.get('recent_avg_latency_ms', 0):.0f}ms")
        else:
            logger.info("✓ Optimization data collection in progress...")
        
        logger.info("="*70)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
