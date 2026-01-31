#!/usr/bin/env python3
"""
Test script using simple_coder.py (not simple_coder_agent) to improve augmentic.py
This uses the sandbox system and shows memory logs.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.simple_coder import SimpleCoder
from utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

async def test_improve_augmentic():
    """Test simple_coder to improve augmentic.py in sandbox"""
    
    print("=" * 80)
    print("Testing SimpleCoder to improve augmentic.py")
    print("=" * 80)
    
    # Initialize SimpleCoder with sandbox mode
    print("\n[1/4] Initializing SimpleCoder...")
    simple_coder = SimpleCoder(sandbox_mode=True, autonomous_mode=False)
    print(f"✅ SimpleCoder initialized")
    print(f"   Sandbox directory: {simple_coder.sandbox_dir}")
    print(f"   Working directory: {simple_coder.sandbox_dir / 'working'}")
    
    # Check augmentic.py in sandbox
    augmentic_path = simple_coder.sandbox_dir / "working" / "augmentic.py"
    print(f"\n[2/4] Checking augmentic.py in sandbox...")
    print(f"   Path: {augmentic_path}")
    
    if augmentic_path.exists():
        with open(augmentic_path, 'r') as f:
            content = f.read()
        print(f"   ✅ File exists ({len(content)} characters, {len(content.splitlines())} lines)")
        
        # Count issues
        issues = []
        if "def " in content:
            func_count = content.count("def ")
            if func_count > 50:
                issues.append(f"Large number of functions ({func_count})")
        
        if content.count("simple_coder_cycle_1_function") > 0:
            issues.append("Contains repetitive simple_coder functions")
        
        if issues:
            print(f"   ⚠️  Issues found: {', '.join(issues)}")
        else:
            print(f"   ✅ No obvious issues detected")
    else:
        print(f"   ⚠️  File not found in sandbox")
        return
    
    # Process directive to improve the file
    directive = "evolve augmentic.py - improve code quality, remove duplicates, add better error handling"
    
    print(f"\n[3/4] Processing directive: {directive}")
    print(f"   This will create an update request in sandbox mode")
    
    try:
        results = await simple_coder.process_directive(directive, target_file="augmentic.py")
        
        print(f"\n   ✅ Directive processed")
        print(f"   Cycle: {results.get('cycle', 'N/A')}")
        print(f"   Changes: {len(results.get('changes', []))} items")
        print(f"   Update requests: {len(results.get('update_requests', []))}")
        print(f"   Backups: {len(results.get('backups', []))} created")
        
        if results.get('update_requests'):
            req = results['update_requests'][0]
            print(f"\n   📋 Update Request Created:")
            print(f"      ID: {req.get('request_id')}")
            print(f"      Status: {req.get('status')}")
            print(f"      Original: {req.get('original_file')}")
            print(f"      Sandbox: {req.get('sandbox_file')}")
        
    except Exception as e:
        logger.error(f"Error processing directive: {e}", exc_info=True)
        print(f"   ❌ Error: {e}")
    
    # Show memory logs
    print(f"\n[4/4] Memory Agent Logs")
    print("=" * 80)
    
    memory_dir = PROJECT_ROOT / "data" / "memory" / "stm"
    
    if memory_dir.exists():
        print(f"\nMemory directory: {memory_dir}")
        
        # Find simple_coder related memories
        simple_coder_dirs = [
            memory_dir / "simple_coder",
            memory_dir / "simple_coder_agent",
        ]
        
        total_files = 0
        for mem_dir in simple_coder_dirs:
            if mem_dir.exists():
                print(f"\n📁 {mem_dir.name}/")
                files = list(mem_dir.rglob("*.json"))
                if files:
                    total_files += len(files)
                    # Show most recent files
                    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    print(f"   Found {len(files)} memory files")
                    print(f"   Most recent files:")
                    for f in files[:5]:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        size = f.stat().st_size
                        rel_path = f.relative_to(memory_dir)
                        print(f"     - {rel_path}")
                        print(f"       Size: {size} bytes, Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # Show a preview of the content
                        try:
                            with open(f, 'r') as mem_file:
                                mem_data = json.load(mem_file)
                                category = mem_data.get('category', 'unknown')
                                memory_type = mem_data.get('memory_type', 'unknown')
                                print(f"       Category: {category}, Type: {memory_type}")
                        except:
                            pass
                else:
                    print(f"   No memory files found")
        
        print(f"\n📊 Summary: {total_files} total memory files found")
    
    # Show update requests
    print(f"\n" + "=" * 80)
    print("Update Requests")
    print("=" * 80)
    
    update_requests = simple_coder.get_update_requests()
    pending = [r for r in update_requests if r.get('status') == 'pending']
    print(f"\nTotal update requests: {len(update_requests)}")
    print(f"Pending requests: {len(pending)}")
    
    if pending:
        print(f"\nMost recent pending requests:")
        for req in pending[-5:]:
            print(f"  - {req.get('request_id')}: {req.get('original_file')} (cycle {req.get('cycle')})")
    
    print(f"\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)

if __name__ == "__main__":
    setup_logging()
    asyncio.run(test_improve_augmentic())
