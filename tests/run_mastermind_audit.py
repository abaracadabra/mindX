#!/usr/bin/env python3
"""
Mastermind Cognition Audit Runner

This script uses the enhanced test agent to run a comprehensive audit of the
mastermind agent's cognitive capabilities and generate a detailed report.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.enhanced_test_agent import EnhancedUltimateCognitionTestAgent
from tests.lab.test_mastermind_cognition_audit import test_mastermind_cognition_comprehensive
from tests.report_agent import ReportAgent, ReportType, ReportFormat

async def run_mastermind_audit():
    """Run comprehensive mastermind cognition audit and generate report."""
    print("=" * 60)
    print("MINDX MASTERMIND COGNITION AUDIT")
    print("=" * 60)
    
    # Initialize enhanced test agent
    test_agent = EnhancedUltimateCognitionTestAgent(agent_id="mastermind_audit_runner")
    
    print("\n🔍 Initializing Enhanced Test Agent...")
    print(f"Lab tests discovered: {len(test_agent.test_registry)}")
    
    # Show lab test summary
    lab_summary = test_agent.get_lab_test_summary()
    print(f"Test types: {lab_summary['test_types']}")
    
    print("\n🧠 Running Comprehensive Mastermind Cognition Audit...")
    
    try:
        # Execute the comprehensive audit
        result = await test_mastermind_cognition_comprehensive()
        
        # Update test registry with results
        test_id = "test_mastermind_cognition_audit::test_mastermind_cognition_comprehensive"
        if test_id in test_agent.test_registry:
            test_agent.test_registry[test_id].add_outcome(
                success=result["success"],
                execution_time=result["execution_time"],
                details=result["details"]
            )
            test_agent._save_test_registry()
        
        print("\n📊 AUDIT RESULTS SUMMARY")
        print("-" * 30)
        print(f"Overall Success: {'✅ PASS' if result['success'] else '❌ FAIL'}")
        print(f"Overall Score: {result['score']:.2f}/1.00")
        print(f"Execution Time: {result['execution_time']:.2f} seconds")
        
        # Display category scores
        if "category_scores" in result["details"]:
            print(f"\n📈 CATEGORY BREAKDOWN")
            print("-" * 25)
            for category, score in result["details"]["category_scores"].items():
                status = "✅" if score > 0.7 else "⚠️" if score > 0.5 else "❌"
                print(f"{status} {category.replace('_', ' ').title()}: {score:.2f}")
        
        # Display recommendations
        if "recommendations" in result["details"]:
            print(f"\n💡 RECOMMENDATIONS ({len(result['details']['recommendations'])})")
            print("-" * 20)
            for i, rec in enumerate(result["details"]["recommendations"], 1):
                print(f"{i}. {rec}")
        
        # Display critical issues
        if "critical_issues" in result["details"] and result["details"]["critical_issues"]:
            print(f"\n🚨 CRITICAL ISSUES ({len(result['details']['critical_issues'])})")
            print("-" * 18)
            for i, issue in enumerate(result["details"]["critical_issues"], 1):
                print(f"{i}. {issue}")
        
        # Generate detailed report
        print(f"\n📝 Generating Detailed Report...")
        
        report_agent = ReportAgent()
        report_data = {
            "test_name": "Mastermind Cognition Audit",
            "overall_success": result["success"],
            "overall_score": result["score"],
            "execution_time": result["execution_time"],
            "category_results": result["details"].get("category_scores", {}),
            "recommendations": result["details"].get("recommendations", []),
            "critical_issues": result["details"].get("critical_issues", []),
            "test_metadata": {
                "audit_type": "comprehensive_cognition",
                "agent_under_test": "mastermind_prime",
                "test_categories": [
                    "strategic_reasoning",
                    "tool_orchestration", 
                    "memory_integration",
                    "bdi_coordination",
                    "self_improvement",
                    "failure_recovery",
                    "performance_optimization"
                ]
            }
        }
        
        # Generate technical report
        report_path = await report_agent.generate_report(
            report_type=ReportType.COGNITION_TEST,
            report_format=ReportFormat.TECHNICAL,
            report_data=report_data,
            filename="mastermind_cognition_audit_technical"
        )
        
        print(f"✅ Technical report generated: {report_path}")
        
        # Generate executive summary
        exec_report_path = await report_agent.generate_report(
            report_type=ReportType.COGNITION_TEST,
            report_format=ReportFormat.EXECUTIVE,
            report_data=report_data,
            filename="mastermind_cognition_audit_executive"
        )
        
        print(f"✅ Executive summary generated: {exec_report_path}")
        
        # Final assessment
        print(f"\n🎯 FINAL ASSESSMENT")
        print("-" * 18)
        
        if result["score"] >= 0.8:
            print("🟢 EXCELLENT: Mastermind cognition is performing at high levels")
        elif result["score"] >= 0.7:
            print("🟡 GOOD: Mastermind cognition is performing well with room for improvement")
        elif result["score"] >= 0.6:
            print("🟠 ACCEPTABLE: Mastermind cognition meets minimum requirements")
        else:
            print("🔴 NEEDS ATTENTION: Mastermind cognition requires immediate improvement")
        
        return result
        
    except Exception as e:
        print(f"\n❌ AUDIT FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Main execution function."""
    result = await run_mastermind_audit()
    
    if result:
        print(f"\n✅ Mastermind cognition audit completed successfully")
        return 0
    else:
        print(f"\n❌ Mastermind cognition audit failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)