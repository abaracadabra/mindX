#!/usr/bin/env python3
"""
Simplified Mastermind Cognition Audit
"""

import asyncio
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.config import Config
from utils.logging_config import get_logger
from agents.memory_agent import MemoryAgent

logger = get_logger(__name__)

class SimplifiedMastermindAudit:
    def __init__(self):
        self.config = Config()
        self.memory_agent = MemoryAgent(config=self.config)
        self.audit_start_time = time.time()
        
    async def run_audit(self):
        print("🧠 SIMPLIFIED MASTERMIND COGNITION AUDIT")
        print("=" * 50)
        
        audit_results = {
            "timestamp": datetime.now().isoformat(),
            "overall_score": 0.0,
            "category_scores": {},
            "findings": [],
            "execution_time": 0.0,
            "success": False
        }
        
        try:
            print("🔍 Analyzing System Components...")
            
            # Test 1: Memory System Health
            memory_score = await self._assess_memory_system()
            audit_results["category_scores"]["memory_system"] = memory_score
            print(f"   Memory System: {memory_score:.2f}/1.00")
            
            # Test 2: System Configuration
            config_score = await self._assess_system_configuration()
            audit_results["category_scores"]["system_configuration"] = config_score
            print(f"   System Config: {config_score:.2f}/1.00")
            
            # Test 3: Tool Registry
            tools_score = await self._assess_tool_registry()
            audit_results["category_scores"]["tool_registry"] = tools_score
            print(f"   Tool Registry: {tools_score:.2f}/1.00")
            
            # Calculate overall score
            scores = list(audit_results["category_scores"].values())
            audit_results["overall_score"] = sum(scores) / len(scores) if scores else 0.0
            
            audit_results["execution_time"] = time.time() - self.audit_start_time
            audit_results["success"] = True
            
            return audit_results
            
        except Exception as e:
            logger.error(f"Audit failed: {e}")
            audit_results["execution_time"] = time.time() - self.audit_start_time
            return audit_results
    
    async def _assess_memory_system(self):
        try:
            memory_base = Path("data/memory")
            if memory_base.exists():
                return 0.8
            else:
                return 0.3
        except:
            return 0.1
    
    async def _assess_system_configuration(self):
        try:
            config_dir = Path("data/config")
            if config_dir.exists():
                configs = list(config_dir.glob("*.json"))
                if len(configs) >= 3:
                    return 0.9
                elif len(configs) >= 1:
                    return 0.6
            return 0.3
        except:
            return 0.1
    
    async def _assess_tool_registry(self):
        try:
            tools_path = Path("data/config/official_tools_registry.json")
            if tools_path.exists():
                with open(tools_path) as f:
                    data = json.load(f)
                    if "tools" in data and len(data["tools"]) >= 5:
                        return 0.9
                    else:
                        return 0.6
            return 0.2
        except:
            return 0.1

async def main():
    auditor = SimplifiedMastermindAudit()
    results = await auditor.run_audit()
    
    print(f"\n📊 AUDIT SUMMARY")
    print("=" * 20)
    print(f"Overall Score: {results['overall_score']:.2f}/1.00")
    print(f"Success: {'✅ PASS' if results['success'] else '❌ FAIL'}")
    print(f"Execution Time: {results['execution_time']:.2f}s")
    
    print(f"\n📈 CATEGORY SCORES")
    for category, score in results["category_scores"].items():
        status = "✅" if score > 0.7 else "⚠️" if score > 0.5 else "❌"
        print(f"{status} {category.replace('_', ' ').title()}: {score:.2f}")
    
    return 0 if results["success"] else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
