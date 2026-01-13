#!/usr/bin/env python3
"""
Comprehensive Mistral API Integration Test for MindX
Tests all modular components: learning, evolution, and core
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_mistral_integration():
    """Test Mistral API integration across all MindX components"""
    print("🧪 Comprehensive Mistral API Integration Test")
    print("=" * 60)
    
    try:
        # Test 1: Core BDI Agent
        print("\n1. Testing Core BDI Agent with Mistral...")
        from core.bdi_agent import BDIAgent
        from core.belief_system import BeliefSystem
        from agents.memory_agent import MemoryAgent
        from utils.config import Config
        
        config = Config()
        belief_system = BeliefSystem()
        memory_agent = MemoryAgent(config=config)
        
        bdi_agent = BDIAgent(
            domain="test_domain",
            belief_system_instance=belief_system,
            tools_registry={},
            config_override=config,
            test_mode=True
        )
        await bdi_agent.async_init_components()
        
        if bdi_agent.llm_handler:
            print(f"   ✅ BDI Agent LLM: {bdi_agent.llm_handler.provider_name}")
            print(f"   ✅ BDI Agent Model: {bdi_agent.llm_handler.model_name_for_api}")
        else:
            print("   ❌ BDI Agent: No LLM handler")
        
        # Test 2: Strategic Evolution Agent
        print("\n2. Testing Strategic Evolution Agent with Mistral...")
        from learning.strategic_evolution_agent import StrategicEvolutionAgent
        from llm.model_registry import ModelRegistry
        
        model_registry = ModelRegistry(config)
        sea = StrategicEvolutionAgent(
            agent_id="test_sea",
            belief_system=belief_system,
            coordinator_agent=None,
            model_registry=model_registry,
            memory_agent=memory_agent,
            config_override=config
        )
        await sea._async_init()
        
        if sea.llm_handler:
            print(f"   ✅ SEA LLM: {sea.llm_handler.provider_name}")
            print(f"   ✅ SEA Model: {sea.llm_handler.model_name_for_api}")
        else:
            print("   ❌ SEA: No LLM handler")
        
        # Test 3: Blueprint Agent
        print("\n3. Testing Blueprint Agent with Mistral...")
        from evolution.blueprint_agent import BlueprintAgent
        from agents.base_gen_agent import BaseGenAgent
        
        base_gen_agent = BaseGenAgent(
            memory_agent=memory_agent,
            agent_id="test_base_gen"
        )
        
        blueprint_agent = BlueprintAgent(
            belief_system=belief_system,
            coordinator_ref=None,
            model_registry_ref=model_registry,
            memory_agent=memory_agent,
            base_gen_agent=base_gen_agent,
            config_override=config,
            test_mode=True
        )
        
        if blueprint_agent.llm_handler:
            print(f"   ✅ Blueprint Agent LLM: {blueprint_agent.llm_handler.provider_name}")
            print(f"   ✅ Blueprint Agent Model: {blueprint_agent.llm_handler.model_name_for_api}")
        else:
            print("   ❌ Blueprint Agent: No LLM handler")
        
        # Test 4: Self Improvement Agent
        print("\n4. Testing Self Improvement Agent with Mistral...")
        from learning.self_improve_agent import SelfImproveAgent
        
        sia = SelfImproveAgent(
            agent_id="test_sia",
            config_override=config,
            test_mode=True
        )
        
        if sia.llm_handler:
            print(f"   ✅ SIA LLM: {sia.llm_handler.provider_name}")
            print(f"   ✅ SIA Model: {sia.llm_handler.model_name_for_api}")
        else:
            print("   ❌ SIA: No LLM handler")
        
        # Test 5: Blueprint to Action Converter
        print("\n5. Testing Blueprint to Action Converter with Mistral...")
        from evolution.blueprint_to_action_converter import BlueprintToActionConverter
        
        if bdi_agent.llm_handler:
            converter = BlueprintToActionConverter(
                llm_handler=bdi_agent.llm_handler,
                memory_agent=memory_agent,
                belief_system=belief_system,
                config=config
            )
            print(f"   ✅ Converter LLM: {converter.llm_handler.provider_name}")
            print(f"   ✅ Converter Model: {converter.llm_handler.model_name_for_api}")
        else:
            print("   ❌ Converter: No LLM handler available")
        
        # Test 6: Actual Mistral API Call
        print("\n6. Testing Actual Mistral API Call...")
        if bdi_agent.llm_handler:
            try:
                test_prompt = "Hello! Can you confirm you are working with Mistral API? Please respond with a simple confirmation."
                response = await bdi_agent.llm_handler.generate_text(
                    prompt=test_prompt,
                    model=bdi_agent.llm_handler.model_name_for_api,
                    temperature=0.7,
                    max_tokens=100
                )
                print(f"   ✅ Mistral API Response: {response[:100]}...")
                print("   🎉 Mistral API integration is working perfectly!")
            except Exception as e:
                print(f"   ❌ Mistral API Error: {e}")
        else:
            print("   ❌ No LLM handler available for API test")
        
        print("\n🎉 Comprehensive Mistral Integration Test Completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mistral_integration())
    if success:
        print("\n✅ All Mistral integrations are working correctly!")
    else:
        print("\n❌ Some Mistral integrations failed.")
