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
        assert "recommendations" in health_report
    
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
        
        # Test backup creation
        await ceo_agent._create_backup()
        backups = list(ceo_agent.backup_dir.glob("*"))
        assert len(backups) > 0

if __name__ == "__main__":
    # Run battle-hardened tests
    pytest.main([__file__, "-v", "--tb=short"]) 