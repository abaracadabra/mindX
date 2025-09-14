#!/usr/bin/env python3
"""
Simple Mistral API Integration Test for MindX
Tests core Mistral functionality without complex dependencies
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_mistral_simple():
    """Test basic Mistral API integration"""
    print("🧪 Simple Mistral API Integration Test")
    print("=" * 50)
    
    try:
        # Test 1: Direct Mistral API
        print("\n1. Testing Direct Mistral API...")
        from api.mistral_api import MistralAPIClient, MistralConfig
        from utils.config import Config
        
        config = Config()
        mistral_config = MistralConfig(api_key=config.get("mistral.api_key"))
        
        # Test basic chat completion
        from api.mistral_api import ChatCompletionRequest, ChatMessage
        
        test_messages = [
            ChatMessage(role="user", content="Hello! Can you confirm you are working with Mistral API? Please respond with a simple confirmation.")
        ]
        
        request = ChatCompletionRequest(
            model="mistral-small-latest",
            messages=test_messages,
            temperature=0.7,
            max_tokens=100
        )
        
        async with MistralAPIClient(mistral_config) as mistral_api:
            response = await mistral_api.chat_completion(request)
        
        if response and 'choices' in response:
            content = response['choices'][0]['message']['content']
            print(f"   ✅ Mistral API Response: {content}")
            print("   🎉 Direct Mistral API is working!")
        else:
            print(f"   ❌ Unexpected response format: {response}")
        
        # Test 2: Mistral Handler
        print("\n2. Testing Mistral Handler...")
        from llm.mistral_handler import MistralHandler
        
        mistral_handler = MistralHandler(
            model_name="mistral-small-latest",
            api_key=config.get("mistral.api_key")
        )
        
        test_prompt = "What is 2+2? Please respond with just the number."
        response_text = await mistral_handler.generate_text(
            prompt=test_prompt,
            temperature=0.1,
            max_tokens=10
        )
        
        if response_text:
            print(f"   ✅ Mistral Handler Response: {response_text}")
            print("   🎉 Mistral Handler is working!")
        else:
            print("   ❌ Mistral Handler returned empty response")
        
        # Test 3: LLM Factory with Mistral
        print("\n3. Testing LLM Factory with Mistral...")
        from llm.llm_factory import create_llm_handler
        
        llm_handler = await create_llm_handler(
            provider_name="mistral",
            model_name="mistral-small-latest"
        )
        
        if llm_handler:
            print(f"   ✅ LLM Factory Provider: {llm_handler.provider_name}")
            print(f"   ✅ LLM Factory Model: {llm_handler.model_name_for_api}")
            
            # Test actual generation
            factory_response = await llm_handler.generate_text(
                prompt="Say 'Mistral Factory Test Success'",
                temperature=0.1,
                max_tokens=20
            )
            print(f"   ✅ Factory Response: {factory_response}")
            print("   🎉 LLM Factory with Mistral is working!")
        else:
            print("   ❌ LLM Factory failed to create Mistral handler")
        
        print("\n🎉 Simple Mistral Integration Test Completed Successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mistral_simple())
    if success:
        print("\n✅ Mistral integration is working correctly!")
    else:
        print("\n❌ Mistral integration failed.")
