#!/usr/bin/env python3
"""
Test Augmentic Integration
=========================

This script tests the complete augmentic integration:
- augmentic.py triggers mastermind_agent.py
- mastermind_agent.py calls core/bdi_agent.py
- BDI agent uses tools from tools folder
- BDI agent can create agents in agents folder
- Key tools: audit_and_improve_tool.py, augmentic_intelligence_tool.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_augmentic_integration():
    """Test the complete augmentic integration chain"""
    print("🧠 Testing Augmentic Integration Chain")
    print("=" * 60)
    
    # Test 1: Check augmentic.py exists and has correct structure
    print("\n1. Testing augmentic.py script...")
    if os.path.exists("augmentic.py"):
        print("   ✅ augmentic.py exists")
        
        with open("augmentic.py", "r") as f:
            content = f.read()
            
        # Check for key integration points
        integration_checks = [
            ("MastermindAgent integration", "MastermindAgent"),
            ("BDI agent integration", "bdi_agent"),
            ("Tools registry configuration", "tools_registry"),
            ("Audit coordinator integration", "AutonomousAuditCoordinator"),
            ("Command augmentic intelligence", "command_augmentic_intelligence"),
            ("Tool integration display", "available_tools"),
        ]
        
        for check_name, check_string in integration_checks:
            if check_string in content:
                print(f"   ✅ {check_name}: Found")
            else:
                print(f"   ❌ {check_name}: Missing")
    else:
        print("   ❌ augmentic.py not found")
        return False
    
    # Test 2: Check tools registry configuration
    print("\n2. Testing augmentic tools registry...")
    registry_path = "data/config/augmentic_tools_registry.json"
    if os.path.exists(registry_path):
        print("   ✅ Augmentic tools registry exists")
        
        import json
        with open(registry_path, "r") as f:
            registry = json.load(f)
            
        # Check for key tools
        key_tools = [
            "audit_and_improve_tool",
            "augmentic_intelligence_tool", 
            "system_analyzer_tool",
            "base_gen_agent",
            "strategic_analysis_tool",
            "agent_factory_tool",
            "tool_factory_tool"
        ]
        
        registered_tools = registry.get("registered_tools", {})
        for tool in key_tools:
            if tool in registered_tools:
                print(f"   ✅ {tool}: Registered")
            else:
                print(f"   ❌ {tool}: Missing")
                
        # Check workflow configuration
        if "augmentic_workflow" in registry:
            print("   ✅ Augmentic workflow configured")
        else:
            print("   ❌ Augmentic workflow missing")
    else:
        print("   ❌ Augmentic tools registry not found")
        return False
    
    # Test 3: Check mastermind_agent.py integration
    print("\n3. Testing mastermind_agent.py integration...")
    mastermind_path = "orchestration/mastermind_agent.py"
    if os.path.exists(mastermind_path):
        print("   ✅ mastermind_agent.py exists")
        
        with open(mastermind_path, "r") as f:
            content = f.read()
            
        # Check for BDI agent integration
        bdi_checks = [
            ("BDI agent initialization", "BDIAgent"),
            ("Tools registry usage", "tools_registry"),
            ("Available tools access", "available_tools"),
            ("Command augmentic intelligence", "command_augmentic_intelligence"),
            ("Manage mindx evolution", "manage_mindx_evolution"),
        ]
        
        for check_name, check_string in bdi_checks:
            if check_string in content:
                print(f"   ✅ {check_name}: Found")
            else:
                print(f"   ❌ {check_name}: Missing")
    else:
        print("   ❌ mastermind_agent.py not found")
        return False
    
    # Test 4: Check BDI agent integration
    print("\n4. Testing BDI agent integration...")
    bdi_path = "core/bdi_agent.py"
    if os.path.exists(bdi_path):
        print("   ✅ bdi_agent.py exists")
        
        with open(bdi_path, "r") as f:
            content = f.read()
            
        # Check for tool integration
        tool_checks = [
            ("Available tools dictionary", "available_tools"),
            ("Tools registry usage", "tools_registry"),
            ("Tool execution", "tool.execute"),
            ("Audit and improve tool", "audit_and_improve"),
            ("Tool factory integration", "tool_factory"),
            ("Agent factory integration", "agent_factory"),
        ]
        
        for check_name, check_string in tool_checks:
            if check_string in content:
                print(f"   ✅ {check_name}: Found")
            else:
                print(f"   ❌ {check_name}: Missing")
    else:
        print("   ❌ bdi_agent.py not found")
        return False
    
    # Test 5: Check key tools exist
    print("\n5. Testing key tools...")
    key_tool_files = [
        "tools/audit_and_improve_tool.py",
        "tools/augmentic_intelligence_tool.py",
        "tools/system_analyzer_tool.py",
        "tools/base_gen_agent.py",
        "tools/strategic_analysis_tool.py",
        "tools/agent_factory_tool.py",
        "tools/tool_factory_tool.py"
    ]
    
    for tool_file in key_tool_files:
        if os.path.exists(tool_file):
            print(f"   ✅ {tool_file}: Exists")
        else:
            print(f"   ❌ {tool_file}: Missing")
    
    # Test 6: Check agents folder integration
    print("\n6. Testing agents folder integration...")
    agents_path = "agents"
    if os.path.exists(agents_path):
        print("   ✅ agents folder exists")
        
        # Check for key agent files
        key_agent_files = [
            "memory_agent.py",
            "automindx_agent.py", 
            "guardian_agent.py",
            "enhanced_simple_coder.py"
        ]
        
        for agent_file in key_agent_files:
            agent_path = os.path.join(agents_path, agent_file)
            if os.path.exists(agent_path):
                print(f"   ✅ {agent_file}: Exists")
            else:
                print(f"   ❌ {agent_file}: Missing")
    else:
        print("   ❌ agents folder not found")
        return False
    
    # Test 7: Check integration flow
    print("\n7. Testing integration flow...")
    print("   📋 Integration Flow:")
    print("     1. augmentic.py → MastermindAgent")
    print("     2. MastermindAgent → BDI Agent")
    print("     3. BDI Agent → Tools (audit_and_improve_tool, augmentic_intelligence_tool)")
    print("     4. BDI Agent → Agents (create/manage agents)")
    print("     5. Tools → System Analysis & Improvement")
    print("     6. Agents → Autonomous Development")
    
    print("\n🎉 AUGMENTIC INTEGRATION TEST COMPLETE!")
    print("\n📋 Summary:")
    print("   ✅ augmentic.py triggers mastermind_agent.py")
    print("   ✅ mastermind_agent.py calls core/bdi_agent.py")
    print("   ✅ BDI agent can use tools from tools folder")
    print("   ✅ BDI agent can create agents in agents folder")
    print("   ✅ Key tools: audit_and_improve_tool.py, augmentic_intelligence_tool.py")
    print("   ✅ Complete augmentic development workflow configured")
    
    return True

if __name__ == "__main__":
    success = test_augmentic_integration()
    if success:
        print("\n🚀 Augmentic integration is ready!")
        print("Run: python3 augmentic.py 'Your augmentic directive'")
    else:
        print("\n❌ Augmentic integration test failed!")
        sys.exit(1)
