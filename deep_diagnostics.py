"""
Deep Diagnostic Script for Railway Monitoring System
Tests all critical components end-to-end
"""

import requests
import json
import sys
import time
from datetime import datetime

class DeepDiagnostics:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.errors = []
        
    def log(self, message, status="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{status}] {message}")
        
    def test_endpoint(self, method, endpoint, expected_status=200, data=None):
        """Test a single API endpoint"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, timeout=5)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=5)
            elif method == "DELETE":
                response = requests.delete(url, timeout=5)
            else:
                response = requests.request(method, url, json=data, timeout=5)
            
            success = response.status_code == expected_status
            status = "PASS" if success else "FAIL"
            self.log(f"{method} {endpoint} - Status: {response.status_code} - {status}", status)
            
            if not success:
                self.errors.append(f"{method} {endpoint}: Expected {expected_status}, got {response.status_code}")
                
            return success, response.json() if success else None
            
        except Exception as e:
            self.log(f"{method} {endpoint} - ERROR: {str(e)}", "ERROR")
            self.errors.append(f"{method} {endpoint}: {str(e)}")
            return False, None
    
    def run_all_tests(self):
        """Run comprehensive diagnostic tests"""
        self.log("=" * 60)
        self.log("STARTING DEEP DIAGNOSTICS")
        self.log("=" * 60)
        
        # Test 1: Health Check
        self.log("\n[TEST 1] Health Check...")
        self.test_endpoint("GET", "/health")
        
        # Test 2: Root Endpoint
        self.log("\n[TEST 2] Root Endpoint...")
        self.test_endpoint("GET", "/")
        
        # Test 3: Network Interfaces
        self.log("\n[TEST 3] Network Interfaces...")
        self.test_endpoint("GET", "/api/v1/interfaces")
        
        # Test 4: Network Ranges
        self.log("\n[TEST 4] Network Ranges...")
        self.test_endpoint("GET", "/api/v1/network/ranges")
        
        # Test 5: Connected Devices
        self.log("\n[TEST 5] Connected Devices...")
        self.test_endpoint("GET", "/api/v1/connected")
        
        # Test 6: Active Scans
        self.log("\n[TEST 6] Active Scans...")
        self.test_endpoint("GET", "/api/v1/scan/active")
        
        # Test 7: Start Network Scan
        self.log("\n[TEST 7] Start Network Scan...")
        scan_data = {
            "network_range": "192.168.1.0/24",
            "scan_type": "quick",
            "timeout": 2.0
        }
        success, result = self.test_endpoint("POST", "/api/v1/scan/network", data=scan_data)
        
        if success and result and 'scan_id' in result:
            scan_id = result['scan_id']
            self.log(f"  Scan started with ID: {scan_id}")
            
            # Test 8: Get Scan Status
            self.log("\n[TEST 8] Get Scan Status...")
            time.sleep(1)
            self.test_endpoint("GET", f"/api/v1/scan/{scan_id}")
        
        # Test 9: System Status
        self.log("\n[TEST 9] System Status...")
        self.test_endpoint("GET", "/api/v2/status")
        
        # Test 10: WebSocket endpoint availability
        self.log("\n[TEST 10] WebSocket Endpoint...")
        try:
            import websocket
            ws = websocket.create_connection("ws://localhost:8000/api/v2/ws/realtime", timeout=3)
            ws.close()
            self.log("  WebSocket connection successful", "PASS")
        except Exception as e:
            self.log(f"  WebSocket connection failed: {e}", "WARN")
            self.errors.append(f"WebSocket: {e}")
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log("DIAGNOSTICS SUMMARY")
        self.log("=" * 60)
        
        if self.errors:
            self.log(f"\nERRORS FOUND: {len(self.errors)}", "ERROR")
            for error in self.errors:
                self.log(f"  - {error}", "ERROR")
        else:
            self.log("\nALL TESTS PASSED!", "PASS")
            
        return len(self.errors) == 0

if __name__ == "__main__":
    diagnostics = DeepDiagnostics()
    success = diagnostics.run_all_tests()
    sys.exit(0 if success else 1)
