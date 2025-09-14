#!/usr/bin/env python3
"""
Comprehensive Test Runner for agent_create Workflow
Runs all tests and generates detailed reports with proof of functionality.
"""

import datetime
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from io import StringIO

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from utils.logging_config import setup_logging


class ComprehensiveTestRunner:
    """Runs all agent_create tests and generates comprehensive reports."""
    
    def __init__(self):
        self.start_time = time.time()
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.reports_dir = Path("tests/reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        # Setup logging
        setup_logging()
        
        self.results = {
            "timestamp": self.timestamp,
            "start_time": self.start_time,
            "test_suites": {},
            "summary": {},
            "live_agent_tests": []
        }
    
    def run_test_suite(self, test_file, suite_name):
        """Run a specific test suite and capture results."""
        print(f"\n{'='*60}")
        print(f"🧪 RUNNING {suite_name.upper()}")
        print(f"{'='*60}")
        
        # Capture output
        output_buffer = StringIO()
        
        try:
            # Run the test
            result = subprocess.run([
                sys.executable, test_file
            ], capture_output=True, text=True, timeout=300)
            
            suite_result = {
                "suite_name": suite_name,
                "test_file": test_file,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
                "duration": None
            }
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            self.results["test_suites"][suite_name] = suite_result
            return suite_result
            
        except subprocess.TimeoutExpired:
            print(f"❌ Test suite {suite_name} timed out!")
            suite_result = {
                "suite_name": suite_name,
                "test_file": test_file,
                "exit_code": -1,
                "stdout": "",
                "stderr": "Test timed out after 300 seconds",
                "success": False,
                "duration": 300
            }
            self.results["test_suites"][suite_name] = suite_result
            return suite_result
        
        except Exception as e:
            print(f"❌ Error running test suite {suite_name}: {e}")
            suite_result = {
                "suite_name": suite_name,
                "test_file": test_file,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
                "duration": None
            }
            self.results["test_suites"][suite_name] = suite_result
            return suite_result
    
    def test_live_agent_creation(self):
        """Test live agent creation with actual mindX system."""
        print(f"\n{'='*60}")
        print("🚀 TESTING LIVE AGENT CREATION")
        print(f"{'='*60}")
        
        test_agents = [
            {
                "command": "echo 'agent_create test_reporter reporter for generating test reports and documentation' | python3 scripts/run_mindx.py",
                "expected_type": "test_reporter",
                "expected_id": "reporter"
            },
            {
                "command": "echo 'agent_create benchmark_tool benchmark for performance benchmarking and analysis' | python3 scripts/run_mindx.py",
                "expected_type": "benchmark_tool", 
                "expected_id": "benchmark"
            },
            {
                "command": "echo 'agent_create quality_checker checker {\"description\": \"quality assurance agent\", \"priority\": \"high\"}' | python3 scripts/run_mindx.py",
                "expected_type": "quality_checker",
                "expected_id": "checker"
            }
        ]
        
        for i, test_case in enumerate(test_agents):
            print(f"\n🔧 Testing live agent creation {i+1}/3...")
            print(f"Command: {test_case['command']}")
            
            try:
                result = subprocess.run(
                    test_case["command"], 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    timeout=180
                )
                
                live_test_result = {
                    "test_number": i + 1,
                    "command": test_case["command"],
                    "expected_type": test_case["expected_type"],
                    "expected_id": test_case["expected_id"],
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "success": result.returncode == 0,
                    "agent_created": "Agent creation successful!" in result.stdout,
                    "code_generated": f"agents/{test_case['expected_id']}.py" in result.stdout,
                    "identity_created": "Public Address:" in result.stdout,
                    "registered": "Total agents:" in result.stdout
                }
                
                self.results["live_agent_tests"].append(live_test_result)
                
                if live_test_result["success"]:
                    print(f"✅ Agent {test_case['expected_id']} created successfully!")
                else:
                    print(f"❌ Agent creation failed with exit code {result.returncode}")
                    
            except subprocess.TimeoutExpired:
                print(f"❌ Live agent creation {i+1} timed out!")
                live_test_result = {
                    "test_number": i + 1,
                    "command": test_case["command"],
                    "expected_type": test_case["expected_type"],
                    "expected_id": test_case["expected_id"],
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": "Command timed out after 180 seconds",
                    "success": False,
                    "agent_created": False,
                    "code_generated": False,
                    "identity_created": False,
                    "registered": False
                }
                self.results["live_agent_tests"].append(live_test_result)
                
            except Exception as e:
                print(f"❌ Error in live agent creation {i+1}: {e}")
                live_test_result = {
                    "test_number": i + 1,
                    "command": test_case["command"],
                    "expected_type": test_case["expected_type"],
                    "expected_id": test_case["expected_id"],
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": str(e),
                    "success": False,
                    "agent_created": False,
                    "code_generated": False,
                    "identity_created": False,
                    "registered": False
                }
                self.results["live_agent_tests"].append(live_test_result)
    
    def generate_summary(self):
        """Generate comprehensive test summary."""
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        # Count results
        total_suites = len(self.results["test_suites"])
        successful_suites = sum(1 for suite in self.results["test_suites"].values() if suite["success"])
        failed_suites = total_suites - successful_suites
        
        total_live_tests = len(self.results["live_agent_tests"])
        successful_live_tests = sum(1 for test in self.results["live_agent_tests"] if test["success"])
        failed_live_tests = total_live_tests - successful_live_tests
        
        # Generate summary
        self.results["summary"] = {
            "total_duration": total_duration,
            "end_time": end_time,
            "test_suites": {
                "total": total_suites,
                "successful": successful_suites,
                "failed": failed_suites,
                "success_rate": (successful_suites / total_suites * 100) if total_suites > 0 else 0
            },
            "live_agent_tests": {
                "total": total_live_tests,
                "successful": successful_live_tests,
                "failed": failed_live_tests,
                "success_rate": (successful_live_tests / total_live_tests * 100) if total_live_tests > 0 else 0
            },
            "overall_success": (successful_suites == total_suites) and (successful_live_tests == total_live_tests)
        }
    
    def save_reports(self):
        """Save all reports to files."""
        # Save JSON report
        json_report_path = self.reports_dir / f"test_results_{self.timestamp}.json"
        with open(json_report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Save human-readable report
        text_report_path = self.reports_dir / f"test_report_{self.timestamp}.txt"
        with open(text_report_path, 'w') as f:
            self.write_text_report(f)
        
        # Save summary report
        summary_path = self.reports_dir / f"test_summary_{self.timestamp}.txt"
        with open(summary_path, 'w') as f:
            self.write_summary_report(f)
        
        return {
            "json_report": str(json_report_path),
            "text_report": str(text_report_path),
            "summary_report": str(summary_path)
        }
    
    def write_text_report(self, f):
        """Write detailed text report."""
        f.write("=" * 80 + "\n")
        f.write("COMPREHENSIVE AGENT_CREATE WORKFLOW TEST RESULTS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Test Run Timestamp: {self.timestamp}\n")
        f.write(f"Total Duration: {self.results['summary']['total_duration']:.2f} seconds\n")
        f.write("\n")
        
        # Test Suites Results
        f.write("TEST SUITES RESULTS:\n")
        f.write("-" * 40 + "\n")
        for suite_name, suite_result in self.results["test_suites"].items():
            f.write(f"\n{suite_name.upper()}:\n")
            f.write(f"  File: {suite_result['test_file']}\n")
            f.write(f"  Success: {'✅ YES' if suite_result['success'] else '❌ NO'}\n")
            f.write(f"  Exit Code: {suite_result['exit_code']}\n")
            if suite_result['stderr']:
                f.write(f"  Errors: {suite_result['stderr']}\n")
            f.write("\n")
        
        # Live Agent Tests Results
        f.write("LIVE AGENT CREATION TESTS:\n")
        f.write("-" * 40 + "\n")
        for test in self.results["live_agent_tests"]:
            f.write(f"\nTest {test['test_number']}: {test['expected_type']} -> {test['expected_id']}\n")
            f.write(f"  Success: {'✅ YES' if test['success'] else '❌ NO'}\n")
            f.write(f"  Agent Created: {'✅ YES' if test['agent_created'] else '❌ NO'}\n")
            f.write(f"  Code Generated: {'✅ YES' if test['code_generated'] else '❌ NO'}\n")
            f.write(f"  Identity Created: {'✅ YES' if test['identity_created'] else '❌ NO'}\n")
            f.write(f"  Registered: {'✅ YES' if test['registered'] else '❌ NO'}\n")
            f.write(f"  Exit Code: {test['exit_code']}\n")
            if test['stderr']:
                f.write(f"  Errors: {test['stderr']}\n")
            f.write("\n")
    
    def write_summary_report(self, f):
        """Write summary report."""
        summary = self.results["summary"]
        
        f.write("🎯 AGENT_CREATE WORKFLOW TEST SUMMARY\n")
        f.write("=" * 50 + "\n")
        f.write(f"📅 Test Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"⏱️  Total Duration: {summary['total_duration']:.2f} seconds\n")
        f.write(f"🎯 Overall Result: {'🎉 SUCCESS' if summary['overall_success'] else '❌ FAILURE'}\n")
        f.write("\n")
        
        f.write("📊 TEST SUITE RESULTS:\n")
        f.write(f"   Total Suites: {summary['test_suites']['total']}\n")
        f.write(f"   ✅ Successful: {summary['test_suites']['successful']}\n")
        f.write(f"   ❌ Failed: {summary['test_suites']['failed']}\n")
        f.write(f"   📈 Success Rate: {summary['test_suites']['success_rate']:.1f}%\n")
        f.write("\n")
        
        f.write("🚀 LIVE AGENT CREATION RESULTS:\n")
        f.write(f"   Total Tests: {summary['live_agent_tests']['total']}\n")
        f.write(f"   ✅ Successful: {summary['live_agent_tests']['successful']}\n")
        f.write(f"   ❌ Failed: {summary['live_agent_tests']['failed']}\n")
        f.write(f"   📈 Success Rate: {summary['live_agent_tests']['success_rate']:.1f}%\n")
        f.write("\n")
        
        if summary['overall_success']:
            f.write("🎉 CONCLUSION: All tests passed! The agent_create workflow is fully functional.\n")
        else:
            f.write("⚠️  CONCLUSION: Some tests failed. Review the detailed report for issues.\n")
    
    def run_all_tests(self):
        """Run all tests and generate reports."""
        print("🚀 STARTING COMPREHENSIVE AGENT_CREATE WORKFLOW TESTING")
        print("=" * 80)
        print(f"📅 Start Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Reports will be saved to: {self.reports_dir}")
        print()
        
        # Define test suites to run
        test_suites = [
            ("tests/test_cli_agent_create_parsing.py", "CLI_Parsing_Tests"),
            ("tests/test_agent_create_simple.py", "Simple_Workflow_Tests"),
            ("tests/test_agent_create_integration.py", "Integration_Tests")
        ]
        
        # Run test suites
        for test_file, suite_name in test_suites:
            if Path(test_file).exists():
                self.run_test_suite(test_file, suite_name)
            else:
                print(f"⚠️  Test file {test_file} not found, skipping...")
        
        # Run live agent creation tests
        self.test_live_agent_creation()
        
        # Generate summary and save reports
        self.generate_summary()
        report_files = self.save_reports()
        
        # Print final results
        print(f"\n{'='*80}")
        print("🏁 COMPREHENSIVE TEST RESULTS")
        print(f"{'='*80}")
        
        summary = self.results["summary"]
        print(f"⏱️  Total Duration: {summary['total_duration']:.2f} seconds")
        print(f"🎯 Overall Success: {'🎉 YES' if summary['overall_success'] else '❌ NO'}")
        print()
        print("📊 Test Suite Results:")
        print(f"   ✅ Successful: {summary['test_suites']['successful']}/{summary['test_suites']['total']}")
        print(f"   📈 Success Rate: {summary['test_suites']['success_rate']:.1f}%")
        print()
        print("🚀 Live Agent Tests:")
        print(f"   ✅ Successful: {summary['live_agent_tests']['successful']}/{summary['live_agent_tests']['total']}")
        print(f"   📈 Success Rate: {summary['live_agent_tests']['success_rate']:.1f}%")
        print()
        print("📁 Reports Generated:")
        for report_type, report_path in report_files.items():
            print(f"   📄 {report_type}: {report_path}")
        
        print(f"\n{'='*80}")
        if summary['overall_success']:
            print("🎉 ALL TESTS PASSED! The agent_create workflow is fully functional!")
        else:
            print("⚠️  Some tests failed. Check the detailed reports for more information.")
        print(f"{'='*80}")
        
        return summary['overall_success']


if __name__ == "__main__":
    runner = ComprehensiveTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1) 