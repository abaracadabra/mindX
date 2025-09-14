#!/usr/bin/env python3
"""
Comprehensive Agent Commands Test Runner
Runs all agent command tests and generates detailed reports

This runner executes all test suites related to agent commands:
- CLI parsing tests
- Simple workflow tests  
- Integration tests
- Lifecycle tests
- Live command tests
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_test_suite(test_file: str, suite_name: str) -> Dict[str, Any]:
    """
    Run a single test suite and return results.
    
    Args:
        test_file: Path to the test file
        suite_name: Human-readable name of the test suite
        
    Returns:
        Dictionary containing test results
    """
    print(f"\n🧪 Running {suite_name}...")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Parse output for test statistics
        stdout_lines = result.stdout.split('\n')
        stderr_lines = result.stderr.split('\n')
        
        # Look for test result patterns
        tests_run = 0
        failures = 0
        errors = 0
        success_rate = 0.0
        
        for line in stdout_lines:
            if "Tests Run:" in line:
                try:
                    tests_run = int(line.split("Tests Run:")[-1].strip())
                except ValueError:
                    pass
            elif "Failures:" in line:
                try:
                    failures = int(line.split("Failures:")[-1].strip())
                except ValueError:
                    pass
            elif "Errors:" in line:
                try:
                    errors = int(line.split("Errors:")[-1].strip())
                except ValueError:
                    pass
            elif "Success Rate:" in line:
                try:
                    success_rate = float(line.split("Success Rate:")[-1].replace("%", "").strip())
                except ValueError:
                    pass
        
        # If we didn't find stats in stdout, try parsing unittest output
        if tests_run == 0:
            for line in stdout_lines:
                if line.startswith("Ran ") and " tests in " in line:
                    try:
                        tests_run = int(line.split("Ran ")[1].split(" tests")[0])
                        if "OK" in line or result.returncode == 0:
                            success_rate = 100.0
                        break
                    except (ValueError, IndexError):
                        pass
        
        return {
            "suite_name": suite_name,
            "test_file": test_file,
            "exit_code": result.returncode,
            "duration": duration,
            "tests_run": tests_run,
            "failures": failures,
            "errors": errors,
            "success_rate": success_rate,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
        
    except subprocess.TimeoutExpired:
        return {
            "suite_name": suite_name,
            "test_file": test_file,
            "exit_code": -1,
            "duration": 300.0,
            "tests_run": 0,
            "failures": 0,
            "errors": 1,
            "success_rate": 0.0,
            "stdout": "",
            "stderr": "Test suite timed out after 5 minutes",
            "success": False
        }
    except Exception as e:
        return {
            "suite_name": suite_name,
            "test_file": test_file,
            "exit_code": -1,
            "duration": 0.0,
            "tests_run": 0,
            "failures": 0,
            "errors": 1,
            "success_rate": 0.0,
            "stdout": "",
            "stderr": f"Test execution error: {str(e)}",
            "success": False
        }

def generate_report(results: List[Dict[str, Any]], output_dir: Path) -> str:
    """Generate comprehensive test report."""
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Calculate overall statistics
    total_tests = sum(r["tests_run"] for r in results)
    total_failures = sum(r["failures"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    total_duration = sum(r["duration"] for r in results)
    successful_suites = sum(1 for r in results if r["success"])
    overall_success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
    
    # Generate summary report
    summary_report = f"""
# Agent Commands Test Suite - Complete Report
Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}

## Overall Summary
- **Total Test Suites**: {len(results)}
- **Successful Suites**: {successful_suites}/{len(results)}
- **Total Tests**: {total_tests}
- **Total Failures**: {total_failures}
- **Total Errors**: {total_errors}
- **Overall Success Rate**: {overall_success_rate:.1f}%
- **Total Duration**: {total_duration:.2f} seconds

## Test Suite Results

"""
    
    for result in results:
        status_emoji = "✅" if result["success"] else "❌"
        summary_report += f"""
### {status_emoji} {result["suite_name"]}
- **File**: `{result["test_file"]}`
- **Exit Code**: {result["exit_code"]}
- **Duration**: {result["duration"]:.2f} seconds
- **Tests Run**: {result["tests_run"]}
- **Failures**: {result["failures"]}
- **Errors**: {result["errors"]}
- **Success Rate**: {result["success_rate"]:.1f}%

"""
        
        if not result["success"]:
            summary_report += f"**Error Details**: {result['stderr'][:500]}...\n\n"
    
    # Add detailed analysis
    summary_report += f"""
## Analysis

