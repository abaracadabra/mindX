#!/usr/bin/env python3
"""
Test mindXagent Ollama Connection Monitor

This script:
1. Monitors Ollama connection status
2. Checks logs for connection errors
3. Validates connection accuracy
4. Tests network sanity and error recovery
5. Reports connection health metrics
"""

import asyncio
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

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
from api.ollama import create_ollama_api

# Setup logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)

# Ollama configuration
OLLAMA_HOST = "10.0.0.155"
OLLAMA_PORT = 18080
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# Test configuration
MONITOR_DURATION = 300  # 5 minutes
CHECK_INTERVAL = 10  # Check every 10 seconds
MAX_ERRORS = 5  # Maximum errors before alerting


class ConnectionMonitor:
    """Monitor Ollama connection health and errors"""
    
    def __init__(self, mindx_agent: MindXAgent):
        self.mindx_agent = mindx_agent
        self.errors: List[Dict[str, Any]] = []
        self.success_count = 0
        self.error_count = 0
        self.latency_history: List[float] = []
        self.start_time = time.time()
        
    async def check_connection(self) -> Dict[str, Any]:
        """Check Ollama connection status"""
        check_start = time.time()
        result = {
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "latency": 0,
            "error": None,
            "details": {}
        }
        
        try:
            # Check if Ollama chat manager is initialized
            if not self.mindx_agent.ollama_chat_manager:
                result["error"] = "Ollama Chat Manager not initialized"
                result["details"]["initialized"] = False
                return result
            
            # Check connection status
            if not self.mindx_agent.ollama_chat_manager.connected:
                result["error"] = "Ollama Chat Manager not connected"
                result["details"]["connected"] = False
                # Try to reconnect
                try:
                    connected = await self.mindx_agent.ollama_chat_manager.initialize()
                    result["details"]["reconnect_attempted"] = True
                    result["details"]["reconnect_success"] = connected
                    if connected:
                        result["success"] = True
                except Exception as e:
                    result["error"] = f"Reconnection failed: {str(e)}"
                result["latency"] = time.time() - check_start
                return result
            
            # Test actual connection with a simple request
            test_result = await self.mindx_agent.chat_with_ollama(
                message="Connection test - please respond with 'OK'",
                max_tokens=10,
                temperature=0.1
            )
            
            result["latency"] = time.time() - check_start
            
            if test_result.get("success"):
                result["success"] = True
                result["details"]["model"] = test_result.get("model")
                result["details"]["response_length"] = len(test_result.get("content", ""))
                result["details"]["tokens"] = test_result.get("tokens", 0)
            else:
                result["error"] = test_result.get("error", "Unknown error")
                result["details"]["test_failed"] = True
                
        except Exception as e:
            result["error"] = str(e)
            result["latency"] = time.time() - check_start
            logger.error(f"Connection check error: {e}", exc_info=True)
        
        return result
    
    async def check_logs_for_errors(self) -> List[Dict[str, Any]]:
        """Check system logs for Ollama-related errors"""
        errors = []
        
        try:
            # Check memory agent logs
            log_dir = PROJECT_ROOT / "data" / "logs"
            if log_dir.exists():
                # Look for recent error logs
                for log_file in log_dir.glob("*.log"):
                    try:
                        # Check last 100 lines for errors
                        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            recent_lines = lines[-100:] if len(lines) > 100 else lines
                            
                            for i, line in enumerate(recent_lines):
                                if any(keyword in line.lower() for keyword in [
                                    'ollama', 'connection', 'error', 'failed', 'timeout'
                                ]):
                                    if 'error' in line.lower() or 'failed' in line.lower():
                                        errors.append({
                                            "file": log_file.name,
                                            "line": len(lines) - 100 + i if len(lines) > 100 else i,
                                            "content": line.strip(),
                                            "timestamp": datetime.now().isoformat()
                                        })
                    except Exception as e:
                        logger.debug(f"Error reading log file {log_file}: {e}")
        except Exception as e:
            logger.warning(f"Error checking logs: {e}")
        
        return errors
    
    async def validate_network_sanity(self) -> Dict[str, Any]:
        """Validate network sanity and connection accuracy"""
        sanity = {
            "timestamp": datetime.now().isoformat(),
            "healthy": True,
            "issues": [],
            "metrics": {}
        }
        
        try:
            # Check if chat manager exists
            if not self.mindx_agent.ollama_chat_manager:
                sanity["healthy"] = False
                sanity["issues"].append("Ollama Chat Manager not initialized")
                return sanity
            
            # Check connection
            if not self.mindx_agent.ollama_chat_manager.connected:
                sanity["healthy"] = False
                sanity["issues"].append("Ollama Chat Manager not connected")
            
            # Check available models
            models = await self.mindx_agent.get_available_ollama_models()
            sanity["metrics"]["available_models"] = len(models) if models else 0
            
            if not models:
                sanity["healthy"] = False
                sanity["issues"].append("No models available")
            
            # Check base URL
            if hasattr(self.mindx_agent.ollama_chat_manager, 'base_url'):
                sanity["metrics"]["base_url"] = str(self.mindx_agent.ollama_chat_manager.base_url)
            
            # Check inference optimizer if available
            if hasattr(self.mindx_agent.ollama_chat_manager, 'inference_optimizer'):
                optimizer = self.mindx_agent.ollama_chat_manager.inference_optimizer
                if optimizer:
                    opt_metrics = self.mindx_agent.get_inference_optimization_metrics()
                    sanity["metrics"]["optimization"] = {
                        "enabled": opt_metrics.get("status") != "no_data",
                        "current_frequency": opt_metrics.get("current_frequency"),
                        "total_requests": opt_metrics.get("total_requests", 0)
                    }
            
            # Check recent error rate
            if self.error_count + self.success_count > 0:
                error_rate = self.error_count / (self.error_count + self.success_count)
                sanity["metrics"]["error_rate"] = error_rate
                sanity["metrics"]["success_rate"] = 1 - error_rate
                
                if error_rate > 0.1:  # More than 10% error rate
                    sanity["healthy"] = False
                    sanity["issues"].append(f"High error rate: {error_rate*100:.1f}%")
            
            # Check average latency
            if self.latency_history:
                avg_latency = sum(self.latency_history) / len(self.latency_history)
                sanity["metrics"]["avg_latency"] = avg_latency
                
                if avg_latency > 10.0:  # More than 10 seconds
                    sanity["healthy"] = False
                    sanity["issues"].append(f"High latency: {avg_latency:.2f}s")
            
        except Exception as e:
            sanity["healthy"] = False
            sanity["issues"].append(f"Validation error: {str(e)}")
            logger.error(f"Network sanity check error: {e}", exc_info=True)
        
        return sanity
    
    async def monitor(self, duration: int = MONITOR_DURATION, interval: int = CHECK_INTERVAL):
        """Monitor connection for specified duration"""
        logger.info("="*70)
        logger.info("Starting Ollama Connection Monitor")
        logger.info("="*70)
        logger.info(f"Monitor duration: {duration}s")
        logger.info(f"Check interval: {interval}s")
        logger.info(f"Ollama URL: {OLLAMA_BASE_URL}")
        logger.info("="*70)
        
        end_time = time.time() + duration
        check_count = 0
        
        while time.time() < end_time:
            check_count += 1
            elapsed = time.time() - self.start_time
            
            logger.info(f"\n[Check {check_count}] Elapsed: {elapsed:.1f}s")
            
            # Check connection
            connection_result = await self.check_connection()
            
            if connection_result["success"]:
                self.success_count += 1
                self.latency_history.append(connection_result["latency"])
                logger.info(f"✓ Connection OK - Latency: {connection_result['latency']:.2f}s")
                if connection_result.get("details", {}).get("model"):
                    logger.info(f"  Model: {connection_result['details']['model']}")
            else:
                self.error_count += 1
                error_info = {
                    "timestamp": connection_result["timestamp"],
                    "error": connection_result["error"],
                    "details": connection_result.get("details", {})
                }
                self.errors.append(error_info)
                logger.error(f"✗ Connection FAILED - {connection_result['error']}")
            
            # Check logs for errors
            log_errors = await self.check_logs_for_errors()
            if log_errors:
                logger.warning(f"⚠ Found {len(log_errors)} error entries in logs")
                for log_error in log_errors[:3]:  # Show first 3
                    logger.warning(f"  Log: {log_error['file']}:{log_error['line']} - {log_error['content'][:100]}")
            
            # Validate network sanity
            sanity = await self.validate_network_sanity()
            if not sanity["healthy"]:
                logger.warning(f"⚠ Network sanity issues: {', '.join(sanity['issues'])}")
            else:
                logger.info(f"✓ Network sanity: OK")
            
            # Wait for next check
            if time.time() < end_time:
                await asyncio.sleep(interval)
        
        # Final summary
        self.print_summary()
    
    def print_summary(self):
        """Print monitoring summary"""
        total_checks = self.success_count + self.error_count
        duration = time.time() - self.start_time
        
        logger.info("")
        logger.info("="*70)
        logger.info("Connection Monitor Summary")
        logger.info("="*70)
        logger.info(f"Total duration: {duration:.1f}s")
        logger.info(f"Total checks: {total_checks}")
        logger.info(f"Successful: {self.success_count} ({self.success_count/total_checks*100:.1f}%)" if total_checks > 0 else "Successful: 0")
        logger.info(f"Failed: {self.error_count} ({self.error_count/total_checks*100:.1f}%)" if total_checks > 0 else "Failed: 0")
        
        if self.latency_history:
            avg_latency = sum(self.latency_history) / len(self.latency_history)
            min_latency = min(self.latency_history)
            max_latency = max(self.latency_history)
            logger.info(f"Average latency: {avg_latency:.2f}s")
            logger.info(f"Min latency: {min_latency:.2f}s")
            logger.info(f"Max latency: {max_latency:.2f}s")
        
        if self.errors:
            logger.info(f"\nErrors encountered: {len(self.errors)}")
            for i, error in enumerate(self.errors[:5], 1):  # Show first 5
                logger.info(f"  {i}. {error['timestamp']}: {error['error']}")
        
        # Network sanity final check
        logger.info("")
        logger.info("Final Network Sanity Check:")
        asyncio.create_task(self.validate_network_sanity())
        
        logger.info("="*70)


