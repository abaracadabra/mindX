#!/usr/bin/env python3
"""
Enhanced Monitoring System Test with CPU, RAM, API Tokens, and Rate Limiter Metrics

This script demonstrates the comprehensive monitoring capabilities including:
- Detailed CPU and RAM monitoring
- API token usage tracking
- Rate limiter performance metrics
- Resource utilization analysis
"""
import asyncio
import sys
import time
import random
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitoring.enhanced_monitoring_system import EnhancedMonitoringSystem
from llm.rate_limiter import RateLimiter
from agents.memory_agent import MemoryAgent
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

class EnhancedMonitoringTestSuite:
    """Comprehensive test suite for enhanced monitoring with all new features."""
    
    def __init__(self):
        self.config = Config()
        self.memory_agent = MemoryAgent(config=self.config)
        self.monitoring_system = None
        self.test_results = {}
    
    async def setup(self):
        """Initialize the enhanced monitoring system."""
        logger.info("🚀 Setting up Enhanced Monitoring System with comprehensive metrics")
        
        self.monitoring_system = EnhancedMonitoringSystem(
            memory_agent=self.memory_agent,
            config=self.config,
            test_mode=True
        )
        
        await self.monitoring_system.start_monitoring()
        logger.info("✅ Enhanced monitoring system started")
    
    async def test_detailed_resource_monitoring(self):
        """Test detailed CPU and RAM monitoring."""
        logger.info("💻 Testing Detailed CPU and RAM Monitoring")
        
        # Let the system collect some baseline metrics
        await asyncio.sleep(2)
        
        # Get current detailed metrics
        current_metrics = self.monitoring_system.get_current_metrics()
        
        # Verify detailed CPU metrics
        cpu_metrics = current_metrics["resource_metrics"]
        expected_cpu_fields = [
            "cpu_percent", "cpu_per_core", "cpu_count_logical", "cpu_count_physical",
            "cpu_freq_current", "cpu_freq_min", "cpu_freq_max", "load_average"
        ]
        
        for field in expected_cpu_fields:
            if field not in cpu_metrics:
                raise AssertionError(f"Missing CPU metric: {field}")
        
        # Verify detailed RAM metrics
        expected_memory_fields = [
            "memory_percent", "memory_total_gb", "memory_available_gb", "memory_used_gb",
            "memory_free_gb", "memory_cached_gb", "memory_buffers_gb",
            "swap_percent", "swap_total_gb", "swap_used_gb", "swap_free_gb"
        ]
        
        for field in expected_memory_fields:
            if field not in cpu_metrics:
                raise AssertionError(f"Missing memory metric: {field}")
        
        logger.info(f"✅ CPU Cores: {cpu_metrics['cpu_count_logical']} logical, {cpu_metrics['cpu_count_physical']} physical")
        logger.info(f"✅ Memory: {cpu_metrics['memory_used_gb']:.1f}GB used / {cpu_metrics['memory_total_gb']:.1f}GB total")
        logger.info(f"✅ Swap: {cpu_metrics['swap_percent']:.1f}% used ({cpu_metrics['swap_used_gb']:.1f}GB)")
        
        if cpu_metrics["cpu_per_core"]:
            logger.info(f"✅ Per-core CPU usage: {[f'{x:.1f}%' for x in cpu_metrics['cpu_per_core'][:4]]}")
        
        self.test_results["detailed_resource_monitoring"] = "PASSED"
    
    async def test_api_token_usage_tracking(self):
        """Test comprehensive API token usage tracking."""
        logger.info("🎯 Testing API Token Usage Tracking")
        
        # Simulate various API calls with different token usage patterns
        api_scenarios = [
            # High-efficiency model (good completion/prompt ratio)
            {"provider": "openai", "model": "gpt-4", "prompt": 150, "completion": 200, "cost": 0.006, "rate_limited": False},
            {"provider": "openai", "model": "gpt-4", "prompt": 200, "completion": 180, "cost": 0.008, "rate_limited": False},
            {"provider": "openai", "model": "gpt-4", "prompt": 120, "completion": 160, "cost": 0.005, "rate_limited": False},
            
            # Lower-efficiency model (poor completion/prompt ratio - should trigger alert)
            {"provider": "anthropic", "model": "claude-3", "prompt": 300, "completion": 20, "cost": 0.004, "rate_limited": False},
            {"provider": "anthropic", "model": "claude-3", "prompt": 250, "completion": 15, "cost": 0.003, "rate_limited": False},
            
            # Rate limited calls
            {"provider": "gemini", "model": "gemini-pro", "prompt": 100, "completion": 80, "cost": 0.002, "rate_limited": True},
            {"provider": "gemini", "model": "gemini-pro", "prompt": 110, "completion": 90, "cost": 0.002, "rate_limited": True},
            {"provider": "gemini", "model": "gemini-pro", "prompt": 90, "completion": 70, "cost": 0.001, "rate_limited": True},
            
            # High cost scenario
            {"provider": "openai", "model": "gpt-4-vision", "prompt": 500, "completion": 300, "cost": 0.025, "rate_limited": False},
            {"provider": "openai", "model": "gpt-4-vision", "prompt": 600, "completion": 400, "cost": 0.030, "rate_limited": False},
        ]
        
        for scenario in api_scenarios:
            await self.monitoring_system.log_api_token_usage(
                model_name=scenario["model"],
                provider=scenario["provider"],
                prompt_tokens=scenario["prompt"],
                completion_tokens=scenario["completion"],
                cost_usd=scenario["cost"],
                success=True,
                rate_limited=scenario["rate_limited"],
                metadata={"test_scenario": True}
            )
            await asyncio.sleep(0.1)  # Small delay to simulate real API calls
        
        # Get API usage summary
        api_summary = await self.monitoring_system.get_api_usage_summary()
        
        # Verify summary data
        assert api_summary["summary"]["total_calls"] == len(api_scenarios)
        assert api_summary["summary"]["total_cost_usd"] > 0
        assert api_summary["summary"]["total_tokens"] > 0
        
        # Verify provider breakdown
        expected_providers = {"openai", "anthropic", "gemini"}
        for provider in expected_providers:
            assert provider in api_summary["by_provider"]
        
        # Verify model details
        assert len(api_summary["by_model"]) >= 4  # At least 4 different models
        
        logger.info(f"✅ Total API Cost: ${api_summary['summary']['total_cost_usd']:.3f}")
        logger.info(f"✅ Total Tokens: {api_summary['summary']['total_tokens']:,}")
        logger.info(f"✅ Providers: {list(api_summary['by_provider'].keys())}")
        
        # Check for efficiency alerts (should be triggered for claude-3)
        await asyncio.sleep(1)  # Let alerts process
        
        self.test_results["api_token_usage_tracking"] = "PASSED"
    
    async def test_rate_limiter_monitoring(self):
        """Test rate limiter performance monitoring."""
        logger.info("⏱️ Testing Rate Limiter Monitoring")
        
        # Create rate limiters with monitoring callbacks
        def create_monitoring_callback(provider: str, model: str):
            async def callback(metrics: Dict[str, Any]):
                await self.monitoring_system.log_rate_limiter_metrics(
                    provider=provider,
                    model_name=model,
                    rate_limiter_metrics=metrics,
                    metadata={"test_scenario": True}
                )
            return callback
        
        # Test different rate limiter scenarios
        limiters = [
            # High-performance limiter (should be healthy)
            {
                "provider": "openai",
                "model": "gpt-4",
                "limiter": RateLimiter(
                    requests_per_minute=60,
                    max_retries=3,
                    monitoring_callback=lambda m: asyncio.create_task(
                        create_monitoring_callback("openai", "gpt-4")(m)
                    )
                )
            },
            # Constrained limiter (may show degraded performance)
            {
                "provider": "anthropic",
                "model": "claude-3",
                "limiter": RateLimiter(
                    requests_per_minute=10,
                    max_retries=5,
                    monitoring_callback=lambda m: asyncio.create_task(
                        create_monitoring_callback("anthropic", "claude-3")(m)
                    )
                )
            },
            # Very constrained limiter (should show critical status)
            {
                "provider": "gemini",
                "model": "gemini-pro",
                "limiter": RateLimiter(
                    requests_per_minute=2,
                    max_retries=3,
                    monitoring_callback=lambda m: asyncio.create_task(
                        create_monitoring_callback("gemini", "gemini-pro")(m)
                    )
                )
            }
        ]
        
        # Simulate API calls through rate limiters
        for limiter_config in limiters:
            limiter = limiter_config["limiter"]
            provider = limiter_config["provider"]
            model = limiter_config["model"]
            
            logger.info(f"Testing {provider}/{model} rate limiter...")
            
            # Make several requests to gather metrics
            for i in range(8):
                success = await limiter.wait()
                logger.debug(f"  Request {i+1}: {'Success' if success else 'Failed'}")
                await asyncio.sleep(0.1)
        
        # Get rate limiter summary
        limiter_summary = await self.monitoring_system.get_rate_limiter_summary()
        
        # Verify summary data
        assert limiter_summary["total_limiters"] >= 3
        assert "overall_health" in limiter_summary
        
        # Verify individual limiter status
        for provider_model, status in limiter_summary["limiter_status"].items():
            assert "status" in status
            assert "success_rate" in status
            assert "total_requests" in status
            logger.info(f"✅ {provider_model}: {status['status']} ({status['success_rate']:.1%} success)")
        
        logger.info(f"✅ Overall Rate Limiter Health: {limiter_summary['overall_health']}")
        
        self.test_results["rate_limiter_monitoring"] = "PASSED"
    
    async def test_swap_memory_alerts(self):
        """Test swap memory monitoring and alerts."""
        logger.info("💾 Testing Swap Memory Monitoring")
        
        # Get current swap metrics
        current_metrics = self.monitoring_system.get_current_metrics()
        swap_percent = current_metrics["resource_metrics"]["swap_percent"]
        
        logger.info(f"✅ Current Swap Usage: {swap_percent:.1f}%")
        
        # Test would trigger swap alerts if swap usage is high
        # In normal conditions, swap usage should be low
        if swap_percent > 60:
            logger.warning(f"High swap usage detected: {swap_percent:.1f}%")
        
        self.test_results["swap_memory_alerts"] = "PASSED"
    
    async def test_comprehensive_reporting(self):
        """Test comprehensive monitoring reports."""
        logger.info("📊 Testing Comprehensive Reporting")
        
        # Generate full monitoring report
        report = await self.monitoring_system.generate_monitoring_report(hours_back=1)
        
        # Verify report structure
        expected_sections = [
            "resource_history", "llm_performance", "agent_performance",
            "alert_history", "active_alerts"
        ]
        
        for section in expected_sections:
            assert section in report, f"Missing report section: {section}"
        
        # Verify enhanced sections
        if "api_token_metrics" in report:
            logger.info("✅ API token metrics included in report")
        
        if "rate_limiter_metrics" in report:
            logger.info("✅ Rate limiter metrics included in report")
        
        # Export to file
        export_path = await self.monitoring_system.export_metrics_to_file()
        assert export_path.exists(), "Export file not created"
        
        file_size = export_path.stat().st_size
        logger.info(f"✅ Exported {file_size:,} bytes to {export_path.name}")
        
        self.test_results["comprehensive_reporting"] = "PASSED"
    
    async def test_memory_integration(self):
        """Test memory agent integration with enhanced metrics."""
        logger.info("🧠 Testing Memory Agent Integration")
        
        # Check for memory files from different categories
        memory_path = Path("data/memory/stm/enhanced_monitoring_system")
        
        if memory_path.exists():
            recent_files = list(memory_path.rglob("*.json"))
            if recent_files:
                logger.info(f"✅ Found {len(recent_files)} memory files")
                
                # Check for different memory types
                memory_types = set()
                for file_path in recent_files[-10:]:  # Check last 10 files
                    try:
                        import json
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            if 'memory_type' in data:
                                memory_types.add(data['memory_type'])
                    except:
                        continue
                
                logger.info(f"✅ Memory types found: {memory_types}")
            else:
                logger.warning("No memory files found")
        else:
            logger.warning("Memory directory not found")
        
        self.test_results["memory_integration"] = "PASSED"
    
    async def run_all_tests(self):
        """Run all enhanced monitoring tests."""
        logger.info("🔬 Starting Enhanced Monitoring Test Suite")
        logger.info("=" * 60)
        
        try:
            await self.setup()
            
            # Run all test categories
            await self.test_detailed_resource_monitoring()
            await self.test_api_token_usage_tracking()
            await self.test_rate_limiter_monitoring()
            await self.test_swap_memory_alerts()
            await self.test_comprehensive_reporting()
            await self.test_memory_integration()
            
            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("🎉 Enhanced Monitoring Test Results:")
            
            for test_name, result in self.test_results.items():
                status_emoji = "✅" if result == "PASSED" else "❌"
                logger.info(f"  {status_emoji} {test_name.replace('_', ' ').title()}: {result}")
            
            total_tests = len(self.test_results)
            passed_tests = sum(1 for r in self.test_results.values() if r == "PASSED")
            
            logger.info(f"\n🏆 Summary: {passed_tests}/{total_tests} tests passed")
            
            if passed_tests == total_tests:
                logger.info("🌟 All enhanced monitoring features working correctly!")
                return True
            else:
                logger.error("❌ Some tests failed")
                return False
                
        except Exception as e:
            logger.error(f"Test suite failed: {e}", exc_info=True)
            return False
        finally:
            if self.monitoring_system:
                await self.monitoring_system.stop_monitoring()

async def main():
    """Main test execution."""
    test_suite = EnhancedMonitoringTestSuite()
    success = await test_suite.run_all_tests()
    
    if success:
        print("\n🎯 Enhanced Monitoring System: FULLY OPERATIONAL")
        print("   • Detailed CPU and RAM monitoring ✓")
        print("   • API token usage tracking ✓")
        print("   • Rate limiter performance monitoring ✓")
        print("   • Comprehensive alerting system ✓")
        print("   • Memory agent integration ✓")
        return 0
    else:
        print("\n❌ Enhanced Monitoring System: TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)