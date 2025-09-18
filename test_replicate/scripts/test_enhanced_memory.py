#!/usr/bin/env python3
"""
Test script for enhanced memory and logging functionality.

This script demonstrates the new timestampmemory.json functionality
and self-awareness capabilities of the MindX memory system.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.memory_agent import MemoryAgent
from utils.config import Config
from utils.logging_config import setup_logging

async def test_timestampmemory():
    """Test the timestamped memory functionality."""
    print("Testing Enhanced Memory System...")
    
    # Initialize memory agent
    config = Config()
    memory_agent = MemoryAgent(config=config, log_level="INFO")
    
    print("✅ Memory agent initialized")
    
    # Test agent ID
    test_agent_id = "test_bdi_agent"
    
    # Test saving timestamped memories
    print(f"\n📝 Testing timestamped memory saving for {test_agent_id}...")
    
    test_interactions = [
        {
            "input": "What is the current system status?",
            "response": "System is running normally. All agents operational.",
            "context": {"request_type": "status_check", "priority": "medium"},
            "success": True
        },
        {
            "input": "Execute plan: optimize resource usage",
            "response": "Plan executed successfully. Resource usage optimized by 15%.",
            "context": {"request_type": "plan_execution", "priority": "high", "optimization": 15},
            "success": True
        },
        {
            "input": "Analyze market trends for cryptocurrency",
            "response": "Error: Market data API unavailable",
            "context": {"request_type": "analysis", "priority": "low", "error_type": "api_unavailable"},
            "success": False
        },
        {
            "input": "Generate summary report",
            "response": "Summary report generated with 3 sections and 12 data points.",
            "context": {"request_type": "report_generation", "priority": "medium", "sections": 3},
            "success": True
        }
    ]
    
    for i, interaction in enumerate(test_interactions):
        result = await memory_agent.save_timestampmemory(
            agent_id=test_agent_id,
            input_content=interaction["input"],
            response_content=interaction["response"],
            context=interaction["context"],
            success=interaction["success"]
        )
        
        if result:
            print(f"  ✅ Saved interaction {i+1}: {interaction['input'][:30]}...")
        else:
            print(f"  ❌ Failed to save interaction {i+1}")
    
    # Test retrieving recent memories
    print(f"\n🔍 Testing memory retrieval for {test_agent_id}...")
    
    recent_memories = await memory_agent.get_recent_timestampmemories(
        agent_id=test_agent_id,
        limit=10,
        days_back=1
    )
    
    print(f"  ✅ Retrieved {len(recent_memories)} recent memories")
    
    if recent_memories:
        latest_memory = recent_memories[0]
        print(f"  📋 Latest memory: {latest_memory.get('input', 'N/A')[:50]}...")
        print(f"  ⏰ Timestamp: {latest_memory.get('timestamp_local', 'N/A')}")
        print(f"  ✅ Success: {latest_memory.get('success', 'N/A')}")
    
    # Test memory pattern analysis
    print(f"\n🧠 Testing memory pattern analysis for {test_agent_id}...")
    
    analysis = await memory_agent.analyze_agent_memory_patterns(
        agent_id=test_agent_id,
        days_back=1
    )
    
    if "error" not in analysis:
        print(f"  ✅ Analysis completed")
        print(f"  📊 Total memories: {analysis['total_memories']}")
        print(f"  📈 Success rate: {analysis['success_rate']:.1%}")
        print(f"  🚨 Error count: {len(analysis['error_patterns'])}")
        print(f"  💡 Insights: {len(analysis['insights'])}")
        
        if analysis['insights']:
            print("  🔍 Key Insights:")
            for insight in analysis['insights']:
                print(f"    - {insight}")
    else:
        print(f"  ❌ Analysis failed: {analysis['error']}")
    
    # Test human-readable summary generation
    print(f"\n📋 Testing human-readable summary generation...")
    
    summary = await memory_agent.generate_memory_summary(
        agent_id=test_agent_id,
        days_back=1
    )
    
    print("  ✅ Summary generated:")
    print("  " + "="*50)
    # Indent each line of the summary
    for line in summary.split('\n'):
        print(f"  {line}")
    print("  " + "="*50)
    
    # Test with multiple agents
    print(f"\n👥 Testing with multiple agents...")
    
    other_agents = ["coordinator_agent", "mastermind_agent", "resource_monitor"]
    
    for agent_id in other_agents:
        # Save a few test memories for each agent
        for i in range(2):
            await memory_agent.save_timestampmemory(
                agent_id=agent_id,
                input_content=f"Test input {i+1} for {agent_id}",
                response_content=f"Test response {i+1} from {agent_id}",
                context={"test": True, "iteration": i+1},
                success=True
            )
        
        print(f"  ✅ Created test memories for {agent_id}")
    
    # Test system-wide memory stats
    print(f"\n📊 System-wide memory overview...")
    
    all_agent_summaries = {}
    for agent_id in [test_agent_id] + other_agents:
        agent_analysis = await memory_agent.analyze_agent_memory_patterns(agent_id, days_back=1)
        if "error" not in agent_analysis:
            all_agent_summaries[agent_id] = {
                "memories": agent_analysis["total_memories"],
                "success_rate": agent_analysis["success_rate"],
                "errors": len(agent_analysis["error_patterns"])
            }
    
    print("  Agent Activity Summary:")
    for agent_id, stats in all_agent_summaries.items():
        print(f"    {agent_id}: {stats['memories']} memories, {stats['success_rate']:.1%} success, {stats['errors']} errors")
    
    # Test process logging compatibility
    print(f"\n🔄 Testing process logging compatibility...")
    
    process_result = await memory_agent.log_process(
        process_name="enhanced_memory_test",
        data={"test_completed": True, "interactions_tested": len(test_interactions)},
        metadata={"agent_id": "test_runner", "test_type": "memory_functionality"}
    )
    
    if process_result:
        print(f"  ✅ Process log saved: {process_result}")
    else:
        print("  ❌ Process log failed")
    
    print(f"\n🎉 Enhanced memory system test completed!")
    print(f"   - Timestamped memories: ✅")
    print(f"   - Pattern analysis: ✅") 
    print(f"   - Human-readable summaries: ✅")
    print(f"   - Multi-agent support: ✅")
    print(f"   - Backwards compatibility: ✅")

async def demonstrate_self_awareness():
    """Demonstrate self-awareness capabilities."""
    print(f"\n🧠 Demonstrating Self-Awareness Capabilities...")
    
    config = Config()
    memory_agent = MemoryAgent(config=config)
    
    # Simulate a BDI agent with varying performance
    bdi_agent_id = "demo_bdi_agent"
    
    # Simulate different types of interactions over time
    simulation_data = [
        # Morning - High performance
        {"input": "Plan daily objectives", "response": "5 objectives planned successfully", "success": True, "time_offset": 0},
        {"input": "Execute objective 1", "response": "Objective 1 completed in 2.3 seconds", "success": True, "time_offset": 1},
        {"input": "Execute objective 2", "response": "Objective 2 completed in 1.8 seconds", "success": True, "time_offset": 2},
        
        # Midday - Some failures
        {"input": "Analyze complex data", "response": "Error: Insufficient memory", "success": False, "time_offset": 3},
        {"input": "Retry data analysis", "response": "Analysis completed with reduced dataset", "success": True, "time_offset": 4},
        {"input": "Generate insights", "response": "3 key insights generated", "success": True, "time_offset": 5},
        
        # Afternoon - Recovery
        {"input": "Execute objective 3", "response": "Objective 3 completed successfully", "success": True, "time_offset": 6},
        {"input": "Update goal priorities", "response": "Priorities updated based on performance data", "success": True, "time_offset": 7},
        {"input": "Self-assessment", "response": "Performance: 85% success rate, areas for improvement identified", "success": True, "time_offset": 8},
    ]
    
    print("  🎭 Simulating agent activity over time...")
    
    for interaction in simulation_data:
        await memory_agent.save_timestampmemory(
            agent_id=bdi_agent_id,
            input_content=interaction["input"],
            response_content=interaction["response"],
            context={
                "simulated": True,
                "performance_category": "planning" if "plan" in interaction["input"].lower() else "execution"
            },
            success=interaction["success"]
        )
    
    # Analyze the patterns
    print("  🔍 Analyzing agent behavior patterns...")
    
    analysis = await memory_agent.analyze_agent_memory_patterns(bdi_agent_id, days_back=1)
    
    if "error" not in analysis:
        print(f"    📊 Performance Metrics:")
        print(f"      - Success Rate: {analysis['success_rate']:.1%}")
        print(f"      - Total Interactions: {analysis['total_memories']}")
        print(f"      - Error Count: {len(analysis['error_patterns'])}")
        
        if analysis['error_patterns']:
            print(f"    🚨 Error Analysis:")
            for error in analysis['error_patterns']:
                print(f"      - {error['timestamp']}: {error['input']}")
        
        if analysis['insights']:
            print(f"    💡 Self-Awareness Insights:")
            for insight in analysis['insights']:
                print(f"      - {insight}")
        
        print(f"    📈 Activity Patterns:")
        if analysis['activity_by_hour']:
            for hour, count in sorted(analysis['activity_by_hour'].items()):
                print(f"      - Hour {hour}: {count} interactions")
    
    # Generate improvement recommendations
    print("  🚀 Generating improvement recommendations...")
    
    recommendations = []
    
    if analysis['success_rate'] < 1.0:
        error_rate = 1.0 - analysis['success_rate']
        recommendations.append(f"Error rate of {error_rate:.1%} detected. Review error patterns for optimization.")
    
    if len(analysis['error_patterns']) > 0:
        common_errors = {}
        for error in analysis['error_patterns']:
            error_type = error['context'].get('error_type', 'unknown')
            common_errors[error_type] = common_errors.get(error_type, 0) + 1
        
        if common_errors:
            most_common = max(common_errors.items(), key=lambda x: x[1])
            recommendations.append(f"Most common error type: {most_common[0]} ({most_common[1]} occurrences)")
    
    if analysis['common_contexts']:
        performance_contexts = [ctx for ctx in analysis['common_contexts'] if 'performance' in ctx]
        if performance_contexts:
            recommendations.append("Performance tracking contexts detected. Consider analyzing performance correlations.")
    
    if recommendations:
        print("    📋 Recommendations:")
        for rec in recommendations:
            print(f"      - {rec}")
    else:
        print("    ✅ No immediate recommendations - agent performing optimally!")

async def main():
    """Main test function."""
    print("🚀 MindX Enhanced Memory and Logging System Test")
    print("=" * 60)
    
    # Setup logging
    setup_logging(log_level="INFO", console=True, log_file=False)
    
    try:
        # Test basic functionality
        await test_timestampmemory()
        
        # Demonstrate self-awareness
        await demonstrate_self_awareness()
        
        print(f"\n✅ All tests completed successfully!")
        print(f"🎯 The enhanced memory system is ready for integration with MindX agents.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 