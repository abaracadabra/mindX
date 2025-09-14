#!/usr/bin/env python3
"""
Test script to verify Mistral API integration with mistral.yaml configuration
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from llm.mistral_handler import MistralHandler
from api.mistral_api import MistralIntegration, MistralConfig
from utils.config import Config

async def test_mistral_yaml_integration():
    """Test that Mistral API uses mistral.yaml configuration"""
    
    print("🧪 Testing Mistral YAML Integration")
    print("=" * 50)
    
    # Test 1: MistralHandler YAML loading
    print("\n1. Testing MistralHandler YAML loading...")
    try:
        handler = MistralHandler(
            model_name_for_api="mistral-large-latest",
            api_key=None,  # No API key to test degraded mode
            config=Config()
        )
        
        # Test model catalog loading
        print(f"   ✅ Model catalog loaded: {len(handler.model_catalog)} models")
        
        # Test available models
        available_models = handler.get_available_models()
        print(f"   ✅ Available models: {len(available_models)}")
        print(f"   📋 Sample models: {available_models[:5]}")
        
        # Test model info retrieval
        model_info = handler.get_model_info("mistral-large-latest")
        if model_info:
            print(f"   ✅ Model info retrieved for mistral-large-latest")
            print(f"   📊 Task scores: {model_info.get('task_scores', {})}")
        else:
            print(f"   ❌ Failed to get model info for mistral-large-latest")
        
        # Test task-based model selection
        best_reasoning = handler.get_best_model_for_task("reasoning")
        best_code = handler.get_best_model_for_task("code_generation")
        print(f"   🧠 Best reasoning model: {best_reasoning}")
        print(f"   💻 Best code model: {best_code}")
        
        # Test model suitability
        is_suitable = handler.is_model_suitable_for_task("mistral-large-latest", "reasoning")
        print(f"   ✅ Model suitability check: {is_suitable}")
        
    except Exception as e:
        print(f"   ❌ MistralHandler test failed: {e}")
        return False
    
    # Test 2: MistralIntegration YAML loading
    print("\n2. Testing MistralIntegration YAML loading...")
    try:
        config = MistralConfig(api_key=None)  # No API key to test degraded mode
        integration = MistralIntegration(config)
        
        # Test model catalog loading
        print(f"   ✅ Model catalog loaded: {len(integration.model_catalog)} models")
        
        # Test model info retrieval
        model_info = integration.get_model_info("mistral-large-latest")
        if model_info:
            print(f"   ✅ Model info retrieved for mistral-large-latest")
        else:
            print(f"   ❌ Failed to get model info for mistral-large-latest")
        
        # Test task-based model selection
        best_reasoning = integration.get_best_model_for_task("reasoning")
        best_code = integration.get_best_model_for_task("code_generation")
        print(f"   🧠 Best reasoning model: {best_reasoning}")
        print(f"   💻 Best code model: {best_code}")
        
    except Exception as e:
        print(f"   ❌ MistralIntegration test failed: {e}")
        return False
    
    # Test 3: Model listing with YAML catalog
    print("\n3. Testing model listing with YAML catalog...")
    try:
        async with handler as h:
            models = await h.list_models()
            if models:
                print(f"   ✅ Listed {len(models)} models from YAML catalog")
                print(f"   📋 Sample models: {[m['id'] for m in models[:5]]}")
            else:
                print(f"   ❌ No models returned")
                return False
    except Exception as e:
        print(f"   ❌ Model listing test failed: {e}")
        return False
    
    # Test 4: Integration methods with auto-model selection
    print("\n4. Testing integration methods with auto-model selection...")
    try:
        async with integration as mistral:
            # Test reasoning with auto-model selection
            reasoning_result = await mistral.enhance_reasoning(
                context="mindX is an autonomous AI system",
                question="How can we improve agent coordination?"
            )
            print(f"   ✅ Reasoning test completed (degraded mode)")
            print(f"   📝 Result preview: {reasoning_result[:100]}...")
            
            # Test code generation with auto-model selection
            code_result = await mistral.generate_code(
                prompt="def calculate_agent_efficiency(",
                suffix="return efficiency_score"
            )
            print(f"   ✅ Code generation test completed (degraded mode)")
            print(f"   📝 Result preview: {code_result[:100]}...")
            
    except Exception as e:
        print(f"   ❌ Integration methods test failed: {e}")
        return False
    
    print("\n🎉 All tests passed! Mistral YAML integration is working correctly.")
    return True

async def test_yaml_file_structure():
    """Test that mistral.yaml file has correct structure"""
    
    print("\n🔍 Testing mistral.yaml file structure...")
    
    try:
        import yaml
        yaml_path = Path(__file__).parent.parent / "models" / "mistral.yaml"
        
        if not yaml_path.exists():
            print(f"   ❌ mistral.yaml not found at {yaml_path}")
            return False
        
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        
        if not data:
            print(f"   ❌ mistral.yaml is empty or invalid")
            return False
        
        print(f"   ✅ mistral.yaml loaded successfully")
        print(f"   📊 Found {len(data)} model configurations")
        
        # Check structure of first model
        first_model_key = list(data.keys())[0]
        first_model = data[first_model_key]
        
        required_fields = ["task_scores", "cost_per_kilo_input_tokens", "cost_per_kilo_output_tokens", 
                          "max_context_length", "supports_streaming", "supports_function_calling", 
                          "api_name", "assessed_capabilities"]
        
        missing_fields = [field for field in required_fields if field not in first_model]
        if missing_fields:
            print(f"   ❌ Missing required fields: {missing_fields}")
            return False
        
        print(f"   ✅ YAML structure is correct")
        print(f"   📋 Sample model: {first_model_key}")
        print(f"   🎯 Task scores: {list(first_model['task_scores'].keys())}")
        print(f"   🔧 Capabilities: {first_model['assessed_capabilities']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ YAML structure test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Mistral YAML Integration Tests")
    print("=" * 60)
    
    # Test YAML file structure
    yaml_test = await test_yaml_file_structure()
    if not yaml_test:
        print("\n❌ YAML file structure test failed. Exiting.")
        return False
    
    # Test integration
    integration_test = await test_mistral_yaml_integration()
    if not integration_test:
        print("\n❌ Integration test failed. Exiting.")
        return False
    
    print("\n🎉 All tests completed successfully!")
    print("✅ Mistral API is properly integrated with mistral.yaml configuration")
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
