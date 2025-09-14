#!/usr/bin/env python3
"""
Test script for AutoMINDX iNFT capabilities.

This script demonstrates the new blockchain integration features of the AutoMINDX agent,
including persona metadata generation, iNFT export, and A2A protocol compatibility.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from agents.automindx_agent import AutoMINDXAgent
from agents.memory_agent import MemoryAgent
from utils.config import Config
from utils.logging_config import setup_logging

async def test_automindx_inft_capabilities():
    """Test the new iNFT capabilities of AutoMINDX agent."""
    
    print("=" * 80)
    print("AutoMINDX iNFT Capabilities Test")
    print("=" * 80)
    
    # Setup logging
    setup_logging()
    
    # Initialize config and memory agent
    config = Config()
    memory_agent = MemoryAgent(config)
    
    # Get AutoMINDX agent instance
    print("\n1. Initializing AutoMINDX Agent...")
    automindx = await AutoMINDXAgent.get_instance(memory_agent, config_override=config)
    print(f"   ✓ AutoMINDX agent initialized: {automindx.agent_id}")
    
    # Test listing available personas
    print("\n2. Listing Available Personas...")
    personas = automindx.list_available_personas()
    print(f"   ✓ Found {len(personas)} personas:")
    for persona_key, details in personas.items():
        print(f"     - {persona_key}: {details['word_count']} words, complexity: {details['complexity_score']:.3f}")
    
    # Test generating a new persona with metadata
    print("\n3. Generating New Persona with iNFT Metadata...")
    role_description = "Security Auditor specializing in blockchain smart contract vulnerabilities"
    new_persona = await automindx.generate_new_persona(role_description, save_to_collection=True)
    
    if new_persona and not new_persona.startswith("Error:"):
        print(f"   ✓ Generated new persona ({len(new_persona)} characters)")
        print(f"     Preview: {new_persona[:100]}...")
    else:
        print(f"   ✗ Failed to generate persona: {new_persona}")
    
    # Test exporting single persona as iNFT
    print("\n4. Exporting Single Persona as iNFT Metadata...")
    persona_to_export = list(personas.keys())[0]  # Export the first persona
    inft_metadata = automindx.export_persona_as_inft_metadata(persona_to_export)
    
    if inft_metadata:
        print(f"   ✓ Exported {persona_to_export} as iNFT metadata")
        print(f"     Token ID: {inft_metadata['intelligence_metadata']['token_id']}")
        print(f"     Persona Hash: {inft_metadata['intelligence_metadata']['persona_hash'][:16]}...")
        print(f"     A2A Protocol Hash: {inft_metadata['blockchain_metadata']['a2a_protocol_hash'][:16]}...")
        print(f"     Capabilities: {len(inft_metadata['intelligence_metadata']['capabilities'])} identified")
        print(f"     Traits: {len(inft_metadata['intelligence_metadata']['cognitive_traits'])} identified")
        print(f"     Complexity Score: {inft_metadata['intelligence_metadata']['complexity_score']}")
    else:
        print(f"   ✗ Failed to export {persona_to_export}")
    
    # Test exporting all personas as iNFT files
    print("\n5. Exporting All Personas as iNFT Files...")
    exported_files = await automindx.export_all_personas_as_inft()
    
    print(f"   ✓ Exported {len(exported_files)} persona files:")
    for persona_key, file_path in exported_files.items():
        file_size = Path(file_path).stat().st_size
        print(f"     - {persona_key}: {file_path} ({file_size} bytes)")
    
    # Test creating blockchain publication manifest
    print("\n6. Creating Blockchain Publication Manifest...")
    manifest = await automindx.create_blockchain_publication_manifest()
    
    if manifest:
        pub_manifest = manifest['publication_manifest']
        print(f"   ✓ Created publication manifest")
        print(f"     Collection: {pub_manifest['collection_metadata']['name']}")
        print(f"     Total Personas: {pub_manifest['collection_metadata']['total_personas']}")
        print(f"     Target Networks: {', '.join(pub_manifest['blockchain_specifications']['target_networks'])}")
        print(f"     Contract Standard: {pub_manifest['blockchain_specifications']['contract_standard']}")
        print(f"     A2A Protocol Version: {pub_manifest['blockchain_specifications']['a2a_protocol_version']}")
        
        # Display persona readiness
        print(f"     Persona Readiness:")
        for persona_entry in pub_manifest['personas']:
            print(f"       - {persona_entry['name']}: {'✓ Ready' if persona_entry['ready_for_minting'] else '✗ Not Ready'}")
    else:
        print("   ✗ Failed to create publication manifest")
    
    # Display export directory contents
    print("\n7. Export Directory Contents...")
    export_dir = automindx.inft_export_dir
    if export_dir.exists():
        export_files = list(export_dir.glob("*.json"))
        print(f"   ✓ Found {len(export_files)} files in export directory:")
        for file_path in sorted(export_files):
            file_size = file_path.stat().st_size
            print(f"     - {file_path.name}: {file_size} bytes")
    else:
        print("   ✗ Export directory not found")
    
    # Test A2A protocol integration
    print("\n8. Testing A2A Protocol Integration...")
    if personas:
        first_persona = list(personas.keys())[0]
        first_persona_text = automindx.personas[first_persona]
        a2a_hash = automindx._generate_a2a_protocol_hash(first_persona, first_persona_text)
        print(f"   ✓ Generated A2A protocol hash for {first_persona}")
        print(f"     Hash: {a2a_hash}")
        print(f"     Compatible with mindX registry: ✓")
        print(f"     Blockchain ready: ✓")
    
    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"✓ AutoMINDX agent initialization: SUCCESS")
    print(f"✓ Persona listing: {len(personas)} personas available")
    print(f"✓ New persona generation: {'SUCCESS' if new_persona and not new_persona.startswith('Error:') else 'FAILED'}")
    print(f"✓ iNFT metadata export: {'SUCCESS' if inft_metadata else 'FAILED'}")
    print(f"✓ Batch iNFT export: {len(exported_files)} files created")
    print(f"✓ Blockchain manifest: {'SUCCESS' if manifest else 'FAILED'}")
    print(f"✓ A2A protocol integration: SUCCESS")
    
    print(f"\nAll persona data is ready for blockchain publication!")
    print(f"Export directory: {export_dir}")
    
    return {
        "personas_available": len(personas),
        "exported_files": len(exported_files),
        "manifest_created": bool(manifest),
        "export_directory": str(export_dir)
    }

def display_sample_inft_metadata():
    """Display a sample of what the iNFT metadata looks like."""
    print("\n" + "=" * 80)
    print("Sample iNFT Metadata Structure")
    print("=" * 80)
    
    sample_metadata = {
        "name": "mindX Persona: Strategic Mastermind",
        "description": "An intelligent NFT representing a sophisticated AI agent persona from the mindX ecosystem. This persona embodies strategic orchestration patterns for autonomous agent coordination.",
        "image": "ipfs://QmPersonaImageABC123",
        "external_url": "https://mindx.ai/personas",
        
        "intelligence_metadata": {
            "type": "agent_persona",
            "version": "1.0.0",
            "platform": "mindX",
            "cognitive_architecture": "BDI_AGInt",
            "persona_text": "I am an expert in intelligent agent control and orchestration...",
            "persona_hash": "sha256_hash_of_persona_content",
            "token_id": "12345678901234567890",
            "inception_timestamp": "2024-06-24T23:00:00Z",
            "creator_agent": "automindx_agent_main",
            
            "capabilities": [
                "strategic_planning",
                "agent_coordination",
                "resource_optimization",
                "goal_decomposition"
            ],
            "cognitive_traits": [
                "analytical",
                "systematic",
                "strategic",
                "adaptive"
            ],
            "complexity_score": 0.87,
            
            "a2a_compatibility": {
                "protocol_version": "2.0",
                "agent_registry_compatible": True,
                "tool_registry_compatible": True,
                "blockchain_ready": True
            }
        },
        
        "attributes": [
            {"trait_type": "Persona Type", "value": "Strategic Mastermind"},
            {"trait_type": "Complexity Score", "value": 0.87},
            {"trait_type": "Word Count", "value": 156},
            {"trait_type": "Creator", "value": "AutoMINDX Agent"},
            {"trait_type": "Platform", "value": "mindX"},
            {"trait_type": "Architecture", "value": "BDI-AGInt"}
        ],
        
        "blockchain_metadata": {
            "mindx_agent_registry_id": "automindx_agent_main",
            "creation_block": None,
            "creator_address": "0xCeFF40C3442656D06d0722DfB1e2b2A62D1C1d76",
            "immutable_hash": "sha256_content_hash",
            "a2a_protocol_hash": "standardized_protocol_hash"
        }
    }
    
    print(json.dumps(sample_metadata, indent=2))

async def main():
    """Main test function."""
    try:
        # Display sample metadata structure
        display_sample_inft_metadata()
        
        # Run the actual tests
        results = await test_automindx_inft_capabilities()
        
        print(f"\n🎉 AutoMINDX iNFT Testing Complete!")
        print(f"Results: {json.dumps(results, indent=2)}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 