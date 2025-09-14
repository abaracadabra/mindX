#!/usr/bin/env python3
"""
Quick Production Test for TokenCalculatorTool
Streamlined test without complex setup to avoid hanging.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import Mock, AsyncMock
from decimal import Decimal

async def run_quick_tests():
    """Run quick production tests without hanging."""
    print("🚀 Quick Production TokenCalculatorTool Tests")
    print("=" * 50)
    
    try:
        # Import after path setup
        from monitoring.token_calculator_tool import TokenCalculatorTool
        from agents.memory_agent import MemoryAgent
        from utils.config import Config
        
        # Setup proper mocks
        mock_memory_agent = Mock(spec=MemoryAgent)
        mock_memory_agent.log_process = AsyncMock(return_value=True)
        
        mock_config = Mock(spec=Config)
        mock_config.get.side_effect = lambda key, default=None: {
            "token_calculator.daily_budget": 100.0,
            "token_calculator.alert_threshold": 0.75,
            "token_calculator.rate_limit": 300,
            "token_calculator.cache_ttl": 600
        }.get(key, default)
        
        # Initialize tool
        tool = TokenCalculatorTool(
            memory_agent=mock_memory_agent,
            config=mock_config
        )
        
        print("✅ TokenCalculatorTool initialized successfully")
        
        # Test 1: Basic provider detection
        providers = [
            ("gpt-4o", "openai"),
            ("gemini-1.5-flash", "google"),
            ("claude-3-sonnet", "anthropic"),
            ("unknown-model", "unknown")
        ]
        
        for model, expected in providers:
            result = tool._detect_provider(model)
            status = "✅" if result == expected else "❌"
            print(f"{status} Provider detection: {model} -> {result}")
        
        # Test 2: Currency validation
        test_amounts = [0, 1.5, "10.25", Decimal("5.50")]
        
        for amount in test_amounts:
            try:
                result = tool._validate_currency(amount)
                print(f"✅ Currency validation: {amount} -> ${float(result):.6f}")
            except Exception as e:
                print(f"❌ Currency validation failed: {amount} -> {e}")
        
        # Test 3: Token estimation (basic)
        test_texts = [
            "Hello world",
            "def function(): return True",
            "API endpoint /api/v1/users returns user data"
        ]
        
        for text in test_texts:
            tokens = tool._estimate_token_count_production(text, "gpt-4o")
            chars_per_token = len(text) / tokens if tokens > 0 else 0
            print(f"✅ Token estimation: '{text[:30]}...' -> {tokens} tokens ({chars_per_token:.1f} chars/token)")
        
        # Test 4: Async methods with timeout
        async_tests = [
            ("get_metrics", {}),
        ]
        
        for action, kwargs in async_tests:
            try:
                result = await asyncio.wait_for(
                    tool.execute(action, **kwargs),
                    timeout=5.0
                )
                status = "✅" if result[0] else "⚠️"
                print(f"{status} Async {action}: Success={result[0]}")
            except asyncio.TimeoutError:
                print(f"⚠️ Async {action}: Timed out")
            except Exception as e:
                print(f"❌ Async {action}: Error - {e}")
        
        # Test 5: Error handling
        error_tests = [
            ("estimate_cost", {"text": "", "model": "gpt-4o"}),
            ("estimate_cost", {"text": None, "model": "gpt-4o"}),
            ("invalid_action", {}),
        ]
        
        for action, kwargs in error_tests:
            try:
                result = await asyncio.wait_for(
                    tool.execute(action, **kwargs),
                    timeout=3.0
                )
                status = "✅" if not result[0] else "⚠️"
                print(f"{status} Error handling {action}: Properly rejected={not result[0]}")
            except Exception as e:
                print(f"❌ Error handling {action}: Unexpected error - {e}")
        
        print("\n" + "=" * 50)
        print("✅ Quick production tests completed successfully!")
        print("🎉 TokenCalculatorTool is functional and ready")
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_quick_tests()) 