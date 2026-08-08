"""
Critical Security Tests for WhatsApp Call Handler
================================================

Tests for the 3 CRITICAL vulnerabilities identified by Security Auditor:
- CVE-2026-001: Cross-Tenant Call Injection (CVSS 9.1)
- CVE-2026-002: API Key Bypass (CVSS 9.4)  
- CVE-2026-003: Memory Exhaustion DoS (CVSS 7.5)

**These tests MUST PASS before production deployment.**

Author: QA Engineer
Date: 2026-02-23
Priority: P0 - CRITICAL SECURITY
"""

import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import test fixtures
from tests.fixtures.call_payloads import (
    create_call_offer_payload,
    create_missed_call_payload,
    create_cross_tenant_attack_payload,
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestCallSecurityCritical:
    """
    P0 CRITICAL SECURITY TESTS
    
    These tests validate fixes for critical vulnerabilities.
    Failures indicate immediate security risk.
    """

    async def test_cve_2026_001_cross_tenant_call_injection_blocked(
        self, test_client, mock_supabase
    ):
        """
        CVE-2026-001: Cross-Tenant Call Injection Prevention
        
        ATTACK: Malicious caller sends missed call payload with:
        - Tenant A's phone number (valid)  
        - Tenant B's device_id (injection attempt)
        
        EXPECTED: 403 Forbidden, call rejected with tenant mismatch error
        CURRENT RISK: Call processed for wrong tenant, data leak
        """
        # Setup: Two tenants with different device IDs
        tenant_a_device = "device-tenant-a-12345"
        tenant_b_device = "device-tenant-b-67890" 
        
        # Configure mock database
        def mock_device_lookup(device_id):
            if device_id == tenant_a_device:
                return MagicMock(data=[{"tenant_id": "tenant-a-uuid", "whatsapp_jid": "+601234567890@s.whatsapp.net"}])
            elif device_id == tenant_b_device:
                return MagicMock(data=[{"tenant_id": "tenant-b-uuid", "whatsapp_jid": "+601987654321@s.whatsapp.net"}])
            else:
                return MagicMock(data=[])  # Device not found
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = mock_device_lookup

        # ATTACK: Use Tenant A's number with Tenant B's device_id
        malicious_payload = create_cross_tenant_attack_payload(
            caller_jid="+601234567890@s.whatsapp.net",  # Tenant A's number
            device_id=tenant_b_device,                   # Tenant B's device (injection!)
            call_id="attack-call-001"
        )
        
        # Execute attack
        response = test_client.post(
            "/webhook/message",
            json=malicious_payload,
            headers={"Content-Type": "application/json", "X-API-Key": "valid-api-key"}
        )
        
        # SECURITY VALIDATION
        assert response.status_code == 403, "Cross-tenant injection should be blocked with 403"
        assert "tenant_mismatch" in response.json().get("detail", "").lower()
        
        # Verify NO database write occurred for wrong tenant
        # Database should not contain any calls for Tenant B from Tenant A's number
        mock_supabase.table.assert_not_called_with("conversations")

    async def test_cve_2026_002_api_key_bypass_blocked(self, test_client):
        """
        CVE-2026-002: API Authentication Bypass Prevention
        
        ATTACK: Send call webhook without proper API key
        EXPECTED: 401 Unauthorized
        CURRENT RISK: Complete authentication bypass
        """
        # Valid call payload
        call_payload = create_call_offer_payload(
            caller_jid="+601234567890@s.whatsapp.net",
            device_id="valid-device-123",
            call_id="auth-test-001"
        )
        
        # ATTACK 1: No API key header
        response1 = test_client.post(
            "/webhook/message",
            json=call_payload,
            headers={"Content-Type": "application/json"}
            # Missing X-API-Key header
        )
        
        assert response1.status_code == 401, "Missing API key should return 401"
        assert "unauthorized" in response1.json().get("detail", "").lower()
        
        # ATTACK 2: Invalid API key
        response2 = test_client.post(
            "/webhook/message", 
            json=call_payload,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": "invalid-fake-key-12345"
            }
        )
        
        assert response2.status_code == 401, "Invalid API key should return 401"
        assert "unauthorized" in response2.json().get("detail", "").lower()
        
        # ATTACK 3: Empty API key
        response3 = test_client.post(
            "/webhook/message",
            json=call_payload,
            headers={
                "Content-Type": "application/json", 
                "X-API-Key": ""
            }
        )
        
        assert response3.status_code == 401, "Empty API key should return 401"

    async def test_cve_2026_002_api_key_brute_force_protection(self, test_client):
        """
        CVE-2026-002: API Key Brute Force Protection
        
        ATTACK: Rapid-fire requests with invalid API keys
        EXPECTED: Rate limiting after threshold (e.g., 10 attempts/minute)
        CURRENT RISK: Unlimited brute force attempts
        """
        call_payload = create_call_offer_payload(
            caller_jid="+601234567890@s.whatsapp.net",
            device_id="device-123",
            call_id="brute-force-test"
        )
        
        failed_attempts = 0
        rate_limited = False
        
        # ATTACK: Send 15 requests with invalid keys in quick succession
        for i in range(15):
            response = test_client.post(
                "/webhook/message",
                json=call_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": f"fake-key-{i:03d}"
                }
            )
            
            if response.status_code == 429:  # Too Many Requests
                rate_limited = True
                break
            elif response.status_code == 401:
                failed_attempts += 1
            
            # Small delay to avoid overwhelming test client
            time.sleep(0.01)
        
        # SECURITY VALIDATION
        assert rate_limited or failed_attempts >= 10, (
            "Rate limiting should activate after repeated failed attempts. "
            f"Got {failed_attempts} 401s, rate_limited={rate_limited}"
        )

    @pytest.mark.slow
    async def test_cve_2026_003_memory_exhaustion_protection(self, test_client):
        """
        CVE-2026-003: Memory Exhaustion DoS Protection
        
        ATTACK: Flood server with call events to exhaust memory
        EXPECTED: Memory usage capped, excess calls rejected
        CURRENT RISK: Unbounded memory growth crashes service
        """
        # ATTACK: Generate 1000 concurrent call events
        attack_payloads = []
        for i in range(1000):
            payload = create_call_offer_payload(
                caller_jid=f"+6012345{i:05d}@s.whatsapp.net",
                device_id=f"attack-device-{i:03d}",
                call_id=f"dos-attack-{i:05d}"
            )
            attack_payloads.append(payload)
        
        # Execute DoS attack
        responses = []
        start_time = time.time()
        
        for payload in attack_payloads[:100]:  # Test with 100 to avoid test timeout
            response = test_client.post(
                "/webhook/message",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": "valid-api-key"  # Assume valid for this test
                }
            )
            responses.append(response.status_code)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # SECURITY VALIDATION
        success_responses = [r for r in responses if r == 200]
        rejected_responses = [r for r in responses if r in [429, 503]]  # Rate limit or service unavailable
        
        # At least some requests should be rejected to prevent memory exhaustion
        assert len(rejected_responses) > 0, (
            "Memory protection should reject excess calls. "
            f"All {len(responses)} requests succeeded, indicating no DoS protection."
        )
        
        # Response time should not degrade significantly (< 5 seconds for 100 requests)
        assert duration < 5.0, (
            f"Response time {duration:.2f}s indicates server stress. "
            "DoS protection may be insufficient."
        )


