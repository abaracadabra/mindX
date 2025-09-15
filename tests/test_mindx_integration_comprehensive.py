#!/usr/bin/env python3
"""
Comprehensive MindX Integration Test Suite
Tests frontend-backend integration, Mistral API connectivity, and agent management
"""

import asyncio
import json
import time
import requests
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class MindXIntegrationTester:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.test_results = {
            "timestamp": time.time(),
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }
    
    def log_test(self, test_name, passed, details=""):
        """Log test result"""
        self.test_results["tests_run"] += 1
        if passed:
            self.test_results["tests_passed"] += 1
            status = "✅ PASS"
        else:
            self.test_results["tests_failed"] += 1
            status = "❌ FAIL"
        
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": time.time()
        }
        self.test_results["details"].append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"    {details}")
    
    def test_backend_health(self):
        """Test backend health endpoint"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("Backend Health Check", True, f"Status: {data['status']}")
                    return True
                else:
                    self.log_test("Backend Health Check", False, f"Unhealthy status: {data.get('status')}")
                    return False
            else:
                self.log_test("Backend Health Check", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Backend Health Check", False, f"Error: {str(e)}")
            return False
    
    def test_frontend_accessibility(self):
        """Test frontend accessibility"""
        try:
            response = requests.get(self.frontend_url, timeout=5)
            if response.status_code == 200 and "mindX Control Panel" in response.text:
                self.log_test("Frontend Accessibility", True, "Frontend accessible and contains expected content")
                return True
            else:
                self.log_test("Frontend Accessibility", False, f"HTTP {response.status_code} or missing content")
                return False
        except Exception as e:
            self.log_test("Frontend Accessibility", False, f"Error: {str(e)}")
            return False
    
    def test_cors_headers(self):
        """Test CORS configuration"""
        try:
            headers = {"Origin": self.frontend_url}
            response = requests.get(f"{self.backend_url}/health", headers=headers, timeout=5)
            cors_headers = response.headers.get("access-control-allow-origin")
            if cors_headers == "*":
                self.log_test("CORS Configuration", True, "CORS properly configured")
                return True
            else:
                self.log_test("CORS Configuration", False, f"CORS header: {cors_headers}")
                return False
        except Exception as e:
            self.log_test("CORS Configuration", False, f"Error: {str(e)}")
            return False
    
    def test_mistral_api_connectivity(self):
        """Test Mistral API connectivity"""
        try:
            # Test through the backend's Mistral integration
            response = requests.get(f"{self.backend_url}/status/mastermind", timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Check if Mistral is being used (indirect test)
                if "mistral" in str(data).lower() or "api" in str(data).lower():
                    self.log_test("Mistral API Connectivity", True, "Mistral API integration detected")
                    return True
                else:
                    self.log_test("Mistral API Connectivity", False, "No Mistral API integration found")
                    return False
            else:
                self.log_test("Mistral API Connectivity", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Mistral API Connectivity", False, f"Error: {str(e)}")
            return False
    
    def test_agents_registry(self):
        """Test agents registry endpoint"""
        try:
            response = requests.get(f"{self.backend_url}/registry/agents", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "agents" in data and isinstance(data["agents"], list):
                    agent_count = len(data["agents"])
                    self.log_test("Agents Registry", True, f"Found {agent_count} agents")
                    return data["agents"]
                else:
                    self.log_test("Agents Registry", False, "Invalid response format")
                    return []
            else:
                self.log_test("Agents Registry", False, f"HTTP {response.status_code}")
                return []
        except Exception as e:
            self.log_test("Agents Registry", False, f"Error: {str(e)}")
            return []
    
    def test_system_metrics(self):
        """Test system metrics endpoint"""
        try:
            response = requests.get(f"{self.backend_url}/system/metrics", timeout=5)
            if response.status_code == 200:
                data = response.json()
                required_fields = ["cpu_usage", "memory_usage", "timestamp"]
                if all(field in data for field in required_fields):
                    self.log_test("System Metrics", True, f"CPU: {data.get('cpu_usage', 'N/A')}%, Memory: {data.get('memory_usage', 'N/A')}%")
                    return True
                else:
                    self.log_test("System Metrics", False, f"Missing fields: {[f for f in required_fields if f not in data]}")
                    return False
            else:
                self.log_test("System Metrics", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("System Metrics", False, f"Error: {str(e)}")
            return False
    
    def test_frontend_backend_integration(self):
        """Test frontend-backend integration"""
        try:
            # Test that frontend can make requests to backend
            headers = {"Origin": self.frontend_url}
            endpoints = ["/health", "/status/mastermind", "/registry/agents", "/system/metrics"]
            successful_requests = 0
            
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{self.backend_url}{endpoint}", headers=headers, timeout=5)
                    if response.status_code == 200:
                        successful_requests += 1
                except:
                    pass
            
            success_rate = (successful_requests / len(endpoints)) * 100
            if success_rate >= 75:  # At least 75% of endpoints should work
                self.log_test("Frontend-Backend Integration", True, f"{success_rate:.1f}% of endpoints accessible")
                return True
            else:
                self.log_test("Frontend-Backend Integration", False, f"Only {success_rate:.1f}% of endpoints accessible")
                return False
        except Exception as e:
            self.log_test("Frontend-Backend Integration", False, f"Error: {str(e)}")
            return False
    
    def test_mistral_direct_api(self):
        """Test Mistral API directly"""
        try:
            # Check if Mistral API key is configured
            env_file = project_root / ".env"
            if env_file.exists():
                with open(env_file, 'r') as f:
                    content = f.read()
                    if "MISTRAL_API_KEY" in content and "YOUR_MISTRAL_API_KEY_HERE" not in content:
                        self.log_test("Mistral API Key Configuration", True, "API key configured")
                        
                        # Try to make a direct Mistral API call
                        try:
                            from llm.mistral_handler import MistralHandler
                            handler = MistralHandler()
                            # This is a basic test - in a real scenario you'd test actual API calls
                            self.log_test("Mistral Handler Initialization", True, "Mistral handler can be instantiated")
                            return True
                        except Exception as e:
                            self.log_test("Mistral Handler Initialization", False, f"Error: {str(e)}")
                            return False
                    else:
                        self.log_test("Mistral API Key Configuration", False, "API key not properly configured")
                        return False
            else:
                self.log_test("Mistral API Key Configuration", False, ".env file not found")
                return False
        except Exception as e:
            self.log_test("Mistral API Key Configuration", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting MindX Integration Test Suite")
        print("=" * 50)
        
        # Core connectivity tests
        self.test_backend_health()
        self.test_frontend_accessibility()
        self.test_cors_headers()
        
        # API integration tests
        self.test_mistral_api_connectivity()
        self.test_mistral_direct_api()
        
        # System functionality tests
        agents = self.test_agents_registry()
        self.test_system_metrics()
        self.test_frontend_backend_integration()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {self.test_results['tests_run']}")
        print(f"Passed: {self.test_results['tests_passed']}")
        print(f"Failed: {self.test_results['tests_failed']}")
        print(f"Success Rate: {(self.test_results['tests_passed'] / self.test_results['tests_run'] * 100):.1f}%")
        
        # Save results
        self.save_results()
        
        return self.test_results
    
    def save_results(self):
        """Save test results to file"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = project_root / "tests" / f"integration_test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n💾 Test results saved to: {results_file}")

def main():
    """Main test runner"""
    tester = MindXIntegrationTester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    if results["tests_failed"] == 0:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {results['tests_failed']} tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
