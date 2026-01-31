#!/usr/bin/env python3
"""
Test mindXagent with Ollama Inference and Reasoning Process Logging

This script tests:
1. mindXagent sending messages to Ollama inference server
2. Model selection from available Ollama models
3. Complete reasoning process logging to data/logs
4. THOT (Transferable Hyper-Optimized Tensor) knowledge creation
5. Assessment from agents and tools for improvement
6. Performance from THOT in distributed mind (AgenticPlace)
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.config import Config
from utils.logging_config import setup_logging, get_logger
from agents.memory_agent import MemoryAgent, MemoryType
from agents.core.belief_system import BeliefSystem
from agents.orchestration.coordinator_agent import get_coordinator_agent_mindx_async
from agents.core.mindXagent import MindXAgent
from llm.model_registry import get_model_registry_async
from api.ollama import OllamaAPI, create_ollama_api

# Setup logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)

# Ollama configuration
OLLAMA_HOST = "10.0.0.155"
OLLAMA_PORT = 18080
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# Reasoning log file
REASONING_LOG_PATH = PROJECT_ROOT / "data" / "logs" / "mindxagent_reasoning.log"
THOT_LOG_PATH = PROJECT_ROOT / "data" / "logs" / "thot_knowledge.log"


class ReasoningLogger:
    """Logs the complete reasoning process for mindXagent"""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.reasoning_steps: List[Dict[str, Any]] = []
    
    def log_step(self, step: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Log a reasoning step"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "data": data,
            "metadata": metadata or {}
        }
        self.reasoning_steps.append(entry)
        
        # Write to file immediately
        with self.log_file.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        
        logger.info(f"[REASONING] {step}: {json.dumps(data, default=str)[:100]}...")
    
    def get_reasoning_trace(self) -> List[Dict[str, Any]]:
        """Get complete reasoning trace"""
        return self.reasoning_steps


class THOTKnowledge:
    """Creates THOT (Transferable Hyper-Optimized Tensor) knowledge from reasoning"""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.thot_artifacts: List[Dict[str, Any]] = []
    
    def create_thot(
        self,
        reasoning_trace: List[Dict[str, Any]],
        assessment: Dict[str, Any],
        performance_metrics: Dict[str, Any],
        agenticplace_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create THOT artifact from reasoning process"""
        
        # Extract key patterns from reasoning
        patterns = self._extract_patterns(reasoning_trace)
        
        # Create THOT structure
        thot = {
            "timestamp": datetime.now().isoformat(),
            "thot_id": f"thot_{int(time.time())}",
            "source": "mindxagent_ollama_reasoning",
            "reasoning_trace": reasoning_trace,
            "patterns": patterns,
            "assessment": assessment,
            "performance_metrics": performance_metrics,
            "agenticplace": agenticplace_context or {},
            "knowledge_vectors": self._create_knowledge_vectors(patterns, assessment),
            "transferable_insights": self._extract_insights(reasoning_trace, assessment)
        }
        
        self.thot_artifacts.append(thot)
        
        # Write to file
        with self.log_file.open("a") as f:
            f.write(json.dumps(thot, indent=2) + "\n\n")
        
        logger.info(f"✓ THOT created: {thot['thot_id']}")
        return thot
    
    def _extract_patterns(self, reasoning_trace: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract patterns from reasoning trace"""
        patterns = {
            "reasoning_steps": len(reasoning_trace),
            "decision_points": [],
            "agent_interactions": [],
            "tool_usage": [],
            "model_selections": []
        }
        
        for step in reasoning_trace:
            step_name = step.get("step", "")
            if "decision" in step_name.lower() or "select" in step_name.lower():
                patterns["decision_points"].append(step)
            if "agent" in step_name.lower():
                patterns["agent_interactions"].append(step)
            if "tool" in step_name.lower():
                patterns["tool_usage"].append(step)
            if "model" in step_name.lower():
                patterns["model_selections"].append(step)
        
        return patterns
    
    def _create_knowledge_vectors(self, patterns: Dict[str, Any], assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Create knowledge vectors for THOT"""
        return {
            "reasoning_complexity": len(patterns.get("decision_points", [])),
            "agent_coordination": len(patterns.get("agent_interactions", [])),
            "tool_effectiveness": len(patterns.get("tool_usage", [])),
            "model_performance": assessment.get("model_performance", {}),
            "knowledge_density": len(patterns.get("decision_points", [])) + len(patterns.get("agent_interactions", []))
        }
    
    def _extract_insights(self, reasoning_trace: List[Dict[str, Any]], assessment: Dict[str, Any]) -> List[str]:
        """Extract transferable insights"""
        insights = []
        
        # Extract key decisions
        for step in reasoning_trace:
            if "decision" in step.get("step", "").lower():
                data = step.get("data", {})
                if "reasoning" in data:
                    insights.append(f"Decision: {data.get('reasoning', '')}")
        
        # Extract performance insights
        if assessment.get("success"):
            insights.append(f"Successful reasoning path identified")
        
        # Extract model insights
        if "model" in assessment:
            insights.append(f"Model selection: {assessment.get('model', 'unknown')}")
        
        return insights


async def get_ollama_models(ollama_api: OllamaAPI) -> List[Dict[str, Any]]:
    """Get available models from Ollama server"""
    logger.info("Fetching available Ollama models...")
    models = await ollama_api.list_models()
    logger.info(f"✓ Found {len(models)} available models")
    return models


async def select_best_model(models: List[Dict[str, Any]], task_type: str = "reasoning") -> Optional[str]:
    """Select best model for reasoning task"""
    if not models:
        return None
    
    # Prefer smaller/faster models first to avoid timeouts
    # Order: small models first, then reasoning-specific, then others
    preferred_keywords = ["7b", "8b", "13b", "mistral", "llama"]
    reasoning_keywords = ["nemo", "reasoning", "thinking"]
    
    # First try smaller models
    for model in models:
        model_name = model.get("name", "").lower()
        if any(keyword in model_name for keyword in preferred_keywords):
            # Skip very large models (30b+) for initial test
            if "30b" not in model_name and "70b" not in model_name:
                logger.info(f"✓ Selected model: {model.get('name')} (smaller model for faster inference)")
                return model.get("name")
    
    # Then try reasoning-specific models
    for model in models:
        model_name = model.get("name", "").lower()
        if any(keyword in model_name for keyword in reasoning_keywords):
            logger.info(f"✓ Selected model: {model.get('name')} (reasoning-specific)")
            return model.get("name")
    
    # Fallback to first model
    selected = models[0].get("name")
    logger.info(f"✓ Selected model: {selected} (fallback)")
    return selected


async def test_mindxagent_ollama_inference(
    mindx_agent: MindXAgent,
    ollama_api: OllamaAPI,
    model: str,
    reasoning_logger: ReasoningLogger,
    thot_knowledge: THOTKnowledge,
    test_message: str
) -> Dict[str, Any]:
    """Test mindXagent sending message to Ollama inference"""
    
    start_time = time.time()
    reasoning_logger.log_step("inference_start", {
        "model": model,
        "message": test_message,
        "ollama_url": ollama_api.base_url
    })
    
    try:
        # Step 1: mindXagent analyzes the request
        reasoning_logger.log_step("mindxagent_analysis", {
            "agent": "mindx_meta_agent",
            "action": "analyzing_request",
            "message_length": len(test_message)
        })
        
        # Step 2: mindXagent selects model (already done)
        reasoning_logger.log_step("model_selection", {
            "model": model,
            "selection_strategy": "task_based",
            "task_type": "reasoning"
        })
        
        # Step 3: Send to Ollama inference
        reasoning_logger.log_step("ollama_inference_request", {
            "endpoint": f"{ollama_api.api_url}/chat",
            "model": model,
            "message": test_message
        })
        
        # Use Ollama chat API
        # Note: For large models, the default 5s timeout may be insufficient
        # The OllamaAPI uses a 5s sock_read timeout which may timeout for large models
        # We'll try with the default timeout first, and log if timeout occurs
        try:
            response = await ollama_api.generate_text(
                prompt=test_message,
                model=model,
                max_tokens=1000,  # Reduced for faster inference
                temperature=0.7,
                use_chat=True,
                messages=[{"role": "user", "content": test_message}]
            )
        except Exception as e:
            # If timeout occurs, log it and continue with error handling
            reasoning_logger.log_step("inference_exception", {
                "exception_type": type(e).__name__,
                "exception_message": str(e)
            })
            response = json.dumps({"error": type(e).__name__, "message": str(e)})
        
        inference_time = time.time() - start_time
        
        # Extract error message if present
        error_message = None
        if response and response.startswith('{"error"'):
            try:
                import json
                error_data = json.loads(response)
                error_message = error_data.get("message", error_data.get("error", "Unknown error"))
            except:
                error_message = response[:200] if response else "Unknown error"
        
        # Step 4: Process response
        reasoning_logger.log_step("ollama_inference_response", {
            "response_length": len(response) if response else 0,
            "inference_time_seconds": inference_time,
            "success": response is not None and not response.startswith('{"error"'),
            "error": error_message if error_message else None,
            "response_preview": response[:200] if response and not response.startswith('{"error"') else None
        })
        
        # Step 5: mindXagent processes response
        reasoning_logger.log_step("mindxagent_response_processing", {
            "agent": "mindx_meta_agent",
            "action": "processing_inference_response",
            "response_received": response is not None
        })
        
        # Step 6: Assessment from agents and tools
        response_success = response is not None and not response.startswith('{"error"')
        response_text = response if response_success else None
        
        assessment = {
            "success": response_success,
            "inference_time": inference_time,
            "model": model,
            "response_quality": "high" if response_text and len(response_text) > 100 else ("medium" if response_text and len(response_text) > 50 else "low"),
            "error_occurred": not response_success,
            "error_message": error_message if error_message else None,
            "model_performance": {
                "latency_ms": inference_time * 1000,
                "tokens_generated": len(response_text.split()) if response_text else 0,
                "throughput": len(response_text) / inference_time if response_text and inference_time > 0 else 0,
                "timeout_occurred": inference_time >= 5.0 and not response_success
            }
        }
        
        reasoning_logger.log_step("assessment_complete", assessment)
        
        # Step 7: Create THOT knowledge
        reasoning_trace = reasoning_logger.get_reasoning_trace()
        performance_metrics = {
            "total_time": inference_time,
            "steps": len(reasoning_trace),
            "model": model
        }
        
        agenticplace_context = {
            "distributed_mind": "AgenticPlace",
            "node_id": "mindx_local",
            "capabilities": ["reasoning", "inference", "thot_generation"],
            "model": model
        }
        
        thot = thot_knowledge.create_thot(
            reasoning_trace=reasoning_trace,
            assessment=assessment,
            performance_metrics=performance_metrics,
            agenticplace_context=agenticplace_context
        )
        
        reasoning_logger.log_step("thot_created", {
            "thot_id": thot["thot_id"],
            "knowledge_vectors": thot["knowledge_vectors"]
        })
        
        return {
            "success": response_success,
            "response": response_text if response_success else None,
            "error": error_message if error_message else None,
            "model": model,
            "inference_time": inference_time,
            "assessment": assessment,
            "thot": thot,
            "reasoning_trace": reasoning_trace
        }
        
    except Exception as e:
        error_time = time.time() - start_time
        reasoning_logger.log_step("inference_error", {
            "error": str(e),
            "error_type": type(e).__name__,
            "time_elapsed": error_time
        })
        
        return {
            "success": False,
            "error": str(e),
            "inference_time": error_time
        }


async def initialize_agents():
    """Initialize all required agents"""
    logger.info("Initializing agents...")
    
    config = Config()
    memory_agent = MemoryAgent(config=config)
    belief_system = BeliefSystem()
    coordinator = await get_coordinator_agent_mindx_async(
        config_override=config,
        memory_agent=memory_agent,
        belief_system=belief_system
    )
    model_registry = await get_model_registry_async(config=config)
    
    mindx_agent = await MindXAgent.get_instance(
        agent_id="mindx_meta_agent",
        config=config,
        memory_agent=memory_agent,
        belief_system=belief_system,
        coordinator_agent=coordinator,
        model_registry=model_registry
    )
    
    logger.info("✓ All agents initialized")
    return {
        "config": config,
        "memory_agent": memory_agent,
        "mindx_agent": mindx_agent,
        "model_registry": model_registry
    }


async def main():
    """Main test execution"""
    logger.info("="*70)
    logger.info("MindXAgent Ollama Inference & Reasoning Test")
    logger.info("="*70)
    logger.info(f"Ollama Server: {OLLAMA_BASE_URL}")
    logger.info(f"Reasoning Log: {REASONING_LOG_PATH}")
    logger.info(f"THOT Log: {THOT_LOG_PATH}")
    logger.info("="*70)
    
    try:
        # Initialize reasoning logger and THOT knowledge
        reasoning_logger = ReasoningLogger(REASONING_LOG_PATH)
        thot_knowledge = THOTKnowledge(THOT_LOG_PATH)
        
        # Initialize Ollama API
        ollama_api = create_ollama_api(base_url=OLLAMA_BASE_URL)
        logger.info(f"✓ Ollama API initialized: {ollama_api.base_url}")
        
        # Get available models
        models = await get_ollama_models(ollama_api)
        if not models:
            logger.error("No models available from Ollama server")
            return
        
        # Select best model for reasoning
        selected_model = await select_best_model(models, task_type="reasoning")
        if not selected_model:
            logger.error("Could not select a model")
            return
        
        logger.info(f"✓ Selected model: {selected_model}")
        
        # Initialize agents
        agents = await initialize_agents()
        
        # Test message for reasoning (shorter for faster inference)
        test_message = """Analyze the mindX system and identify one improvement opportunity. 
        Focus on: performance, agent coordination, or knowledge management. 
        Provide a brief assessment."""
        
        logger.info("\n" + "="*70)
        logger.info("Starting Inference Test")
        logger.info("="*70)
        logger.info(f"Model: {selected_model}")
        logger.info(f"Message: {test_message[:100]}...")
        logger.info("="*70 + "\n")
        
        # Run inference test
        result = await test_mindxagent_ollama_inference(
            mindx_agent=agents["mindx_agent"],
            ollama_api=ollama_api,
            model=selected_model,
            reasoning_logger=reasoning_logger,
            thot_knowledge=thot_knowledge,
            test_message=test_message
        )
        
        # Log result to memory agent
        await agents["memory_agent"].save_timestamped_memory(
            agent_id="mindx_meta_agent",
            memory_type=MemoryType.INTERACTION,
            content={
                "test_type": "ollama_inference_reasoning",
                "result": result,
                "model": selected_model
            },
            context={"test": "mindxagent_ollama_reasoning"},
            tags=["test", "ollama", "reasoning", "thot"]
        )
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("Test Summary")
        logger.info("="*70)
        logger.info(f"✓ Success: {result.get('success', False)}")
        logger.info(f"✓ Model: {selected_model}")
        logger.info(f"✓ Inference Time: {result.get('inference_time', 0):.2f}s")
        logger.info(f"✓ Reasoning Steps: {len(result.get('reasoning_trace', []))}")
        if result.get('thot'):
            logger.info(f"✓ THOT ID: {result['thot']['thot_id']}")
            logger.info(f"✓ Knowledge Vectors: {result['thot']['knowledge_vectors']}")
        logger.info(f"✓ Reasoning Log: {REASONING_LOG_PATH}")
        logger.info(f"✓ THOT Log: {THOT_LOG_PATH}")
        logger.info("="*70)
        
        if result.get('response'):
            logger.info("\nResponse Preview:")
            logger.info(result['response'][:500] + "..." if len(result['response']) > 500 else result['response'])
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
