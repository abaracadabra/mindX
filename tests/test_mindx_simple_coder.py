#!/usr/bin/env python3
"""
Test script to use mindXagent with simple_coder_agent to fix and improve augmentic.py
This script demonstrates the integration and shows memory_agent logs.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.simple_coder_agent import SimpleCoderAgent
from agents.memory_agent import MemoryAgent
from utils.config import Config
from utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

async def test_mindx_with_simple_coder():
    """Test simple_coder_agent to improve augmentic.py in sandbox"""
    
    print("=" * 80)
    print("Testing simple_coder_agent to improve augmentic.py")
    print("=" * 80)
    
    # Initialize components
    config = Config()
    memory_agent = MemoryAgent(config=config)
    
    # Initialize simple_coder_agent
    print("\n[1/5] Initializing SimpleCoderAgent...")
    simple_coder = SimpleCoderAgent(
        memory_agent=memory_agent,
        config=config
    )
    print(f"✅ SimpleCoderAgent initialized")
    print(f"   Sandbox root: {simple_coder.sandbox_root}")
    print(f"   Working directory: {simple_coder.current_working_directory}")
    
    # Check augmentic.py in sandbox
    augmentic_path = simple_coder.sandbox_root / "working" / "augmentic.py"
    print(f"\n[3/5] Checking augmentic.py in sandbox...")
    print(f"   Path: {augmentic_path}")
    
    if augmentic_path.exists():
        # Read current file
        with open(augmentic_path, 'r') as f:
            content = f.read()
        print(f"   ✅ File exists ({len(content)} characters)")
        
        # Analyze the file
        print(f"\n[4/5] Analyzing augmentic.py...")
        analysis = await simple_coder.execute(
            operation="analyze_code",
            file_path="augmentic.py",
            code_content=content[:5000] if len(content) > 5000 else content  # Limit for analysis
        )
        
        if analysis.get("status") == "SUCCESS":
            print(f"   ✅ Analysis completed")
            print(f"   Analysis preview: {str(analysis.get('analysis', {}))[:200]}...")
        else:
            print(f"   ⚠️  Analysis status: {analysis.get('status')}")
            print(f"   Message: {analysis.get('message', 'No message')}")
    else:
        print(f"   ⚠️  File not found in sandbox, copying from project root...")
        # Copy from project root if exists
        source_path = PROJECT_ROOT / "augmentic.py"
        if source_path.exists():
            import shutil
            shutil.copy2(source_path, augmentic_path)
            print(f"   ✅ Copied from {source_path}")
        else:
            print(f"   ❌ Source file not found at {source_path}")
            return
    
    # Create improvement directive
    directive = """
    Improve augmentic.py by:
    1. Adding better error handling and logging
    2. Improving code organization and structure
    3. Adding type hints where missing
    4. Fixing any code quality issues
    5. Optimizing imports and dependencies
    6. Adding comprehensive docstrings
    """
    
    print(f"\n[5/5] Executing improvement directive...")
    print(f"   Directive: {directive.strip()[:100]}...")
    
    # Use simple_coder_agent to improve the file
    try:
        # First, read the full file
        read_result = await simple_coder.execute(
            operation="read_file",
            path="augmentic.py"
        )
        
        if read_result.get("status") == "SUCCESS":
            file_content = read_result.get("content", "")
            
            # Generate improved code
            generate_result = await simple_coder.execute(
                operation="generate_code",
                description=directive,
                language="python",
                style="clean"
            )
            
            if generate_result.get("status") == "SUCCESS":
                print(f"   ✅ Code generation completed")
                
                # Use optimize_code to improve the existing file
                optimize_result = await simple_coder.execute(
                    operation="optimize_code",
                    file_path="augmentic.py",
                    code_content=file_content
                )
                
                if optimize_result.get("status") == "SUCCESS":
                    print(f"   ✅ Code optimization completed")
                    print(f"   Optimization preview: {str(optimize_result.get('optimization', {}))[:200]}...")
                else:
                    print(f"   ⚠️  Optimization status: {optimize_result.get('status')}")
            else:
                print(f"   ⚠️  Generation status: {generate_result.get('status')}")
        else:
            print(f"   ⚠️  Read status: {read_result.get('status')}")
            
    except Exception as e:
        logger.error(f"Error during improvement: {e}", exc_info=True)
        print(f"   ❌ Error: {e}")
    
    # Show memory logs
    print(f"\n" + "=" * 80)
    print("Memory Agent Logs")
    print("=" * 80)
    
    # Get recent memory logs
    memory_dir = PROJECT_ROOT / "data" / "memory" / "stm"
    
    if memory_dir.exists():
        print(f"\nMemory directory: {memory_dir}")
        
        # Find simple_coder related memories
        simple_coder_dirs = [
            memory_dir / "simple_coder",
            memory_dir / "simple_coder_agent",
        ]
        
        for mem_dir in simple_coder_dirs:
            if mem_dir.exists():
                print(f"\n📁 {mem_dir.name}/")
                files = list(mem_dir.rglob("*.json"))
                if files:
                    # Show most recent files
                    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    print(f"   Found {len(files)} memory files")
                    print(f"   Most recent files:")
                    for f in files[:5]:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        size = f.stat().st_size
                        print(f"     - {f.name} ({size} bytes, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
                else:
                    print(f"   No memory files found")
    
    print(f"\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)

if __name__ == "__main__":
    setup_logging()
    asyncio.run(test_mindx_with_simple_coder())