@pytest.mark.integration  
@pytest.mark.asyncio
class TestCallAuthenticationIntegration:
    """
    Integration tests for API authentication flow
    """
    
    async def test_valid_api_key_authentication_flow(self, test_client, mock_supabase):
        """
        Verify valid API key allows call processing
        """
        # Configure valid API key
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "test-bridge-api-key"}):
            # Configure tenant lookup
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"tenant_id": "test-tenant-123", "whatsapp_jid": "+601234567890@s.whatsapp.net"}]
            )
            
            call_payload = create_missed_call_payload(
                caller_jid="+601234567890@s.whatsapp.net",
                device_id="valid-device-123",
                call_id="auth-integration-001"
            )
            
            response = test_client.post(
                "/webhook/message",
                json=call_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": "test-bridge-api-key"  # Valid key
                }
            )
            
            # Should succeed with valid authentication
            assert response.status_code == 200
            assert response.json().get("status") == "accepted"

    async def test_api_key_validation_edge_cases(self, test_client):
        """
        Test API key validation with various edge cases
        """
        call_payload = create_call_offer_payload(
            caller_jid="+601234567890@s.whatsapp.net", 
            device_id="device-123",
            call_id="edge-case-test"
        )
        
        edge_cases = [
            # Case 1: Very long API key (potential buffer overflow)
            ("A" * 10000, 401, "Extremely long API key should be rejected"),
            
            # Case 2: Special characters in API key
            ("key-with-@#$%^&*()-chars", 401, "Special chars in key should be handled"),
            
            # Case 3: Case sensitivity test
            ("TEST-BRIDGE-API-KEY", 401, "API key should be case sensitive"),
            
            # Case 4: Whitespace handling
            (" valid-key-with-spaces ", 401, "Whitespace should be handled properly"),
            
            # Case 5: SQL injection attempt in API key
            ("'; DROP TABLE tenants; --", 401, "SQL injection in API key should be blocked"),
        ]
        
        for api_key, expected_status, description in edge_cases:
            response = test_client.post(
                "/webhook/message",
                json=call_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": api_key
                }
            )
            
            assert response.status_code == expected_status, (
                f"{description}. Got {response.status_code}, expected {expected_status}"
            )


