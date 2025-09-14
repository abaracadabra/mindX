#!/usr/bin/env python3
"""
Enhanced Monitoring System Test Script

This script demonstrates the enhanced monitoring system with:
- Real resource monitoring and alerting
- LLM performance tracking
- Agent performance logging
- Memory agent integration for structured logging
- Report generation and export
"""
import asyncio
import time
import random
from pathlib import Path
import sys

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import Config
from utils.logging_config import get_logger
from agents.memory_agent import MemoryAgent
from monitoring.enhanced_monitoring_system import EnhancedMonitoringSystem, get_enhanced_monitoring_system
from monitoring.monitoring_integration import IntegratedMonitoringManager, get_integrated_monitoring_manager

logger = get_logger(__name__)

class MonitoringTestScenario:
    """Test scenario for the enhanced monitoring system."""
    
    def __init__(self):
        self.config = Config()
        self.memory_agent = MemoryAgent(config=self.config)
        self.monitoring_system = None
        self.integrated_manager = None
        
    async def initialize(self):
        """Initialize the monitoring systems."""
        logger.info("🚀 Initializing Enhanced Monitoring Test")
        
        # Initialize enhanced monitoring system
        self.monitoring_system = await get_enhanced_monitoring_system(
            memory_agent=self.memory_agent,
            config=self.config
        )
        
        # Initialize integrated monitoring manager
        self.integrated_manager = await get_integrated_monitoring_manager(self.config)
        
        logger.info("✅ Monitoring systems initialized")
    
    async def test_basic_monitoring(self):
        """Test basic resource monitoring functionality."""
        logger.info("📊 Testing Basic Resource Monitoring")
        
        # Start monitoring
        await self.monitoring_system.start_monitoring()
        await self.integrated_manager.start_monitoring()
        
        # Let it collect some data
        logger.info("Collecting baseline metrics for 30 seconds...")
        await asyncio.sleep(30)
        
        # Get current metrics
        current_metrics = self.monitoring_system.get_current_metrics()
        logger.info(f"Current CPU: {current_metrics['resource_metrics']['cpu_percent']:.1f}%")
        logger.info(f"Current Memory: {current_metrics['resource_metrics']['memory_percent']:.1f}%")
        logger.info(f"Active Alerts: {len(current_metrics['active_alerts'])}")
        
        return current_metrics
    
    async def test_llm_performance_logging(self):
        """Test LLM performance logging with various scenarios."""
        logger.info("🤖 Testing LLM Performance Logging")
        
        test_scenarios = [
            # Normal performance
            {"model": "gpt-4", "task": "planning", "agent": "bdi_agent", "latency": 1500, "success": True, "tokens": (100, 50)},
            {"model": "gpt-4", "task": "code_generation", "agent": "enhanced_simple_coder", "latency": 2200, "success": True, "tokens": (150, 80)},
            {"model": "gemini-pro", "task": "analysis", "agent": "mastermind", "latency": 1800, "success": True, "tokens": (120, 60)},
            
            # High latency scenarios
            {"model": "gpt-4", "task": "planning", "agent": "bdi_agent", "latency": 6000, "success": True, "tokens": (200, 100)},
            {"model": "gpt-4", "task": "planning", "agent": "bdi_agent", "latency": 7500, "success": True, "tokens": (250, 120)},
            
            # Failure scenarios
            {"model": "gpt-4", "task": "code_generation", "agent": "enhanced_simple_coder", "latency": 1000, "success": False, "error": "rate_limit"},
            {"model": "gemini-pro", "task": "analysis", "agent": "mastermind", "latency": 500, "success": False, "error": "timeout"},
            
            # Cost tracking
            {"model": "gpt-4", "task": "planning", "agent": "bdi_agent", "latency": 2000, "success": True, "tokens": (300, 150), "cost": 0.006},
            {"model": "gemini-pro", "task": "analysis", "agent": "mastermind", "latency": 1500, "success": True, "tokens": (180, 90), "cost": 0.003},
        ]
        
        for i, scenario in enumerate(test_scenarios):
            logger.info(f"Logging LLM call {i+1}/9: {scenario['model']} {scenario['task']}")
            
            prompt_tokens, completion_tokens = scenario.get("tokens", (0, 0))
            
            await self.monitoring_system.log_llm_performance(
                model_name=scenario["model"],
                task_type=scenario["task"],
                agent_id=scenario["agent"],
                latency_ms=scenario["latency"],
                success=scenario["success"],
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=scenario.get("cost"),
                error_type=scenario.get("error"),
                metadata={"test_scenario": i+1, "batch": "performance_test"}
            )
            
            # Also log via integrated manager
            await self.integrated_manager.log_llm_call(
                model_name=scenario["model"],
                task_type=scenario["task"],
                initiating_agent_id=scenario["agent"],
                latency_ms=scenario["latency"],
                success=scenario["success"],
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=scenario.get("cost"),
                error_type=scenario.get("error"),
                metadata={"test_scenario": i+1, "batch": "performance_test"}
            )
            
            # Small delay between calls
            await asyncio.sleep(0.5)
        
        logger.info("✅ LLM performance logging completed")
    
    async def test_agent_performance_logging(self):
        """Test agent performance logging."""
        logger.info("🎯 Testing Agent Performance Logging")
        
        agents_and_actions = [
            ("bdi_agent", "goal_planning", 150, True),
            ("bdi_agent", "action_execution", 200, True),
            ("bdi_agent", "belief_update", 50, True),
            ("enhanced_simple_coder", "code_analysis", 300, True),
            ("enhanced_simple_coder", "code_generation", 500, True),
            ("enhanced_simple_coder", "test_execution", 800, False),  # Failed test
            ("mastermind", "strategic_planning", 400, True),
            ("mastermind", "coordination", 100, True),
            ("guardian_agent", "security_check", 75, True),
            ("guardian_agent", "threat_analysis", 250, True),
        ]
        
        for agent_id, action_type, exec_time, success in agents_and_actions:
            logger.info(f"Logging agent performance: {agent_id} - {action_type}")
            
            # Add some random variation
            actual_exec_time = exec_time + random.randint(-50, 50)
            
            await self.monitoring_system.log_agent_performance(
                agent_id=agent_id,
                action_type=action_type,
                execution_time_ms=actual_exec_time,
                success=success,
                metadata={
                    "test_execution": True,
                    "baseline_time": exec_time,
                    "variation_ms": actual_exec_time - exec_time
                }
            )
            
            await asyncio.sleep(0.2)
        
        logger.info("✅ Agent performance logging completed")
    
    async def test_alert_system(self):
        """Test the alert system by simulating high resource usage."""
        logger.info("🚨 Testing Alert System")
        
        # Note: In a real scenario, we would simulate actual high CPU/memory usage
        # For this test, we'll just demonstrate the alert logging mechanism
        
        # Simulate some resource alerts by directly triggering them
        logger.info("Simulating resource alerts...")
        
        # The actual alerts would be triggered by the monitoring loop
        # Here we just demonstrate the alert logging capability
        current_metrics = self.monitoring_system.get_current_metrics()
        logger.info(f"Current active alerts: {current_metrics['active_alerts']}")
        
        logger.info("✅ Alert system test completed")
    
    async def test_memory_integration(self):
        """Test memory agent integration and data persistence."""
        logger.info("🧠 Testing Memory Agent Integration")
        
        # Check recent memories related to monitoring
        recent_memories = await self.memory_agent.get_recent_memories(
            agent_id="enhanced_monitoring_system",
            limit=10
        )
        
        logger.info(f"Found {len(recent_memories)} recent monitoring memories")
        
        for memory in recent_memories[:3]:  # Show first 3
            logger.info(f"Memory: {memory.memory_type.value} - {memory.timestamp}")
        
        # Check STM directory structure
        stm_path = self.memory_agent.stm_path / "enhanced_monitoring_system"
        if stm_path.exists():
            memory_files = list(stm_path.rglob("*.json"))
            logger.info(f"Found {len(memory_files)} memory files in STM")
        
        logger.info("✅ Memory integration test completed")
    
    async def test_report_generation(self):
        """Test comprehensive report generation."""
        logger.info("📈 Testing Report Generation")
        
        # Generate monitoring report
        report = await self.monitoring_system.generate_monitoring_report(hours_back=1)
        
        logger.info("📊 Monitoring Report Summary:")
        logger.info(f"  Hours analyzed: {report['hours_analyzed']}")
        logger.info(f"  Resource data points: {report['resource_summary']['data_points']}")
        logger.info(f"  Average CPU: {report['resource_summary']['avg_cpu_percent']}%")
        logger.info(f"  Average Memory: {report['resource_summary']['avg_memory_percent']}%")
        logger.info(f"  Performance metrics: {len(report['performance_summary'])}")
        logger.info(f"  Total alerts: {report['alert_summary']['total_alerts']}")
        logger.info(f"  Active alerts: {report['alert_summary']['active_alerts']}")
        
        # Export metrics to file
        export_path = await self.monitoring_system.export_metrics_to_file()
        logger.info(f"📁 Metrics exported to: {export_path}")
        
        # Get integrated metrics
        integrated_metrics = await self.integrated_manager.get_current_metrics()
        logger.info(f"🔗 Integrated metrics components: {list(integrated_metrics.keys())}")
        
        logger.info("✅ Report generation completed")
    
    async def test_monitoring_logs_directory(self):
        """Test that logs are properly created in /data/monitoring/logs."""
        logger.info("📁 Testing Monitoring Logs Directory")
        
        monitoring_logs_path = Path("data/monitoring/logs")
        
        if monitoring_logs_path.exists():
            log_files = list(monitoring_logs_path.rglob("*"))
            logger.info(f"Found {len(log_files)} files in monitoring logs directory")
            
            # Show recent files
            for log_file in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                size_kb = log_file.stat().st_size / 1024
                logger.info(f"  {log_file.name} ({size_kb:.1f} KB)")
        else:
            logger.warning("Monitoring logs directory not found")
        
        # Check memory agent STM structure
        stm_monitoring_path = Path("data/memory/stm/enhanced_monitoring_system")
        if stm_monitoring_path.exists():
            stm_files = list(stm_monitoring_path.rglob("*.json"))
            logger.info(f"Found {len(stm_files)} STM files for monitoring system")
        
        logger.info("✅ Monitoring logs directory test completed")
    
    async def cleanup(self):
        """Clean up monitoring systems."""
        logger.info("🧹 Cleaning up monitoring systems")
        
        try:
            await self.monitoring_system.stop_monitoring()
            await self.integrated_manager.stop_monitoring()
            logger.info("✅ Monitoring systems stopped")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

