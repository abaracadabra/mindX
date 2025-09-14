#!/usr/bin/env python3
"""
Test script to verify Mistral API integration in the deployed MindX environment
"""

import sys
import os
import asyncio

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_mistral_integration():
    """Test Mistral API integration"""
    print("🧪 Testing Mistral API Integration in Deployed Environment")
    print("=" * 60)
    
    try:
        # Import our Mistral API client
        from api.mistral_api import MistralAPIClient, ChatCompletionRequest, ChatMessage, MistralConfig
        
        # Test with the configured API key
        config = MistralConfig(api_key='ZHgH4FsGsk0k6jhY4V1jryZOG71EzcIN')
        client = MistralAPIClient(config)
        
        # Create a test request
        request = ChatCompletionRequest(
            model='mistral-small-latest',
            messages=[ChatMessage(role='user', content='Hello! Can you confirm you are working?')],
            temperature=0.7,
            max_tokens=50
        )
        
        print("📡 Making API request to Mistral...")
        response = await client.chat_completion(request)
        print("✅ API Response received!")
        print(f"📝 Response: {response}")
        
        if 'choices' in response and len(response['choices']) > 0:
            content = response['choices'][0]['message']['content']
            print(f"💬 Generated text: {content}")
            print("🎉 Mistral API integration is working perfectly!")
            return True
        else:
            print("⚠️  Unexpected response format")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("🔧 This might be expected if the API key has usage limits")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mistral_integration())
    if success:
        print("\n✅ Mistral integration test completed successfully!")
    else:
        print("\n❌ Mistral integration test failed.")
