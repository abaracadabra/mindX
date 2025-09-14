#!/usr/bin/env python3
"""
Real LLM Pricing Demo - Demonstrates actual pricing calculations
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring.enhanced_monitoring_system import EnhancedMonitoringSystem
import time


async def test_real_pricing_calculations():
    """Test real pricing calculations with actual provider models"""
    
    print("🎯 Real LLM Pricing Demo")
    print("=" * 60)
    
    # Initialize monitoring system
    monitoring = EnhancedMonitoringSystem(test_mode=True)
    
    print("\n💰 Testing Real Pricing Calculations:")
    
    # Test various models with 10K input, 2K output tokens
    test_scenarios = [
        # OpenAI Models
        ("openai", "gpt-4o", 10000, 2000),
        ("openai", "gpt-4o-mini", 10000, 2000),
        ("openai", "o3", 10000, 2000),
        ("openai", "o1", 10000, 2000),
        ("openai", "gpt-4.1", 10000, 2000),
        ("openai", "gpt-3.5-turbo", 10000, 2000),
        
        # Anthropic Models
        ("anthropic", "claude-4-opus", 10000, 2000),
        ("anthropic", "claude-4-sonnet", 10000, 2000),
        ("anthropic", "claude-3.5-sonnet", 10000, 2000),
        ("anthropic", "claude-3.5-haiku", 10000, 2000),
        
        # Google Models
        ("google", "gemini-2.5-pro", 10000, 2000),
        ("google", "gemini-2.5-flash", 10000, 2000),
        ("google", "gemini-1.5-pro", 10000, 2000),
        ("google", "gemini-1.5-flash", 10000, 2000),
        
        # Other Providers
        ("groq", "llama-3.1-70b", 10000, 2000),
        ("mistral", "mistral-large-2", 10000, 2000),
        ("cohere", "command-r", 10000, 2000),
        ("deepseek", "deepseek-v3", 10000, 2000),
    ]
    
    results = []
    
    for provider, model, input_tokens, output_tokens in test_scenarios:
        cost = monitoring.calculate_llm_cost(model, input_tokens, output_tokens, provider)
        cost_per_1m_in = (cost / ((input_tokens + output_tokens) / 1_000_000)) * (input_tokens / (input_tokens + output_tokens))
        cost_per_1m_out = (cost / ((input_tokens + output_tokens) / 1_000_000)) * (output_tokens / (input_tokens + output_tokens))
        
        results.append({
            "provider": provider,
            "model": model,
            "cost": cost,
            "cost_per_1k": cost * 100,  # Cost per 1K tokens (10K input + 2K output = 12K total)
        })
        
        print(f"  {provider:10} {model:20} ${cost:.6f} (${cost*100:.4f}/1K tokens)")
    
    # Sort by cost
    results_sorted = sorted(results, key=lambda x: x["cost"])
    
    print(f"\n🏆 Most Cost-Effective Models (10K input + 2K output tokens):")
    for i, result in enumerate(results_sorted[:5]):
        print(f"  {i+1}. {result['provider']}:{result['model']} - ${result['cost']:.6f}")
    
    print(f"\n💸 Most Expensive Models:")
    for i, result in enumerate(results_sorted[-5:]):
        print(f"  {i+1}. {result['provider']}:{result['model']} - ${result['cost']:.6f}")
    
    # Test API logging with automatic pricing
    print(f"\n📊 Testing API Usage Logging with Automatic Pricing:")
    
    await monitoring.log_api_token_usage(
        model_name="gpt-4o",
        provider="openai", 
        prompt_tokens=5000,
        completion_tokens=1500,
        # cost_usd=0.0,  # Will be calculated automatically
        success=True
    )
    
    await monitoring.log_api_token_usage(
        model_name="claude-3.5-haiku",
        provider="anthropic",
        prompt_tokens=8000,
        completion_tokens=2000,
        success=True
    )
    
    await monitoring.log_api_token_usage(
        model_name="gemini-1.5-flash",
        provider="google",
        prompt_tokens=12000,
        completion_tokens=3000,
        success=True
    )
    
    # Get API usage summary
    api_summary = await monitoring.get_api_usage_summary()
    
    print(f"  Total Cost: ${api_summary['total_cost']:.6f}")
    print(f"  Total Tokens: {api_summary['total_tokens']:,}")
    print(f"  Total Calls: {api_summary['total_calls']}")
    
    print(f"\n  Provider Breakdown:")
    for provider, data in api_summary['provider_summary'].items():
        print(f"    {provider}: ${data['cost']:.6f} ({data['tokens']:,} tokens, {data['calls']} calls)")
    
    # Monthly cost estimation
    print(f"\n📅 Monthly Cost Estimations (1000 calls/day):")
    
    monthly_scenarios = [
        ("openai", "gpt-4o-mini", 2000, 500),  # Efficient choice
        ("anthropic", "claude-3.5-haiku", 2000, 500),  # Fast choice
        ("google", "gemini-1.5-flash", 2000, 500),  # Google choice
        ("deepseek", "deepseek-v3", 2000, 500),  # Budget choice
    ]
    
    for provider, model, avg_input, avg_output in monthly_scenarios:
        daily_cost = monitoring.calculate_llm_cost(model, avg_input, avg_output, provider) * 1000
        monthly_cost = daily_cost * 30
        print(f"  {provider:10} {model:20} ${monthly_cost:.2f}/month (${daily_cost:.2f}/day)")
    
    # Test context-aware pricing (Google)
    print(f"\n🔍 Context-Aware Pricing Test (Google Long Context):")
    
    # Test short vs long context for Gemini
    short_context_cost = monitoring.calculate_llm_cost("gemini-1.5-pro", 50000, 2000, "google")
    long_context_cost = monitoring.calculate_llm_cost("gemini-1.5-pro-long", 200000, 2000, "google")
    
    print(f"  Gemini 1.5 Pro (50K tokens): ${short_context_cost:.6f}")
    print(f"  Gemini 1.5 Pro (200K tokens): ${long_context_cost:.6f}")
    print(f"  Long context premium: {(long_context_cost/short_context_cost - 1)*100:.1f}%")
    
    # Test efficiency comparison
    print(f"\n⚡ Efficiency Comparison (Same Task - Document Summarization):")
    
    # Simulate document summarization: 50K input, 1K output
    doc_scenarios = [
        ("openai", "gpt-4o-mini"),
        ("anthropic", "claude-3.5-haiku"),
        ("google", "gemini-1.5-flash"),
        ("groq", "llama-3.1-70b"),
        ("deepseek", "deepseek-v3"),
    ]
    
    for provider, model in doc_scenarios:
        cost = monitoring.calculate_llm_cost(model, 50000, 1000, provider)
        print(f"  {provider:10} {model:20} ${cost:.6f}")
    
    print(f"\n✅ Real pricing demonstration complete!")
    print(f"📋 All costs calculated using actual provider pricing as of January 2025")


if __name__ == "__main__":
    asyncio.run(test_real_pricing_calculations()) 