async def main():
    """Main test execution."""
    test_scenario = MonitoringTestScenario()
    
    try:
        await test_scenario.initialize()
        
        # Run test sequence
        logger.info("🎬 Starting Enhanced Monitoring System Test Sequence")
        
        # Test 1: Basic monitoring
        await test_scenario.test_basic_monitoring()
        
        # Test 2: LLM performance logging
        await test_scenario.test_llm_performance_logging()
        
        # Test 3: Agent performance logging
        await test_scenario.test_agent_performance_logging()
        
        # Test 4: Alert system
        await test_scenario.test_alert_system()
        
        # Test 5: Memory integration
        await test_scenario.test_memory_integration()
        
        # Test 6: Report generation
        await test_scenario.test_report_generation()
        
        # Test 7: Monitoring logs directory
        await test_scenario.test_monitoring_logs_directory()
        
        logger.info("🎉 All monitoring tests completed successfully!")
        
        # Show final summary
        current_metrics = test_scenario.monitoring_system.get_current_metrics()
        logger.info("📋 Final Test Summary:")
        logger.info(f"  CPU Usage: {current_metrics['resource_metrics']['cpu_percent']:.1f}%")
        logger.info(f"  Memory Usage: {current_metrics['resource_metrics']['memory_percent']:.1f}%")
        logger.info(f"  LLM Performance Metrics: {current_metrics['performance_metrics_count']['llm_calls']}")
        logger.info(f"  Agent Performance Metrics: {current_metrics['performance_metrics_count']['agent_performance']}")
        logger.info(f"  Active Alerts: {len(current_metrics['active_alerts'])}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1
    
    finally:
        await test_scenario.cleanup()
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))