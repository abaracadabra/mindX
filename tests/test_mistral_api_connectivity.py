#!/usr/bin/env python3
"""
Mistral API Connectivity Test
Verifies that MindX can connect to and use the Mistral API
"""

import asyncio
import json
import time
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_mistral_api_connectivity():
    """Test Mistral API connectivity and functionality"""
    print("🔍 Testing Mistral API Connectivity")
    print("=" * 40)
    
    try:
        # Import Mistral handler
        from llm.mistral_handler import MistralHandler
        from utils.config import Config
        
        # Load configuration
        config = Config()
        
        # Check if API key is configured
        api_key = os.getenv('MISTRAL_API_KEY') or config.get('MISTRAL_API_KEY')
        if not api_key or api_key == "YOUR_MISTRAL_API_KEY_HERE":
            print("❌ FAIL: Mistral API key not configured")
            return False
        
        print(f"✅ API Key found: {api_key[:8]}...")
        
        # Initialize Mistral handler
        handler = MistralHandler()
        print("✅ Mistral handler initialized")
        
        # Test basic text generation
        print("🧪 Testing text generation...")
        try:
            response = await handler.generate_text(
                prompt="Hello, this is a test message. Please respond with 'API connection successful'.",
                model="mistral-small-latest",
                max_tokens=50
            )
            
            if response and len(response) > 0:
                print(f"✅ Text generation successful: {response[:100]}...")
                return True
            else:
                print("❌ FAIL: Empty response from Mistral API")
                return False
                
        except Exception as e:
            print(f"❌ FAIL: Text generation failed - {str(e)}")
            return False
            
    except ImportError as e:
        print(f"❌ FAIL: Could not import Mistral handler - {str(e)}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error - {str(e)}")
        return False

async def test_mistral_chat_completion():
    """Test Mistral chat completion functionality"""
    print("\n💬 Testing Mistral Chat Completion")
    print("=" * 40)
    
    try:
        from llm.mistral_handler import MistralHandler
        
        handler = MistralHandler()
        
        # Test chat completion using generate_text
        response = await handler.generate_text(
            prompt="What is 2+2? Please respond with just the number.",
            model="mistral-small-latest",
            max_tokens=10
        )
        
        if response and "4" in str(response):
            print(f"✅ Chat completion successful: {response}")
            return True
        else:
            print(f"❌ FAIL: Unexpected chat response: {response}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Chat completion failed - {str(e)}")
        return False

async def test_mistral_embeddings():
    """Test Mistral embeddings functionality"""
    print("\n🔢 Testing Mistral Embeddings")
    print("=" * 40)
    
    try:
        from llm.mistral_handler import MistralHandler
        
        handler = MistralHandler()
        
        # Test embeddings
        text = "This is a test sentence for embedding generation."
        embeddings = await handler.create_embeddings(text)
        
        if embeddings and len(embeddings) > 0:
            print(f"✅ Embeddings generated successfully: {len(embeddings)} dimensions")
            return True
        else:
            print("❌ FAIL: No embeddings generated")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Embeddings generation failed - {str(e)}")
        return False

async def test_mistral_in_mindx_system():
    """Test Mistral integration within MindX system"""
    print("\n🧠 Testing Mistral in MindX System")
    print("=" * 40)
    
    try:
        from llm.model_registry import get_model_registry_async
        from llm.llm_factory import create_llm_handler
        
        # Get model registry
        model_registry = await get_model_registry_async()
        
        # Try to get Mistral handler from factory
        handler = await create_llm_handler("mistral", "default_model_for_mistral")
        
        if handler and hasattr(handler, 'generate_text'):
            print("✅ Mistral handler created through MindX factory")
            
            # Test a simple generation
            response = await handler.generate_text("Test message", model="mistral-small-latest", max_tokens=20)
            if response:
                print(f"✅ MindX-Mistral integration working: {response[:50]}...")
                return True
            else:
                print("❌ FAIL: Empty response from MindX-Mistral integration")
                return False
        else:
            print("❌ FAIL: Could not create Mistral handler through MindX factory")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: MindX-Mistral integration failed - {str(e)}")
        return False

async def main():
    """Run all Mistral API tests"""
    print("🚀 Starting Mistral API Connectivity Tests")
    print("=" * 50)
    
    tests = [
        test_mistral_api_connectivity,
        test_mistral_chat_completion,
        test_mistral_embeddings,
        test_mistral_in_mindx_system
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ FAIL: Test {test.__name__} crashed - {str(e)}")
    
    print("\n" + "=" * 50)
    print("📊 MISTRAL API TEST SUMMARY")
    print("=" * 50)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All Mistral API tests passed!")
        return True
    else:
        print(f"⚠️  {total-passed} Mistral API tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
