#!/usr/bin/env python3
"""Quick test of production auth endpoints"""
import requests
import json

BASE_URL = "https://bijou-production.fly.dev"

# Test signup
print("Testing signup endpoint...")
signup_data = {
    "email": "prodtest@example.com",
    "password": "Test123Password!",
    "business_name": "Production Test Co",
    "phone": "+60123456789",
    "plan": "free"
}

try:
    response = requests.post(
        f"{BASE_URL}/api/auth/signup",
        json=signup_data,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Exception: {e}")

# Test health endpoint
print("\n\nTesting health endpoint...")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
