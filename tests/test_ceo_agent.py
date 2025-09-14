#!/usr/bin/env python3
"""
Battle-Hardened CEO Agent Test Suite

Comprehensive testing for the CEO Agent including:
- Core functionality validation
- Security and resilience testing
- Error handling and recovery
- Performance under stress
- Circuit breaker and health monitoring
- State persistence and integrity
"""

import asyncio
import pytest
import json
import tempfile
import shutil
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestration.ceo_agent import CEOAgent, SecurityValidator, RateLimiter, CircuitBreakerState
from utils.config import Config
from core.belief_system import BeliefSystem
from agents.memory_agent import MemoryAgent

class TestCEOAgentBattleHardened:
    """Battle-hardened test suite for CEO Agent"""
    
    @pytest.fixture
    async def ceo_agent(self):
        """Create a test CEO agent with temporary directories"""
        # Create temporary directory for test
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test config
        config = Config()
        config.config_data = {
            'ceo_agent': {
                'agent_id': 'test_ceo_battle_hardened'
            },
            'data_dir': self.temp_dir
        }
        
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
        
        yield agent
        
        # Cleanup
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_ceo_agent_initialization_resilience(self, ceo_agent):
        """Test CEO agent initialization under various conditions"""
        
        # Test basic initialization
        assert ceo_agent.agent_id is not None
        assert ceo_agent.strategic_objectives is not None
        assert ceo_agent.business_metrics is not None
        assert ceo_agent.monetization_strategies is not None
        
        # Test battle hardening components
        assert hasattr(ceo_agent, 'security_validator')
        assert hasattr(ceo_agent, 'rate_limiter')
        assert hasattr(ceo_agent, '_circuit_breakers')
        assert hasattr(ceo_agent, 'health_status')
        
        # Test circuit breakers initialized
        expected_breakers = ["strategic_directive", "monetization_campaign", "bdi_execution", "state_persistence"]
        for breaker_name in expected_breakers:
            assert breaker_name in ceo_agent._circuit_breakers
            assert ceo_agent._circuit_breakers[breaker_name].state == "CLOSED"
    
    @pytest.mark.asyncio
    async def test_security_validation(self, ceo_agent):
        """Test security validation and input sanitization"""
        
        # Test valid directives
        valid_directives = [
            "Analyze market opportunities",
            "Develop strategic plan for Q4",
            "Optimize revenue streams"
        ]
        
        for directive in valid_directives:
            assert SecurityValidator.validate_directive(directive) == True
        
        # Test invalid/dangerous directives
        dangerous_directives = [
            "exec('rm -rf /')",
            "import subprocess; subprocess.call(['rm', '-rf', '/'])",
            "eval('__import__(\\'os\\').system(\\'dangerous\\')')",
            "<script>alert('xss')</script>",
            "DROP TABLE users;",
            "a" * 15000  # Too long
        ]
        
        for directive in dangerous_directives:
            assert SecurityValidator.validate_directive(directive) == False
        
        # Test input sanitization
        test_data = {
            "directive": "Test\x00\x01directive",  # Control characters
            "nested": {
                "list": ["item1", "item\x02with\x03control"]
            }
        }
        
        sanitized = SecurityValidator.sanitize_input(test_data)
        assert "\x00" not in str(sanitized)
        assert "\x01" not in str(sanitized)
        assert "\x02" not in str(sanitized)
        assert "\x03" not in str(sanitized)
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, ceo_agent):
        """Test rate limiting functionality"""
        
        # Test rate limiter directly
        rate_limiter = RateLimiter(max_tokens=5, refill_rate=1.0)
        
        # Should be able to acquire up to max_tokens
        for i in range(5):
            assert rate_limiter.acquire() == True
        
        # Next acquisition should fail
        assert rate_limiter.acquire() == False
        
        # Wait for refill and try again
        time.sleep(1.1)
        assert rate_limiter.acquire() == True
        
        # Test CEO agent rate limiting
        # Rapid fire directives should trigger rate limiting
        results = []
        for i in range(60):  # Exceed rate limit
            result = await ceo_agent.execute_strategic_directive(
                f"Test directive {i}",
                {"test": True}
            )
            results.append(result)
        
        # Should have some rate limited responses
        rate_limited = [r for r in results if r.get("status") == "RATE_LIMITED"]
        assert len(rate_limited) > 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, ceo_agent):
        """Test circuit breaker patterns"""
        
        # Mock BDI agent to always fail
        mock_bdi = AsyncMock()
        mock_bdi.start_reasoning_cycle = AsyncMock(side_effect=Exception("Simulated failure"))
        ceo_agent.strategic_bdi = mock_bdi
        
        # Execute directives until circuit breaker opens
        breaker = ceo_agent._circuit_breakers["strategic_directive"]
        initial_threshold = breaker.failure_threshold
        
        results = []
        for i in range(initial_threshold + 2):
            result = await ceo_agent.execute_strategic_directive(
                f"Test failing directive {i}",
                {"test": True}
            )
            results.append(result)
        
        # Circuit breaker should be open after threshold failures
        assert breaker.state == "OPEN"
        
        # Subsequent calls should be blocked
        blocked_result = await ceo_agent.execute_strategic_directive(
            "Should be blocked",
            {"test": True}
        )
        assert blocked_result.get("status") == "CIRCUIT_BREAKER_OPEN"
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self, ceo_agent):
        """Test comprehensive health monitoring"""
        
        # Wait for initial health check
        await asyncio.sleep(0.1)
        
        # Get system health
        health_report = await ceo_agent.get_system_health()
        
        # Validate health report structure
        assert "overall_status" in health_report
        assert "timestamp" in health_report
        assert "agent_id" in health_report
        assert "components" in health_report
        assert "circuit_breakers" in health_report
        assert "performance_metrics" in health_report
        assert "recommendations" in health_report
        
        # Test health status updates
        ceo_agent._update_health_status("test_component", "HEALTHY")
        assert "test_component" in ceo_agent.health_status
        assert ceo_agent.health_status["test_component"].status == "HEALTHY"
        
        ceo_agent._update_health_status("test_component", "CRITICAL", {"error": "test error"})
        assert ceo_agent.health_status["test_component"].status == "CRITICAL"
        assert ceo_agent.health_status["test_component"].error_count == 1
        
        # Test overall status determination
        health_report = await ceo_agent.get_system_health()
        # Should be CRITICAL due to test_component being critical
        assert health_report["overall_status"] in ["CRITICAL", "DEGRADED"]
    
    @pytest.mark.asyncio
    async def test_state_persistence_and_recovery(self, ceo_agent):
        """Test atomic state operations and backup/recovery"""
        
        # Add test data
        test_objective = {
            "id": "test_objective_123",
            "title": "Test Objective",
            "description": "Test strategic objective",
            "priority": "HIGH",
            "status": "ACTIVE"
        }
        ceo_agent.strategic_objectives.append(test_objective)
        
        # Save state
        await ceo_agent._save_strategic_state()
        
        # Verify files exist
        assert ceo_agent.strategic_plan_file.exists()
        assert ceo_agent.business_metrics_file.exists()
        assert ceo_agent.checksum_file.exists()
        
        # Verify checksums
        checksum_valid = await ceo_agent._verify_file_checksums()
        assert checksum_valid == True
        
        # Test backup creation
        await ceo_agent._create_backup()
        backups = list(ceo_agent.backup_dir.glob("*"))
        assert len(backups) > 0
        
        # Simulate data corruption
        ceo_agent.strategic_plan_file.write_text("corrupted data")
        
        # Verify checksum fails
        checksum_valid = await ceo_agent._verify_file_checksums()
        assert checksum_valid == False
        
        # Test recovery from backup
        recovery_success = await ceo_agent._recover_from_backup()
        assert recovery_success == True
        
        # Verify data recovered
        assert test_objective in ceo_agent.strategic_objectives
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, ceo_agent):
        """Test CEO agent under concurrent load"""
        
        # Mock successful BDI execution
        mock_bdi = AsyncMock()
        mock_bdi.start_reasoning_cycle = AsyncMock(return_value={
            "success": True,
            "result": "Strategic analysis completed"
        })
        ceo_agent.strategic_bdi = mock_bdi
        
        # Execute multiple concurrent directives
        tasks = []
        for i in range(10):
            task = ceo_agent.execute_strategic_directive(
                f"Concurrent directive {i}",
                {"concurrent": True, "index": i}
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate results
        successful_results = [r for r in results if not isinstance(r, Exception) and r.get("success")]
        assert len(successful_results) > 0
        
        # Test concurrent state operations
        state_tasks = []
        for i in range(5):
            state_tasks.append(ceo_agent._save_strategic_state())
        
        # Should handle concurrent state saves gracefully
        await asyncio.gather(*state_tasks, return_exceptions=True)
    
    @pytest.mark.asyncio
    async def test_error_handling_and_fallbacks(self, ceo_agent):
        """Test comprehensive error handling and fallback mechanisms"""
        
        # Test BDI initialization failure
        with patch.object(ceo_agent, 'strategic_bdi', None):
            # Mock BDIAgent to raise exception
            with patch('orchestration.ceo_agent.BDIAgent', side_effect=Exception("BDI init failed")):
                try:
                    await ceo_agent.async_init_components()
                    # Should handle gracefully
                except Exception:
                    pass  # Expected to handle gracefully
        
        # Test filesystem errors
        # Make work directory read-only
        original_mode = os.stat(ceo_agent.work_dir).st_mode
        try:
            os.chmod(ceo_agent.work_dir, 0o444)  # Read-only
            
            # State save should handle gracefully
            try:
                await ceo_agent._save_strategic_state()
            except Exception:
                pass  # Should be handled gracefully
                
        finally:
            # Restore permissions
            os.chmod(ceo_agent.work_dir, original_mode)
        
        # Test fallback responses
        fallback = ceo_agent._get_fallback_response("test_operation", {"error": "test error"})
        assert fallback["success"] == False
        assert fallback["fallback"] == True
        assert "recommendations" in fallback
    
    @pytest.mark.asyncio
    async def test_performance_under_stress(self, ceo_agent):
        """Test CEO agent performance under stress conditions"""
        
        # Mock fast BDI execution
        mock_bdi = AsyncMock()
        mock_bdi.start_reasoning_cycle = AsyncMock(return_value={
            "success": True,
            "result": "Fast strategic analysis"
        })
        ceo_agent.strategic_bdi = mock_bdi
        
        # Stress test: rapid sequential operations
        start_time = time.time()
        results = []
        
        for i in range(20):  # 20 rapid operations
            result = await ceo_agent.execute_strategic_directive(
                f"Stress test directive {i}",
                {"stress_test": True}
            )
            results.append(result)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert duration < 30.0  # 30 seconds max for 20 operations
        
        # Most operations should succeed or be rate limited
        successful_or_limited = [
            r for r in results 
            if r.get("success") or r.get("status") == "RATE_LIMITED"
        ]
        assert len(successful_or_limited) >= 15  # At least 75% success rate
    
    @pytest.mark.asyncio
    async def test_monetization_campaign_resilience(self, ceo_agent):
        """Test monetization campaign execution under various conditions"""
        
        # Test valid campaign launch
        campaign_result = await ceo_agent.launch_monetization_campaign(
            "swaas_platform",
            {
                "target_clients": 10,
                "duration_days": 30,
                "budget": 5000.0
            }
        )
        
        # Should return structured response
        assert "campaign_id" in campaign_result
        assert "status" in campaign_result
        
        # Test invalid strategy name
        invalid_result = await ceo_agent.launch_monetization_campaign(
            "nonexistent_strategy",
            {"test": True}
        )
        
        # Should handle gracefully
        assert invalid_result.get("success") == False or invalid_result.get("fallback") == True
        
        # Test campaign with malicious parameters
        malicious_result = await ceo_agent.launch_monetization_campaign(
            "swaas_platform",
            {
                "evil_param": "exec('rm -rf /')",
                "script_injection": "<script>alert('xss')</script>"
            }
        )
        
        # Should be sanitized and handled safely
        assert "campaign_id" in malicious_result or malicious_result.get("fallback") == True
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, ceo_agent):
        """Test graceful shutdown functionality"""
        
        # Add some test data
        ceo_agent.strategic_objectives.append({
            "id": "shutdown_test",
            "title": "Shutdown Test Objective",
            "description": "Test data for shutdown",
            "priority": "LOW",
            "status": "TESTING"
        })
        
        # Trigger graceful shutdown
        await ceo_agent._graceful_shutdown()
        
        # Should have saved state before shutdown
        assert ceo_agent.strategic_plan_file.exists()
        
        # Load saved data to verify
        with open(ceo_agent.strategic_plan_file, 'r') as f:
            saved_data = json.load(f)
        
        # Should contain test objective
        objectives = saved_data.get("strategic_objectives", [])
        shutdown_test_obj = next((obj for obj in objectives if obj.get("id") == "shutdown_test"), None)
        assert shutdown_test_obj is not None
    
    @pytest.mark.asyncio
    async def test_strategic_data_validation(self, ceo_agent):
        """Test strategic data validation and integrity checks"""
        
        # Test with valid data
        try:
            ceo_agent._validate_strategic_data()
        except Exception as e:
            pytest.fail(f"Valid data failed validation: {e}")
        
        # Test with invalid strategic objectives
        original_objectives = ceo_agent.strategic_objectives.copy()
        ceo_agent.strategic_objectives = [{"invalid": "objective"}]  # Missing required fields
        
        with pytest.raises(ValueError, match="missing required field"):
            ceo_agent._validate_strategic_data()
        
        # Restore valid data
        ceo_agent.strategic_objectives = original_objectives
        
        # Test with invalid business metrics
        original_metrics = ceo_agent.business_metrics.copy()
        ceo_agent.business_metrics = {"invalid": "metrics"}  # Missing required sections
        
        with pytest.raises(ValueError, match="missing required section"):
            ceo_agent._validate_strategic_data()
        
        # Restore valid data
        ceo_agent.business_metrics = original_metrics
    
    def test_security_validator_edge_cases(self):
        """Test security validator with edge cases"""
        
        # Test empty/None input
        assert SecurityValidator.validate_directive("") == False
        assert SecurityValidator.validate_directive(None) == False
        
        # Test extremely long input
        long_directive = "a" * 20000
        assert SecurityValidator.validate_directive(long_directive) == False
        
        # Test case sensitivity
        assert SecurityValidator.validate_directive("EXEC('test')") == False
        assert SecurityValidator.validate_directive("Exec('test')") == False
        
        # Test nested dangerous patterns
        assert SecurityValidator.validate_directive("Please exec('safe_command')") == False
        
        # Test legitimate directives that might contain similar patterns
        legitimate_directives = [
            "Execute the strategic plan",  # Contains "execute" but not "exec("
            "Delete obsolete strategies",  # Contains "delete" but not dangerous
            "Drop the old pricing model"   # Contains "drop" but not SQL
        ]
        
        for directive in legitimate_directives:
            assert SecurityValidator.validate_directive(directive) == True

@pytest.mark.asyncio
async def test_integration_with_mock_dependencies():
    """Test CEO agent integration with mocked dependencies"""
    
    # Create comprehensive mocks
    config = Mock(spec=Config)
    config.get.return_value = {'agent_id': 'integration_test_ceo'}
    
    belief_system = Mock(spec=BeliefSystem)
    memory_agent = Mock(spec=MemoryAgent)
    memory_agent.close = AsyncMock()
    
    # Create CEO agent
    with tempfile.TemporaryDirectory() as temp_dir:
        ceo_agent = CEOAgent(
            config=config,
            belief_system=belief_system,
            memory_agent=memory_agent
        )
        
        # Test basic functionality
        assert ceo_agent is not None
        
        # Test strategic status
        status = await ceo_agent.get_strategic_status()
        assert "agent_id" in status
        assert "strategic_objectives" in status
        
        # Test health reporting
        health = await ceo_agent.get_system_health()
        assert "overall_status" in health

if __name__ == "__main__":
    # Run specific battle-hardened tests
    pytest.main([__file__, "-v", "--tb=short"]) 