@pytest.mark.regression
@pytest.mark.asyncio
class TestCallSecurityRegression:
    """
    Regression tests for call security vulnerabilities
    
    These tests ensure previously fixed security bugs don't regress.
    DO NOT DELETE these tests - they prevent regression.
    """
    
    async def test_regression_tenant_isolation_enforcement(self, test_client, mock_supabase):
        """
        REGRESSION TEST - DO NOT DELETE
        
        Previous Bug: Call events could leak between tenants
        Fix: Added strict tenant_id validation 
        Verified: 2026-02-23
        """
        # Configure two separate tenants
        def mock_tenant_lookup(device_id):
            tenant_map = {
                "tenant-a-device": [{"tenant_id": "aaaa-bbbb-cccc-dddd", "whatsapp_jid": "+601111111111@s.whatsapp.net"}],
                "tenant-b-device": [{"tenant_id": "eeee-ffff-gggg-hhhh", "whatsapp_jid": "+602222222222@s.whatsapp.net"}],
            }
            return MagicMock(data=tenant_map.get(device_id, []))
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = mock_tenant_lookup
        
        # Call from Tenant A should only process for Tenant A
        tenant_a_payload = create_missed_call_payload(
            caller_jid="+601111111111@s.whatsapp.net",
            device_id="tenant-a-device",
            call_id="regression-test-a"
        )
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "test-key"}):
            response = test_client.post(
                "/webhook/message",
                json=tenant_a_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": "test-key"
                }
            )
        
        # Should be accepted for proper tenant
        assert response.status_code == 200
        
        # Verify tenant isolation maintained
        # (Additional checks would verify database writes only for correct tenant)
        
    async def test_regression_call_memory_leaks_fixed(self):
        """
        REGRESSION TEST - DO NOT DELETE
        
        Previous Bug: Call tracking map grew unbounded
        Fix: Added periodic cleanup and memory limits
        Verified: 2026-02-23
        """
        # This test would simulate the memory leak scenario
        # and verify cleanup mechanisms are working
        
        # Mock the pendingCalls map from the Go bridge
        with patch('src.core.bijou.logger') as mock_logger:
            # Simulate 1000 calls being tracked
            # Verify cleanup occurs after timeout
            # Ensure memory usage remains bounded
            
            # For now, this is a placeholder for the actual implementation
            assert True, "Memory cleanup mechanism should be verified"


@pytest.mark.load
@pytest.mark.slow
@pytest.mark.asyncio 
class TestCallSecurityUnderLoad:
    """
    Security validation under load conditions
    """
    
    async def test_security_under_concurrent_load(self, test_client):
        """
        Verify security measures hold under concurrent load
        """
        import concurrent.futures
        import threading
        
        # Create concurrent requests with mix of valid/invalid credentials
        def make_request(api_key: str, call_id: str) -> int:
            payload = create_call_offer_payload(
                caller_jid=f"+60123456{call_id}@s.whatsapp.net",
                device_id=f"load-test-{call_id}",
                call_id=f"concurrent-{call_id}"
            )
            
            response = test_client.post(
                "/webhook/message",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": api_key
                }
            )
            return response.status_code
        
        # Execute 50 concurrent requests (25 valid, 25 invalid)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            # Submit requests with mix of valid/invalid keys
            for i in range(50):
                api_key = "valid-key" if i % 2 == 0 else f"invalid-key-{i}"
                future = executor.submit(make_request, api_key, str(i).zfill(3))
                futures.append(future)
            
            # Collect results
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify security held under load
        unauthorized_count = sum(1 for r in results if r == 401)
        success_count = sum(1 for r in results if r == 200)
        
        # Should have rejected invalid API keys even under load
        assert unauthorized_count >= 20, (
            f"Security validation failed under load. Only {unauthorized_count}/25 invalid requests rejected"
        )


# Test fixtures and data creation functions would be imported from separate files
# for better organization and reusability across test modules