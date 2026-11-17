#!/usr/bin/env python3

import requests
import json
import sys
from datetime import datetime

def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_endpoint(url, method="GET", data=None, description=""):
    print(f"\nTesting: {description}")
    print(f"URL: {url}")
    print(f"Method: {method}")
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            print(f"Payload: {json.dumps(data, indent=2)}")
            response = requests.post(url, json=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("SUCCESS")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print("FAILED")
            print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"
    print_section(f"Testing ER Wait Time API at {base_url}")
    results = {}
    print_section("Test 1: Root Endpoint")
    results['root'] = test_endpoint(f"{base_url}/", description="API information endpoint")
    print_section("Test 2: Health Check (Liveness Probe)")
    results['healthz'] = test_endpoint(f"{base_url}/healthz", description="Kubernetes liveness probe endpoint")
    print_section("Test 3: Readiness Check")
    results['ready'] = test_endpoint(f"{base_url}/ready", description="Kubernetes readiness probe endpoint")
    print_section("Test 4: Detailed Health Status")
    results['health'] = test_endpoint(f"{base_url}/health", description="Detailed health status with model info")
    print_section("Test 5: Model Information")
    results['models'] = test_endpoint(f"{base_url}/models", description="Model metadata and performance metrics")
    print_section("Test 6: Prediction - Normal Case")
    normal_patient = {
        "arrival_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "triage_level": 3,
        "age": 45,
        "department": "General",
        "num_doctors_available": 5,
        "queue_length": 12,
        "is_weekend": 0
    }
    results['predict_normal'] = test_endpoint(f"{base_url}/predict", method="POST", data=normal_patient, description="Prediction for normal case patient")
    print_section("Test 7: Prediction - High Risk Case")
    high_risk_patient = {
        "arrival_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "triage_level": 5,
        "age": 65,
        "department": "General",
        "num_doctors_available": 2,
        "queue_length": 25,
        "is_weekend": 1
    }
    results['predict_high_risk'] = test_endpoint(f"{base_url}/predict", method="POST", data=high_risk_patient, description="Prediction for high-risk case")
    print_section("Test 8: Prediction - Low Risk Case")
    low_risk_patient = {
        "arrival_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "triage_level": 1,
        "age": 30,
        "department": "General",
        "num_doctors_available": 8,
        "queue_length": 3,
        "is_weekend": 0
    }
    results['predict_low_risk'] = test_endpoint(f"{base_url}/predict", method="POST", data=low_risk_patient, description="Prediction for low-risk case")
    print_section("Test 9: Error Handling - Invalid Input")
    invalid_patient = {
        "arrival_time": "invalid-date",
        "triage_level": 10,
        "age": -5,
        "department": "Unknown",
        "num_doctors_available": -1,
        "queue_length": -10,
        "is_weekend": 2
    }
    print("(This test should fail - testing error handling)")
    test_endpoint(f"{base_url}/predict", method="POST", data=invalid_patient, description="Invalid input to test error handling")
    print_section("Test Summary")
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")
    if passed_tests == total_tests:
        print("\nAll tests passed!")
        return 0
    else:
        print(f"\n{total_tests - passed_tests} test(s) failed")
        return 1

if __name__ == "__main__":
    print("""
ER Wait Time API - Comprehensive Test Suite

Usage:
  python test_api.py                    # Test localhost:8000
  python test_api.py http://URL:PORT    # Test custom URL

Examples:
  python test_api.py
  python test_api.py http://localhost:8000
  python test_api.py http://192.168.1.100:8000
  python test_api.py http://your-k8s-service-url
    """)
    sys.exit(main())
