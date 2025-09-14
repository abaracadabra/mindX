#!/usr/bin/env python3
"""
Integrated Mastermind Cognition Audit with Comprehensive Reporting
"""

import asyncio
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.config import Config
from utils.logging_config import get_logger
from tests.enhanced_test_agent import EnhancedUltimateCognitionTestAgent, TestRegistryEntry
from tests.report_agent import ReportAgent, ReportType, ReportFormat, ReportMetadata
from tests.simple_mastermind_audit import SimplifiedMastermindAudit

logger = get_logger(__name__)

class IntegratedMastermindAuditor:
    def __init__(self, test_session_id: str = None):
        self.test_session_id = test_session_id or f"mastermind_audit_{int(time.time())}"
        self.config = Config()
        
        # Initialize components
        self.test_agent = EnhancedUltimateCognitionTestAgent(
            agent_id=f"integrated_auditor_{self.test_session_id}"
        )
        self.report_agent = ReportAgent(
            agent_id=f"report_agent_{self.test_session_id}"
        )
        self.simplified_auditor = SimplifiedMastermindAudit()
        
        # Results storage
        self.audit_results = {
            "session_id": self.test_session_id,
            "timestamp": datetime.now().isoformat(),
            "test_agent_results": {},
            "simplified_audit_results": {},
            "lab_test_summary": {},
            "overall_assessment": {},
            "reports_generated": []
        }
        
    async def run_comprehensive_audit(self):
        start_time = time.time()
        
        try:
            print("🧠 INTEGRATED MASTERMIND COGNITION AUDIT")
            print("=" * 60)
            
            # Phase 1: Lab Test Analysis
            print("\n�� Phase 1: Lab Test Discovery and Registry Analysis")
            await self._run_lab_test_analysis()
            
            # Phase 2: Simplified System Audit
            print("\n🔍 Phase 2: System Health and Configuration Audit")
            await self._run_simplified_audit()
            
            # Phase 3: Analysis and Scoring
            print("\n📊 Phase 3: Comprehensive Analysis and Scoring")
            await self._run_comprehensive_analysis()
            
            # Phase 4: Report Generation
            print("\n📝 Phase 4: Report Generation")
            await self._generate_comprehensive_reports()
            
            self.audit_results["execution_time"] = time.time() - start_time
            self.audit_results["success"] = True
            
            await self._display_final_summary()
            
            return self.audit_results
            
        except Exception as e:
            logger.error(f"Integrated audit failed: {e}")
            self.audit_results["execution_time"] = time.time() - start_time
            self.audit_results["success"] = False
            self.audit_results["error"] = str(e)
            return self.audit_results
    
    async def _run_lab_test_analysis(self):
        try:
            lab_summary = self.test_agent.get_lab_test_summary()
            self.audit_results["lab_test_summary"] = lab_summary
            
            print(f"   📁 Lab tests discovered: {lab_summary['total_tests']}")
            print(f"   📊 Test types: {lab_summary['test_types']}")
            
        except Exception as e:
            self.audit_results["lab_test_summary"] = {"error": str(e)}
    
    async def _run_simplified_audit(self):
        try:
            audit_results = await self.simplified_auditor.run_audit()
            self.audit_results["simplified_audit_results"] = audit_results
            
            print(f"   🏥 System Health Score: {audit_results['overall_score']:.2f}/1.00")
            
        except Exception as e:
            self.audit_results["simplified_audit_results"] = {"error": str(e)}
    
    async def _run_comprehensive_analysis(self):
        try:
            system_score = self.audit_results["simplified_audit_results"].get("overall_score", 0)
            
            assessment = {
                "overall_score": system_score,
                "system_health_score": system_score,
                "assessment_level": self._get_assessment_level(system_score),
                "key_strengths": ["Functional system components"],
                "improvement_areas": ["Tool registry enhancement"],
                "recommendations": ["Continue monitoring and optimization"]
            }
            
            self.audit_results["overall_assessment"] = assessment
            
            print(f"   🎯 Overall Mastermind Score: {system_score:.2f}/1.00")
            print(f"   📊 Assessment Level: {assessment['assessment_level']}")
            
        except Exception as e:
            self.audit_results["overall_assessment"] = {"error": str(e)}
    
    async def _generate_comprehensive_reports(self):
        try:
            reports_generated = []
            
            # Generate technical report
            print("   📄 Generating Technical Report...")
            technical_success, technical_path = await self.report_agent.generate_cognition_test_report(
                self.audit_results
            )
            
            if technical_success:
                reports_generated.append(technical_path)
                print(f"     ✅ Technical report: {Path(technical_path).name}")
            
            self.audit_results["reports_generated"] = reports_generated
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            self.audit_results["reports_generated"] = []
    
    async def _display_final_summary(self):
        print(f"\n🎯 FINAL AUDIT SUMMARY")
        print("=" * 30)
        
        overall = self.audit_results["overall_assessment"]
        if "error" not in overall:
            print(f"Overall Score: {overall['overall_score']:.2f}/1.00")
            print(f"Assessment Level: {overall['assessment_level']}")
            print(f"Reports Generated: {len(self.audit_results['reports_generated'])}")
        
        print(f"Execution Time: {self.audit_results['execution_time']:.2f} seconds")
    
    def _get_assessment_level(self, score: float) -> str:
        if score >= 0.9:
            return "EXCELLENT"
        elif score >= 0.8:
            return "VERY GOOD"
        elif score >= 0.7:
            return "GOOD"
        elif score >= 0.6:
            return "ACCEPTABLE"
        else:
            return "NEEDS IMPROVEMENT"

async def test_integrated_mastermind_audit():
    """Run integrated mastermind audit test."""
    auditor = IntegratedMastermindAuditor()
    results = await auditor.run_comprehensive_audit()
    
    return {
        "success": results.get("success", False),
        "score": results["overall_assessment"].get("overall_score", 0),
        "execution_time": results.get("execution_time", 0),
        "reports_generated": len(results.get("reports_generated", [])),
        "details": results
    }

if __name__ == "__main__":
    async def main():
        auditor = IntegratedMastermindAuditor()
        results = await auditor.run_comprehensive_audit()
        
        return 0 if results.get("success", False) else 1
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
