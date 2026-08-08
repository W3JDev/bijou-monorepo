import requests
import os
import sys

# Configuration
BASE_URL = os.getenv("API_URL", "https://bijou-staging.fly.dev")
TENANT_ID = "00000000-0000-0000-0000-000000000001"  # W3J Tenant
EXISTING_JID = "60123456789@s.whatsapp.net"
NON_EXISTENT_JID = "99999999999@s.whatsapp.net"
AGENT_NAME = "TestVerifier"

def test_takeover():
    print(f"\n--- Testing Takeover Endpoint ---")
    url = f"{BASE_URL}/api/dashboard/takeover"
    headers = {"X-Tenant-ID": TENANT_ID}

    # Test 1: Existing Customer (Should succeed - 200)
    print(f"Test 1: Existing Customer ({EXISTING_JID}) -> Expect 200")
    payload = {"customer_jid": EXISTING_JID, "agent_name": AGENT_NAME}
    try:
        resp = requests.post(url, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        if resp.status_code == 200:
            print("✅ PASS: Correctly allowed takeover for existing customer")
        else:
            print("❌ FAIL: Expected 200, got", resp.status_code)
    except Exception as e:
        print(f"❌ FAIL: Exception {e}")

    # Test 2: Non-Existent Customer (Should fail - 403)
    print(f"\nTest 2: Non-Existent Customer ({NON_EXISTENT_JID}) -> Expect 403")
    payload = {"customer_jid": NON_EXISTENT_JID, "agent_name": AGENT_NAME}
    try:
        resp = requests.post(url, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        if resp.status_code == 403:
            print("✅ PASS: Correctly denied takeover for non-existent customer")
        else:
            print("❌ FAIL: Expected 403, got", resp.status_code)
    except Exception as e:
        print(f"❌ FAIL: Exception {e}")

def test_return_to_ai():
    print(f"\n--- Testing Return-to-AI Endpoint ---")
    headers = {"X-Tenant-ID": TENANT_ID}

    # Test 1: Existing Customer (Should succeed - 200)
    print(f"Test 1: Existing Customer ({EXISTING_JID}) -> Expect 200")
    url = f"{BASE_URL}/api/dashboard/return-to-ai/{EXISTING_JID}?agent_name={AGENT_NAME}"
    try:
        resp = requests.post(url, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        if resp.status_code == 200:
            print("✅ PASS: Correctly returned to AI for existing customer")
        else:
            print("❌ FAIL: Expected 200, got", resp.status_code)
    except Exception as e:
        print(f"❌ FAIL: Exception {e}")

    # Test 2: Non-Existent Customer (Should fail - 403)
    print(f"\nTest 2: Non-Existent Customer ({NON_EXISTENT_JID}) -> Expect 403")
    url = f"{BASE_URL}/api/dashboard/return-to-ai/{NON_EXISTENT_JID}?agent_name={AGENT_NAME}"
    try:
        resp = requests.post(url, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        if resp.status_code == 403:
            print("✅ PASS: Correctly denied return-to-ai for non-existent customer")
        else:
            print("❌ FAIL: Expected 403, got", resp.status_code)
    except Exception as e:
        print(f"❌ FAIL: Exception {e}")

if __name__ == "__main__":
    print(f"Testing against: {BASE_URL}")
    test_takeover()
    test_return_to_ai()