async def initialize_agents():
    """Initialize all required agents"""
    logger.info("Initializing agents...")
    
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


async def test_ollama_connection():
    """Test initial Ollama connection"""
    logger.info("Testing initial Ollama connection...")
    
    try:
        ollama_api = create_ollama_api(base_url=OLLAMA_BASE_URL)
        models = await ollama_api.list_models()
        
        if models:
            logger.info(f"✓ Ollama connection successful: {OLLAMA_BASE_URL}")
            logger.info(f"✓ Found {len(models)} available models")
            return True
        else:
            logger.warning("⚠ Ollama connected but no models found")
            return False
    except Exception as e:
        logger.error(f"✗ Ollama connection failed: {e}")
        return False


async def main():
    """Main test execution"""
    logger.info("="*70)
    logger.info("mindXagent Ollama Connection Monitor Test")
    logger.info("="*70)
    
    try:
        # Step 1: Test initial Ollama connection
        if not await test_ollama_connection():
            logger.error("Cannot proceed without Ollama connection")
            return
        
        # Step 2: Initialize agents
        agents = await initialize_agents()
        
        # Step 3: Ensure Ollama chat manager is initialized
        if not agents["mindx_agent"].ollama_chat_manager:
            logger.info("Initializing Ollama Chat Manager...")
            await agents["mindx_agent"]._init_ollama_chat_manager()
        
        if not agents["mindx_agent"].ollama_chat_manager:
            logger.error("Failed to initialize Ollama Chat Manager")
            return
        
        # Step 4: Start monitoring
        monitor = ConnectionMonitor(agents["mindx_agent"])
        await monitor.monitor(duration=MONITOR_DURATION, interval=CHECK_INTERVAL)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
