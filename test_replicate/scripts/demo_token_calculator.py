# mindx/scripts/demo_token_calculator.py
"""
Demo script showing how any agent can use the TokenCalculatorTool.
This demonstrates the tool's integration with the MindX ecosystem.

Usage: python3 scripts/demo_token_calculator.py
"""

import sys
import asyncio
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from tools.token_calculator_tool import TokenCalculatorTool
from agents.memory_agent import MemoryAgent
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

async def demo_token_calculator():
    """Demonstrate TokenCalculatorTool capabilities."""
    print("🧮 MindX TokenCalculatorTool Demo")
    print("=" * 50)
    
    # Initialize dependencies
    memory_agent = MemoryAgent()
    config = Config()
    
    # Initialize the TokenCalculatorTool
    token_calc = TokenCalculatorTool(memory_agent=memory_agent, config=config)
    
    # Demo 1: Cost Estimation
    print("\n📊 Demo 1: Cost Estimation")
    print("-" * 30)
    
    sample_prompt = "Analyze the following Python code and suggest improvements: def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
    
    result = await token_calc.execute(
        action="estimate_cost",
        text=sample_prompt,
        model="gemini-2.5-flash",
        operation_type="code_generation"
    )
    
    if result[0]:
        estimate = result[1]
        print(f"✅ Cost Estimate for Gemini 2.5 Flash:")
        print(f"   Input tokens: {estimate['estimated_input_tokens']}")
        print(f"   Output tokens: {estimate['estimated_output_tokens']}")
        print(f"   Total cost: ${estimate['total_cost_usd']:.6f}")
    else:
        print(f"❌ Cost estimation failed: {result[1]}")
    
    # Demo 2: Usage Tracking
    print("\n📈 Demo 2: Usage Tracking")
    print("-" * 30)
    
    result = await token_calc.execute(
        action="track_usage",
        agent_id="demo_agent",
        operation="code_analysis",
        model="gemini-2.5-flash",
        input_tokens=45,
        output_tokens=120,
        cost_usd=0.000165
    )
    
    if result[0]:
        tracking = result[1]
        print(f"✅ Usage tracked successfully:")
        print(f"   Daily spend: ${tracking['daily_spend']:.6f}")
        print(f"   Budget remaining: ${tracking['budget_remaining']:.2f}")
    else:
        print(f"❌ Usage tracking failed: {result[1]}")
    
    # Demo 3: Budget Check
    print("\n💰 Demo 3: Budget Status")
    print("-" * 30)
    
    result = await token_calc.execute(action="check_budget")
    
    if result[0]:
        budget = result[1]
        print(f"✅ Budget Status:")
        print(f"   Daily budget: ${budget['daily_budget']:.2f}")
        print(f"   Daily spent: ${budget['daily_spent']:.6f}")
        print(f"   Utilization: {budget['daily_utilization']:.1%}")
        print(f"   Status: {budget['status']}")
    else:
        print(f"❌ Budget check failed: {result[1]}")
    
    # Demo 4: Cost Optimization
    print("\n🔧 Demo 4: Prompt Optimization")
    print("-" * 30)
    
    long_prompt = """
    Please analyze this code thoroughly and provide detailed feedback on:
    1. Code structure and organization
    2. Performance optimizations
    3. Security considerations
    4. Best practices adherence
    5. Documentation improvements
    6. Testing recommendations
    7. Error handling enhancements
    8. Maintainability aspects
    
    Here is the code to analyze:
    def factorial(n):
        if n <= 1:
            return 1
        else:
            return n * factorial(n-1)
    
    Please provide comprehensive analysis with specific examples and code snippets.
    """
    
    result = await token_calc.execute(
        action="optimize_prompt",
        original_prompt=long_prompt,
        max_tokens=500,
        cost_budget=0.001,
        target_model="gemini-2.5-flash"
    )
    
    if result[0]:
        optimization = result[1]
        print(f"✅ Optimization Analysis:")
        print(f"   Original tokens: {optimization['original_tokens']}")
        print(f"   Original cost: ${optimization['original_cost']:.6f}")
        print(f"   Potential savings: ${optimization['potential_savings']:.6f}")
        
        if optimization['best_optimization']:
            best = optimization['best_optimization']
            print(f"   Best strategy: {best['strategy']}")
            print(f"   Optimized cost: ${best['cost']:.6f}")
    else:
        print(f"❌ Prompt optimization failed: {result[1]}")
    
    # Demo 5: Usage Report
    print("\n📋 Demo 5: Usage Report")
    print("-" * 30)
    
    result = await token_calc.execute(
        action="get_usage_report",
        days_back=7
    )
    
    if result[0]:
        report = result[1]
        if "error" not in report:
            print(f"✅ 7-Day Usage Report:")
            print(f"   Total operations: {report['total_operations']}")
            print(f"   Total cost: ${report['total_cost_usd']:.6f}")
            print(f"   Average cost per operation: ${report['average_cost_per_operation']:.6f}")
            print(f"   Daily average: ${report['daily_average_cost']:.6f}")
            
            if report.get('optimization_recommendations'):
                print(f"   Recommendations: {len(report['optimization_recommendations'])} available")
        else:
            print(f"ℹ️  No usage data available for reporting")
    else:
        print(f"❌ Usage report failed: {result[1]}")
    
    # Demo 6: Multi-Model Cost Comparison
    print("\n⚖️  Demo 6: Multi-Model Cost Comparison")
    print("-" * 30)
    
    models_to_compare = [
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gpt-4o-mini",
        "claude-3.5-haiku"
    ]
    
    comparison_text = "Summarize the key features of autonomous AI systems in 3 bullet points."
    
    print(f"Comparing costs for: '{comparison_text[:50]}...'")
    print()
    
    for model in models_to_compare:
        result = await token_calc.execute(
            action="estimate_cost",
            text=comparison_text,
            model=model,
            operation_type="simple_chat"
        )
        
        if result[0]:
            estimate = result[1]
            print(f"   {model:<20}: ${estimate['total_cost_usd']:.6f}")
        else:
            print(f"   {model:<20}: Pricing not available")
    
    print("\n🎉 TokenCalculatorTool Demo Complete!")
    print("\nThe tool is now available to all agents in the MindX system.")
    print("Any agent can call it using the same execute() method with different actions.")

if __name__ == "__main__":
    asyncio.run(demo_token_calculator()) 