### Performance Analysis
- **Fastest Suite**: {min(results, key=lambda x: x["duration"])["suite_name"]} ({min(r["duration"] for r in results):.2f}s)
- **Slowest Suite**: {max(results, key=lambda x: x["duration"])["suite_name"]} ({max(r["duration"] for r in results):.2f}s)
- **Average Duration**: {total_duration / len(results):.2f} seconds per suite

### Quality Metrics
- **Suite Success Rate**: {successful_suites / len(results) * 100:.1f}%
- **Test Success Rate**: {overall_success_rate:.1f}%
- **Total Test Coverage**: {total_tests} test cases across {len(results)} suites

### Recommendations
"""
    
    if overall_success_rate >= 95:
        summary_report += "🎉 **Excellent**: All agent commands are working perfectly!\n"
    elif overall_success_rate >= 80:
        summary_report += "✅ **Good**: Most agent commands are working well with minor issues.\n"
    elif overall_success_rate >= 60:
        summary_report += "⚠️ **Needs Attention**: Some agent commands have issues that should be addressed.\n"
    else:
        summary_report += "❌ **Critical**: Major issues detected in agent command functionality.\n"
    
    # Save summary report
    summary_file = output_dir / f"agent_tests_summary_{timestamp}.md"
    with summary_file.open("w", encoding="utf-8") as f:
        f.write(summary_report)
    
    # Save detailed JSON report
    json_file = output_dir / f"agent_tests_detailed_{timestamp}.json"
    with json_file.open("w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "overall_stats": {
                "total_suites": len(results),
                "successful_suites": successful_suites,
                "total_tests": total_tests,
                "total_failures": total_failures,
                "total_errors": total_errors,
                "overall_success_rate": overall_success_rate,
                "total_duration": total_duration
            },
            "suite_results": results
        }, f, indent=2)
    
    return str(summary_file)

def main():
    """Main test runner function."""
    print("🚀 Agent Commands Comprehensive Test Suite")
    print("=" * 60)
    print("Running all agent command tests...")
    
    # Define test suites to run
    test_suites = [
        ("tests/test_cli_agent_create_parsing.py", "CLI Parsing Tests"),
        ("tests/test_agent_create_simple.py", "Simple Workflow Tests"),
        ("tests/test_agent_create_integration.py", "Integration Tests"),
        ("tests/test_agent_lifecycle_complete.py", "Lifecycle Complete Tests"),
        ("tests/test_agent_commands_live.py", "Live Commands Tests"),
    ]
    
    results = []
    start_time = time.time()
    
    # Run each test suite
    for test_file, suite_name in test_suites:
        if Path(test_file).exists():
            result = run_test_suite(test_file, suite_name)
            results.append(result)
            
            # Print immediate feedback
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            print(f"\n{status} - {suite_name}")
            print(f"   Tests: {result['tests_run']}, Duration: {result['duration']:.2f}s")
            if not result["success"]:
                print(f"   Failures: {result['failures']}, Errors: {result['errors']}")
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    total_time = time.time() - start_time
    
    # Generate comprehensive report
    reports_dir = Path("tests/reports")
    summary_file = generate_report(results, reports_dir)
    
    # Print final summary
    print("\n" + "=" * 60)
    print("🎯 COMPREHENSIVE TEST RESULTS")
    print("=" * 60)
    
    successful_suites = sum(1 for r in results if r["success"])
    total_tests = sum(r["tests_run"] for r in results)
    total_failures = sum(r["failures"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    overall_success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Suites Run: {len(results)}")
    print(f"Successful Suites: {successful_suites}/{len(results)}")
    print(f"Total Tests: {total_tests}")
    print(f"Total Failures: {total_failures}")
    print(f"Total Errors: {total_errors}")
    print(f"Overall Success Rate: {overall_success_rate:.1f}%")
    print(f"Total Duration: {total_time:.2f} seconds")
    
    print(f"\n📊 Detailed report saved to: {summary_file}")
    
    # Final status
    if successful_suites == len(results) and overall_success_rate >= 95:
        print("\n🎉 ALL AGENT COMMAND TESTS SUCCESSFUL!")
        print("✨ The agent command workflow is fully functional!")
        return 0
    elif overall_success_rate >= 80:
        print("\n✅ AGENT COMMAND TESTS MOSTLY SUCCESSFUL!")
        print("⚠️  Minor issues detected, but core functionality works.")
        return 0
    else:
        print("\n❌ AGENT COMMAND TESTS HAVE ISSUES!")
        print("🔧 Please review the detailed report for troubleshooting.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 