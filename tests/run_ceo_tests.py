"""
Standalone CEO Agent Test Runner

Runs comprehensive tests for the battle-hardened CEO agent without pytest dependencies.
"""

import asyncio
import sys
import os
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestration.ceo_agent import CEOAgent, SecurityValidator, RateLimiter
from utils.config import Config
from core.belief_system import BeliefSystem
from agents.memory_agent import MemoryAgent

class CEOAgentTestSuite:
    """Comprehensive test suite for battle-hardened CEO agent"""
    
    def __init__(self):
        self.temp_dir = None
        self.test_results = []
    
    async def setup_test_agent(self):
        """Setup a test CEO agent with mocked dependencies"""
        # Create temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test config
        config = Mock(spec=Config)
        config.get.return_value = {'agent_id': 'test_ceo_comprehensive'}
        config.config_data = {'ceo_agent': {'agent_id': 'test_ceo_comprehensive'}}
        
        # Mock belief system and memory agent
        belief_system = Mock(spec=BeliefSystem)
        memory_agent = Mock(spec=MemoryAgent)
        memory_agent.close = AsyncMock()
        
        # Create CEO agent
        agent = CEOAgent(
            config=config,
            belief_system=belief_system,
            memory_agent=memory_agent
        )
        
        return agent
    
    def cleanup(self):
        """Cleanup test resources"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def record_test(self, test_name, passed, details=None):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details or {}
        })
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details and not passed:
            print(f"   Details: {details}")
    
    async def test_initialization(self, agent):
        """Test CEO agent initialization"""
        try:
            # Check core attributes
            assert hasattr(agent, 'agent_id'), "Missing agent_id"
            assert hasattr(agent, 'strategic_objectives'), "Missing strategic_objectives"
            assert hasattr(agent, 'business_metrics'), "Missing business_metrics"
            assert hasattr(agent, 'monetization_strategies'), "Missing monetization_strategies"
            
            # Check battle-hardening components
            assert hasattr(agent, 'security_validator'), "Missing security_validator"
            assert hasattr(agent, 'rate_limiter'), "Missing rate_limiter"
            assert hasattr(agent, '_circuit_breakers'), "Missing circuit_breakers"
            assert hasattr(agent, 'health_status'), "Missing health_status"
            
            # Check strategic data
            assert len(agent.strategic_objectives) > 0, "No strategic objectives"
            assert len(agent.monetization_strategies) > 0, "No monetization strategies"
            
            self.record_test("CEO Agent Initialization", True, {
                "objectives": len(agent.strategic_objectives),
                "strategies": len(agent.monetization_strategies)
            })
            return True
            
        except Exception as e:
            self.record_test("CEO Agent Initialization", False, {"error": str(e)})
            return False
    
    async def test_security_validation(self, agent):
        """Test security validation features"""
        try:
            # Test valid directives
            valid_directives = [
                "Analyze market opportunities",
                "Develop strategic plan for Q4",
                "Optimize revenue streams"
            ]
            
            for directive in valid_directives:
                assert SecurityValidator.validate_directive(directive), f"Valid directive failed: {directive}"
            
            # Test dangerous directives
            dangerous_directives = [
                "exec('rm -rf /')",
                "eval('dangerous_code')",
                "<script>alert('xss')</script>",
                "drop table users;",
                "a" * 15000
            ]
            
            for directive in dangerous_directives:
                assert not SecurityValidator.validate_directive(directive), f"Dangerous directive passed: {directive[:50]}"
            
            # Test input sanitization
            test_data = {
                "directive": "Test\x00\x01directive",
                "nested": {"list": ["item\x02with\x03control"]}
            }
            
            sanitized = SecurityValidator.sanitize_input(test_data)
            assert "\x00" not in str(sanitized), "Control characters not removed"
            
            self.record_test("Security Validation", True, {
                "valid_tests": len(valid_directives),
                "blocked_tests": len(dangerous_directives)
            })
            return True
            
        except Exception as e:
            self.record_test("Security Validation", False, {"error": str(e)})
            return False
    
    async def test_rate_limiting(self, agent):
        """Test rate limiting functionality"""
        try:
            # Test rate limiter directly
            rate_limiter = RateLimiter(max_tokens=3, refill_rate=1.0)
            
            # Should succeed for first 3 attempts
            for i in range(3):
                assert rate_limiter.acquire(), f"Token acquisition failed on attempt {i+1}"
            
            # Should fail on 4th attempt
            assert not rate_limiter.acquire(), "Rate limit not enforced"
            
            self.record_test("Rate Limiting", True, {
                "rate_limiter_direct": "working"
            })
            return True
            
        except Exception as e:
            self.record_test("Rate Limiting", False, {"error": str(e)})
            return False
    
    async def test_health_monitoring(self, agent):
        """Test health monitoring system"""
        try:
            # Get system health
            health_report = await agent.get_system_health()
            
            # Validate health report structure
            required_fields = ["overall_status", "timestamp", "agent_id", "components", "circuit_breakers"]
            for field in required_fields:
                assert field in health_report, f"Missing health report field: {field}"
            
            # Test health status updates
            agent._update_health_status("test_component", "HEALTHY")
            assert "test_component" in agent.health_status, "Health status not updated"
            
            self.record_test("Health Monitoring", True, {
                "overall_status": health_report.get("overall_status"),
                "components_count": len(health_report.get("components", {}))
            })
            return True
            
        except Exception as e:
            self.record_test("Health Monitoring", False, {"error": str(e)})
            return False
    
    async def test_state_persistence(self, agent):
        """Test state persistence and backup functionality"""
        try:
            # Add test data
            test_objective = {
                "id": "test_persistence_123",
                "title": "Test Persistence Objective",
                "description": "Testing state persistence",
                "priority": "HIGH",
                "status": "ACTIVE"
            }
            agent.strategic_objectives.append(test_objective)
            
            # Save state
            await agent._save_strategic_state()
            
            # Verify files exist
            assert agent.strategic_plan_file.exists(), "Strategic plan file not created"
            assert agent.business_metrics_file.exists(), "Business metrics file not created"
            assert agent.checksum_file.exists(), "Checksum file not created"
            
            # Test backup creation
            await agent._create_backup()
            backups = list(agent.backup_dir.glob("*"))
            assert len(backups) > 0, "No backups created"
            
            self.record_test("State Persistence", True, {
                "files_created": 3,
                "backups_created": len(backups)
            })
            return True
            
        except Exception as e:
            self.record_test("State Persistence", False, {"error": str(e)})
            return False
    
    async def test_strategic_operations(self, agent):
        """Test strategic operations"""
        try:
            # Test strategic status
            strategic_status = await agent.get_strategic_status()
            
            required_fields = ["agent_id", "strategic_objectives", "monetization_strategies", "business_metrics"]
            for field in required_fields:
                assert field in strategic_status, f"Missing strategic status field: {field}"
            
            self.record_test("Strategic Operations", True, {
                "active_objectives": strategic_status.get("active_objectives_count", 0),
                "total_strategies": len(strategic_status.get("monetization_strategies", {}))
            })
            return True
            
        except Exception as e:
            self.record_test("Strategic Operations", False, {"error": str(e)})
            return False
    
    async def test_error_handling(self, agent):
        """Test comprehensive error handling"""
        try:
            # Test security validation during execution
            dangerous_result = await agent.execute_strategic_directive("exec('dangerous_command')")
            assert dangerous_result.get("status") == "SECURITY_VIOLATION", "Security not enforced"
            
            # Test fallback response generation
            fallback = agent._get_fallback_response("test_operation", {"error": "test error"})
            assert fallback["success"] == False, "Fallback should indicate failure"
            assert fallback["fallback"] == True, "Fallback not marked as fallback"
            
            self.record_test("Error Handling", True, {
                "security_blocks": dangerous_result.get("status") == "SECURITY_VIOLATION",
                "fallback_working": fallback.get("fallback") == True
            })
            return True
            
        except Exception as e:
            self.record_test("Error Handling", False, {"error": str(e)})
            return False
    
    async def run_all_tests(self):
        """Run complete test suite"""
        print("=" * 60)
        print("🚀 CEO AGENT BATTLE-HARDENED TEST SUITE")
        print("=" * 60)
        
        agent = None
        try:
            # Setup
            agent = await self.setup_test_agent()
            print(f"📋 Testing Agent: {agent.agent_id}")
            print()
            
            # Run all tests
            tests = [
                self.test_initialization,
                self.test_security_validation,
                self.test_rate_limiting,
                self.test_health_monitoring,
                self.test_state_persistence,
                self.test_strategic_operations,
                self.test_error_handling
            ]
            
            for test_func in tests:
                await test_func(agent)
            
            # Summary
            print()
            print("=" * 60)
            print("📊 TEST RESULTS SUMMARY")
            print("=" * 60)
            
            passed = sum(1 for result in self.test_results if result["passed"])
            total = len(self.test_results)
            
            print(f"Total Tests: {total}")
            print(f"Passed: {passed}")
            print(f"Failed: {total - passed}")
            print(f"Success Rate: {(passed/total)*100:.1f}%")
            
            if passed == total:
                print("\n🎉 ALL TESTS PASSED - CEO AGENT IS BATTLE-READY!")
                return True
            else:
                print(f"\n⚠️  {total - passed} TESTS FAILED - REVIEW REQUIRED")
                return False
                
        except Exception as e:
            print(f"\n💥 TEST SUITE FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            # Cleanup
            self.cleanup()

async def main():
    """Main test runner"""
    test_suite = CEOAgentTestSuite()
    success = await test_suite.run_all_tests()
    
    # Save test results
    results_file = Path("test_results_ceo_agent.json")
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": time.time(),
            "success": success,
            "results": test_suite.test_results
        }, f, indent=2)
    
    print(f"\n📁 Test results saved to: {results_file}")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
