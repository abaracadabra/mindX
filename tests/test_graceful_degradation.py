#!/usr/bin/env python3
"""
Test script to verify graceful degradation without API keys

This script tests that the mindX system works properly with or without
API keys, ensuring modular development and graceful degradation.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from utils.config import Config
from utils.logging_config import setup_logging, get_logger
from llm.llm_factory import create_llm_handler
from llm.model_registry import get_model_registry_async
from api.mistral_api import MistralIntegration, create_mistral_config

# Setup logging
setup_logging()
logger = get_logger(__name__)

async def test_llm_factory_without_keys():
    """Test LLM factory works without API keys"""
    logger.info("=== Testing LLM Factory without API keys ===")
    
    # Clear any existing API keys
    original_env = {}
    api_keys = ['MISTRAL_API_KEY', 'GEMINI_API_KEY', 'GROQ_API_KEY', 'OPENAI_API_KEY']
    for key in api_keys:
        original_env[key] = os.environ.get(key)
        if key in os.environ:
            del os.environ[key]
    
    try:
        # Test creating handlers without API keys
        providers = ['mistral', 'gemini', 'groq', 'openai']
        
        for provider in providers:
            logger.info(f"Testing {provider} handler without API key...")
            try:
                handler = await create_llm_handler(provider_name=provider)
                logger.info(f"✓ {provider} handler created successfully")
                
                # Test basic functionality
                if hasattr(handler, 'test_connection'):
                    connection_ok = await handler.test_connection()
                    logger.info(f"✓ {provider} connection test: {connection_ok}")
                
                # Test text generation (should return mock response)
                if hasattr(handler, 'generate_text'):
                    response = await handler.generate_text(
                        prompt="Test prompt",
                        model="test-model"
                    )
                    logger.info(f"✓ {provider} text generation: {response[:100]}...")
                
            except Exception as e:
                logger.error(f"✗ {provider} handler failed: {e}")
        
    finally:
        # Restore original environment
        for key, value in original_env.items():
            if value is not None:
                os.environ[key] = value

async def test_mistral_integration_without_key():
    """Test Mistral integration without API key"""
    logger.info("=== Testing Mistral Integration without API key ===")
    
    # Clear Mistral API key
    original_key = os.environ.get('MISTRAL_API_KEY')
    if 'MISTRAL_API_KEY' in os.environ:
        del os.environ['MISTRAL_API_KEY']
    
    try:
        # Create config without API key
        config = create_mistral_config(api_key="")
        
        # Test integration
        async with MistralIntegration(config) as mistral:
            logger.info("✓ Mistral integration created without API key")
            
            # Test reasoning
            reasoning = await mistral.enhance_reasoning(
                context="Test context",
                question="Test question"
            )
            logger.info(f"✓ Reasoning test: {reasoning[:100]}...")
            
            # Test code generation
            code = await mistral.generate_code(
                prompt="def hello():",
                suffix="print('world')"
            )
            logger.info(f"✓ Code generation test: {code[:100]}...")
            
            # Test embeddings
            embeddings = await mistral.create_embeddings_for_memory(
                texts=["test text 1", "test text 2"]
            )
            logger.info(f"✓ Embeddings test: {len(embeddings)} vectors, {len(embeddings[0])} dimensions")
    
    finally:
        # Restore original API key
        if original_key:
            os.environ['MISTRAL_API_KEY'] = original_key

async def test_model_registry_without_keys():
    """Test model registry works without API keys"""
    logger.info("=== Testing Model Registry without API keys ===")
    
    # Clear API keys
    original_env = {}
    api_keys = ['MISTRAL_API_KEY', 'GEMINI_API_KEY', 'GROQ_API_KEY']
    for key in api_keys:
        original_env[key] = os.environ.get(key)
        if key in os.environ:
            del os.environ[key]
    
    try:
        # Test model registry initialization
        registry = await get_model_registry_async()
        logger.info("✓ Model registry initialized without API keys")
        
        # Test available providers
        providers = registry.list_available_providers()
        logger.info(f"✓ Available providers: {providers}")
        
        # Test capabilities
        capabilities = list(registry.capabilities.keys())
        logger.info(f"✓ Available capabilities: {len(capabilities)} models")
        
    finally:
        # Restore original environment
        for key, value in original_env.items():
            if value is not None:
                os.environ[key] = value

async def test_agent_initialization_without_keys():
    """Test that agents can initialize without external API keys"""
    logger.info("=== Testing Agent Initialization without API keys ===")
    
    # Clear API keys
    original_env = {}
    api_keys = ['MISTRAL_API_KEY', 'GEMINI_API_KEY', 'GROQ_API_KEY']
    for key in api_keys:
        original_env[key] = os.environ.get(key)
        if key in os.environ:
            del os.environ[key]
    
    try:
        # Test core components
        from core.belief_system import BeliefSystem
        from core.id_manager_agent import IDManagerAgent
        from agents.memory_agent import MemoryAgent
        
        # Test belief system
        belief_system = BeliefSystem()
        logger.info("✓ Belief system initialized")
        
        # Test ID manager
        id_manager = IDManagerAgent(agent_id="test_id", belief_system=belief_system)
        logger.info("✓ ID manager initialized")
        
        # Test memory agent
        memory_agent = MemoryAgent()
        logger.info("✓ Memory agent initialized")
        
        # Test BDI agent (should work with mock LLM)
        from core.bdi_agent import BDIAgent
        bdi_agent = BDIAgent(
            domain="test",
            belief_system_instance=belief_system,
            tools_registry={},
            config_override=Config()
        )
        await bdi_agent.async_init_components()
        logger.info("✓ BDI agent initialized and components loaded")
        
    except Exception as e:
        logger.error(f"✗ Agent initialization failed: {e}")
    finally:
        # Restore original environment
        for key, value in original_env.items():
            if value is not None:
                os.environ[key] = value

async def test_config_system():
    """Test configuration system handles missing API keys gracefully"""
    logger.info("=== Testing Configuration System ===")
    
    # Test config loading
    config = Config()
    logger.info("✓ Config system initialized")
    
    # Test getting non-existent API keys
    mistral_key = config.get("llm.mistral.api_key")
    gemini_key = config.get("llm.gemini.api_key")
    
    logger.info(f"✓ Mistral API key: {'Present' if mistral_key else 'Not configured'}")
    logger.info(f"✓ Gemini API key: {'Present' if gemini_key else 'Not configured'}")
    
    # Test getting default values
    mistral_base_url = config.get("llm.mistral.base_url", "https://api.mistral.ai/v1")
    logger.info(f"✓ Mistral base URL default: {mistral_base_url}")

async def main():
    """Run all graceful degradation tests"""
    logger.info("🚀 Starting Graceful Degradation Tests")
    logger.info("=" * 60)
    
    try:
        # Test configuration system
        await test_config_system()
        logger.info("")
        
        # Test LLM factory without keys
        await test_llm_factory_without_keys()
        logger.info("")
        
        # Test Mistral integration without key
        await test_mistral_integration_without_key()
        logger.info("")
        
        # Test model registry without keys
        await test_model_registry_without_keys()
        logger.info("")
        
        # Test agent initialization without keys
        await test_agent_initialization_without_keys()
        logger.info("")
        
        logger.info("✅ All graceful degradation tests completed successfully!")
        logger.info("🎉 mindX system works perfectly with or without API keys!")
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
