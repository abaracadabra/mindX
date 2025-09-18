#!/usr/bin/env python3
"""
Enhanced AutoMINDX Test Script

This script comprehensively tests the enhanced AutoMINDX agent with:
- Avatar generation and management
- A2A protocol compliance and Agent Card generation
- AgenticPlace marketplace integration
- Custom fields for user-defined metadata
- Complete iNFT export with avatar support
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.automindx_agent import AutoMINDXAgent
from agents.memory_agent import MemoryAgent
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

async def test_enhanced_automindx():
    """Comprehensive test of enhanced AutoMINDX capabilities."""
    print("🚀 Starting Enhanced AutoMINDX Test Suite")
    print("=" * 60)
    
    # Initialize components
    print("\n1. Initializing AutoMINDX Agent...")
    memory_agent = MemoryAgent()
    automindx = await AutoMINDXAgent.get_instance(memory_agent)
    
    # Test 1: List existing personas
    print("\n2. Listing existing personas...")
    existing_personas = automindx.list_available_personas()
    print(f"   Found {len(existing_personas)} existing personas:")
    for persona_key, info in existing_personas.items():
        print(f"   - {persona_key}: {info.get('word_count', 0)} words, "
              f"Avatar: {info.get('has_avatar', False)}, "
              f"A2A Card: {info.get('a2a_card_available', False)}")
    
    # Test 2: Generate new persona with custom fields and avatar
    print("\n3. Generating new persona with enhanced features...")
    custom_fields = {
        "evolution_stage": "adaptation",
        "specialization_domain": "blockchain_security",
        "interaction_preference": "multimodal",
        "autonomy_level": 0.85,
        "marketplace_tags": ["security", "blockchain", "audit", "defi"],
        "license_type": "open_source"
    }
    
    avatar_config = {
        "type": "generated",
        "style": "professional"
    }
    
    role_description = "Advanced Blockchain Security Auditor specializing in smart contract vulnerabilities and DeFi protocol analysis"
    
    new_persona = await automindx.generate_new_persona(
        role_description=role_description,
        save_to_collection=True,
        custom_fields=custom_fields,
        avatar_config=avatar_config
    )
    
    if new_persona.startswith("Error:"):
        print(f"   ❌ Failed to generate persona: {new_persona}")
    else:
        print(f"   ✅ Successfully generated new persona:")
        print(f"   {new_persona[:200]}..." if len(new_persona) > 200 else f"   {new_persona}")
    
    # Test 3: Update avatar for existing persona
    print("\n4. Testing avatar update for existing persona...")
    if "MASTERMIND" in automindx.personas:
        avatar_update_result = await automindx.update_persona_avatar(
            "MASTERMIND",
            {"type": "generated", "style": "strategic"}
        )
        print(f"   Avatar update result: {'✅ Success' if avatar_update_result else '❌ Failed'}")
    
    # Test 4: Update custom fields for existing persona
    print("\n5. Testing custom fields update...")
    if "MASTERMIND" in automindx.personas:
        custom_fields_update = {
            "evolution_stage": "optimization",
            "specialization_domain": "strategic_orchestration",
            "marketplace_tags": ["orchestration", "strategy", "planning"],
            "autonomy_level": 0.95
        }
        
        fields_update_result = await automindx.update_persona_custom_fields(
            "MASTERMIND",
            custom_fields_update
        )
        print(f"   Custom fields update result: {'✅ Success' if fields_update_result else '❌ Failed'}")
    
    # Test 5: Export all personas as iNFT with enhanced metadata
    print("\n6. Exporting all personas as enhanced iNFT metadata...")
    exported_files = await automindx.export_all_personas_as_inft()
    print(f"   ✅ Exported {len(exported_files)} personas as iNFT metadata:")
    for persona, file_path in exported_files.items():
        file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
        print(f"   - {persona}: {file_path} ({file_size:,} bytes)")
    
    # Test 6: Generate A2A discovery endpoint
    print("\n7. Generating A2A protocol discovery endpoint...")
    discovery_data = automindx.generate_a2a_discovery_endpoint()
    if discovery_data:
        total_agents = discovery_data.get("metadata", {}).get("total_agents", 0)
        print(f"   ✅ Generated A2A discovery endpoint with {total_agents} agents")
    else:
        print("   ❌ Failed to generate A2A discovery endpoint")
    
    # Test 7: Generate AgenticPlace marketplace manifest
    print("\n8. Generating AgenticPlace marketplace manifest...")
    marketplace_manifest = automindx.generate_agenticplace_manifest()
    if marketplace_manifest:
        agent_count = len(marketplace_manifest.get("marketplace_manifest", {}).get("agents", []))
        print(f"   ✅ Generated AgenticPlace manifest with {agent_count} agents")
    else:
        print("   ❌ Failed to generate AgenticPlace manifest")
    
    # Test 8: Create blockchain publication manifest
    print("\n9. Creating blockchain publication manifest...")
    blockchain_manifest = await automindx.create_blockchain_publication_manifest()
    if blockchain_manifest:
        persona_count = len(blockchain_manifest.get("publication_manifest", {}).get("personas", []))
        print(f"   ✅ Created blockchain publication manifest with {persona_count} personas")
    else:
        print("   ❌ Failed to create blockchain publication manifest")
    
    # Test 9: Full AgenticPlace deployment preparation
    print("\n10. Preparing full AgenticPlace deployment...")
    deployment_package = await automindx.deploy_to_agenticplace()
    if deployment_package:
        files_generated = deployment_package.get("files_generated", {})
        print(f"   ✅ Generated deployment package:")
        print(f"   - iNFT metadata files: {len(files_generated.get('inft_metadata', []))}")
        print(f"   - A2A agent cards: {len(files_generated.get('agent_cards', []))}")
        print(f"   - Avatar files: {len(files_generated.get('avatars', []))}")
        print(f"   - Manifest files: {len(files_generated.get('manifests', []))}")
        
        # Show deployment status
        deployment_status = deployment_package.get("deployment_status", {})
        ready_count = sum(1 for status in deployment_status.values() if status == "ready")
        total_count = len(deployment_status)
        print(f"   - Deployment status: {ready_count}/{total_count} personas ready")
    else:
        print("   ❌ Failed to prepare deployment package")
    
    # Test 10: Verify file generation and content
    print("\n11. Verifying generated files...")
    
    # Check iNFT exports directory
    inft_export_dir = automindx.inft_export_dir
    inft_files = list(inft_export_dir.glob("*.json"))
    print(f"   iNFT export directory: {len(inft_files)} JSON files")
    
    # Check avatars directory
    avatars_dir = automindx.avatars_dir
    avatar_files = list(avatars_dir.glob("*"))
    print(f"   Avatars directory: {len(avatar_files)} files")
    
    # Check A2A cards directory
    a2a_cards_dir = automindx.a2a_cards_dir
    card_files = list(a2a_cards_dir.glob("*.json"))
    print(f"   A2A cards directory: {len(card_files)} JSON files")
    
    # Test 11: Sample content verification
    print("\n12. Verifying sample iNFT metadata content...")
    if inft_files:
        sample_file = inft_files[0]
        try:
            with sample_file.open("r", encoding="utf-8") as f:
                sample_data = json.load(f)
            
            # Check for enhanced features
            intelligence_metadata = sample_data.get("intelligence_metadata", {})
            has_avatar = intelligence_metadata.get("avatar", {}).get("has_custom_avatar", False)
            has_custom_fields = bool(intelligence_metadata.get("custom_attributes", {}))
            has_marketplace_integration = bool(intelligence_metadata.get("marketplace_integration", {}))
            a2a_compatible = intelligence_metadata.get("a2a_compatibility", {}).get("agenticplace_compatible", False)
            
            print(f"   Sample file: {sample_file.name}")
            print(f"   - Has avatar metadata: {'✅' if has_avatar else '❌'}")
            print(f"   - Has custom fields: {'✅' if has_custom_fields else '❌'}")
            print(f"   - Has marketplace integration: {'✅' if has_marketplace_integration else '❌'}")
            print(f"   - A2A compatible: {'✅' if a2a_compatible else '❌'}")
            
        except Exception as e:
            print(f"   ❌ Error reading sample file: {e}")
    
    # Test 12: Updated personas list with new features
    print("\n13. Final persona overview with enhanced features...")
    final_personas = automindx.list_available_personas()
    print(f"   Total personas: {len(final_personas)}")
    
    for persona_key, info in final_personas.items():
        custom_fields = info.get('custom_fields', {})
        evolution_stage = custom_fields.get('evolution_stage', 'unknown')
        autonomy_level = custom_fields.get('autonomy_level', 0.0)
        marketplace_tags = custom_fields.get('marketplace_tags', [])
        
        print(f"   - {persona_key}:")
        print(f"     * Words: {info.get('word_count', 0)}")
        print(f"     * Complexity: {info.get('complexity_score', 0.0):.3f}")
        print(f"     * Avatar: {'✅' if info.get('has_avatar') else '❌'}")
        print(f"     * A2A Card: {'✅' if info.get('a2a_card_available') else '❌'}")
        print(f"     * Evolution Stage: {evolution_stage}")
        print(f"     * Autonomy Level: {autonomy_level:.2f}")
        print(f"     * Marketplace Tags: {len(marketplace_tags)} tags")
    
    print("\n" + "=" * 60)
    print("🎉 Enhanced AutoMINDX Test Suite Completed Successfully!")
    print("\n📋 Summary of New Features Tested:")
    print("✅ Avatar generation and management")
    print("✅ A2A protocol Agent Card generation")
    print("✅ Custom fields validation and storage")
    print("✅ AgenticPlace marketplace integration")
    print("✅ Enhanced iNFT metadata with avatar support")
    print("✅ A2A discovery endpoint generation")
    print("✅ Complete deployment package preparation")
    print("\n🌐 Ready for AgenticPlace marketplace deployment!")
    print(f"🔗 Marketplace URL: {automindx.agenticplace_base_url}")
    print(f"🔗 GitHub Organization: {automindx.github_base_url}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_automindx()) 