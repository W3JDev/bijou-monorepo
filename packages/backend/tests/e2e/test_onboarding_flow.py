"""
End-to-End Test Suite for Onboarding Flow
==========================================

Tests the complete onboarding journey:
1. Signup (create tenant)
2. Check status (qr_ready)
3. Get QR code (PNG image)
4. Attempt completion (should fail until WhatsApp connected)

Usage:
    pytest tests/e2e/test_onboarding_flow.py -v
    
Environment:
    Requires BIJOU_API_URL env var or defaults to staging
"""

import os
import time
import requests
import pytest
from typing import Dict, Any


# Test configuration
BASE_URL = os.getenv("BIJOU_API_URL", "https://bijou-staging.fly.dev")
TEST_EMAIL_PREFIX = "e2e-test"


@pytest.fixture(scope="module")
def onboarding_session() -> Dict[str, Any]:
    """
    Creates a new tenant via signup and returns session data.
    
    Returns:
        Dict containing tenant_id, onboarding_token, and signup response
    """
    timestamp = int(time.time())
    signup_payload = {
        "business_name": f"E2E Test Business {timestamp}",
        "email": f"{TEST_EMAIL_PREFIX}-{timestamp}@example.com",
        "phone": f"+60{timestamp % 1000000000}",
        "plan_tier": "free"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/onboarding/signup",
        json=signup_payload,
        timeout=10
    )
    
    assert response.status_code == 200, f"Signup failed: {response.text}"
    data = response.json()
    
    assert "tenant_id" in data, "Missing tenant_id in response"
    assert "onboarding_url" in data, "Missing onboarding_url in response"
    
    # Extract token from URL (format: https://domain/onboard/{token})
    onboarding_token = data["onboarding_url"].split("/onboard/")[-1]
    
    return {
        "tenant_id": data["tenant_id"],
        "onboarding_token": onboarding_token,
        "signup_response": data,
        "email": signup_payload["email"],
        "business_name": signup_payload["business_name"]
    }


class TestOnboardingFlow:
    """E2E test suite for onboarding flow"""
    
    def test_01_signup_creates_tenant(self, onboarding_session):
        """
        Test Step 1: Signup creates tenant successfully
        
        Verifies:
        - HTTP 200 response
        - tenant_id is UUID format
        - onboarding_token is returned
        - onboarding_url contains token
        """
        data = onboarding_session["signup_response"]
        
        # Verify required fields
        assert "tenant_id" in data
        assert "onboarding_url" in data
        
        # Verify UUID format (36 chars with hyphens)
        assert len(data["tenant_id"]) == 36
        assert data["tenant_id"].count("-") == 4
        
        # Verify token in URL
        assert onboarding_session["onboarding_token"] in data["onboarding_url"]
        
        print(f"\n✅ Tenant created: {data['tenant_id']}")
        print(f"✅ Onboarding URL: {data['onboarding_url']}")
    
    
    def test_02_status_returns_qr_ready(self, onboarding_session):
        """
        Test Step 2: Status endpoint returns correct onboarding state
        
        Verifies:
        - HTTP 200 response
        - status is 'qr_ready'
        - whatsapp_connected is False
        - onboarding_completed is False
        - tenant_id matches signup
        """
        token = onboarding_session["onboarding_token"]
        
        response = requests.get(
            f"{BASE_URL}/api/onboarding/status/{token}",
            timeout=10
        )
        
        assert response.status_code == 200, f"Status check failed: {response.text}"
        data = response.json()
        
        # Verify state
        assert data["status"] == "qr_ready", f"Expected qr_ready, got {data['status']}"
        assert data["whatsapp_connected"] is False
        assert data["onboarding_completed"] is False
        assert data["tenant_id"] == onboarding_session["tenant_id"]
        
        # Verify business info
        assert data["business_name"] == onboarding_session["business_name"]
        assert data["email"] == onboarding_session["email"]
        
        print(f"\n✅ Status: {data['status']}")
        print(f"✅ WhatsApp connected: {data['whatsapp_connected']}")
    
    
    def test_03_qr_code_returns_valid_png(self, onboarding_session):
        """
        Test Step 3: QR code endpoint returns valid PNG image
        
        Verifies:
        - HTTP 200 response
        - Content-Type is image/png
        - Content length > 1000 bytes (valid QR code)
        - File starts with PNG magic bytes (89 50 4E 47)
        """
        token = onboarding_session["onboarding_token"]
        
        response = requests.get(
            f"{BASE_URL}/api/onboarding/qr/{token}",
            timeout=10
        )
        
        assert response.status_code == 200, f"QR code fetch failed: {response.status_code}"
        
        # Verify headers
        assert response.headers["Content-Type"] == "image/png"
        
        # Verify content
        content = response.content
        assert len(content) > 1000, f"QR code too small: {len(content)} bytes"
        
        # Verify PNG magic bytes
        png_header = content[:8]
        expected_header = b'\x89PNG\r\n\x1a\n'
        assert png_header == expected_header, f"Invalid PNG header: {png_header.hex()}"
        
        print(f"\n✅ QR code size: {len(content)} bytes")
        print(f"✅ Content-Type: {response.headers['Content-Type']}")
    
    
    def test_04_complete_fails_without_whatsapp(self, onboarding_session):
        """
        Test Step 4: Complete endpoint rejects when WhatsApp not connected
        
        Verifies:
        - HTTP 400 response (bad request)
        - Error message mentions WhatsApp not connected
        - Cannot complete onboarding without scanning QR
        """
        token = onboarding_session["onboarding_token"]
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/complete/{token}",
            json={"whatsapp_jid": "60123456789@s.whatsapp.net"},
            timeout=10
        )
        
        # Should fail with 400
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        # Verify error message
        data = response.json()
        assert "detail" in data
        assert "WhatsApp not connected" in data["detail"] or "scan QR" in data["detail"].lower()
        
        print(f"\n✅ Correctly rejected completion (WhatsApp not connected)")
        print(f"✅ Error message: {data['detail']}")


class TestOnboardingEdgeCases:
    """Test error handling and edge cases"""
    
    def test_status_with_invalid_token_returns_404(self):
        """Verify invalid token returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/status/invalid-token-12345",
            timeout=10
        )
        
        assert response.status_code == 404
        print(f"\n✅ Invalid token correctly returns 404")
    
    
    def test_qr_with_invalid_token_returns_404(self):
        """Verify QR endpoint with invalid token returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/qr/invalid-token-12345",
            timeout=10
        )
        
        assert response.status_code == 404
        print(f"\n✅ Invalid QR token correctly returns 404")
    
    
    def test_signup_with_missing_fields_returns_422(self):
        """Verify signup validation rejects missing required fields"""
        response = requests.post(
            f"{BASE_URL}/api/onboarding/signup",
            json={"business_name": "Incomplete Data"},  # Missing email, phone
            timeout=10
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"\n✅ Missing fields correctly returns 422 (validation error)")


# Pytest configuration
def pytest_configure(config):
    """Add custom markers"""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test requiring live API"
    )


if __name__ == "__main__":
    """Run tests directly with pytest"""
    pytest.main([__file__, "-v", "--tb=short"])
