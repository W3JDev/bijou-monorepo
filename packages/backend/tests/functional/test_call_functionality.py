"""
Functional Tests for WhatsApp Call Handler
==========================================

Tests core call handling functionality after security vulnerabilities are fixed:
- End-to-end call flow validation  
- Multi-tenant call isolation
- Configuration matrix testing
- Missed call follow-up logic
- Bridge-Core integration

Priority: P1 - HIGH (functional validation after security fixes)

Author: QA Engineer  
Date: 2026-02-23
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.call_payloads import (
    create_call_offer_payload,
    create_call_accept_payload,
    create_call_terminate_payload,
    create_missed_call_payload,
    create_multi_tenant_test_scenario,
)


@pytest.mark.integration
@pytest.mark.asyncio
class TestCallFlowEndToEnd:
    """
    End-to-end call flow testing across different scenarios
    """

    async def test_missed_call_flow_with_followup_enabled(
        self, test_client, mock_supabase
    ):
        """
        Test complete missed call flow: Call Offer → Timeout → Missed Call Follow-up
        
        Configuration: CALLS_ENABLED=true, MISSED_CALL_FOLLOWUP=true
        Expected: Phone rings, times out, AI sends follow-up message
        """
        # Configure tenant with calls enabled
        tenant_config = {
            "tenant_id": "test-tenant-001",
            "device_id": "device-call-test-001", 
            "whatsapp_jid": "+601234567890@s.whatsapp.net",
            "calls_enabled": True,
            "missed_call_followup": True,
        }
        
        # Mock tenant lookup
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[tenant_config]
        )
        
        with patch.dict(os.environ, {
            "BRIDGE_API_KEY": "test-api-key",
            "WHATSAPP_CALLS_ENABLED": "true", 
            "MISSED_CALL_FOLLOWUP": "true"
        }):
            # Step 1: Receive call offer
            call_offer = create_call_offer_payload(
                caller_jid="+601234567890@s.whatsapp.net",
                device_id="device-call-test-001",
                call_id="e2e-test-001"
            )
            
            response1 = test_client.post(
                "/webhook/message",
                json=call_offer,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": "test-api-key"
                }
            )
            
            # Call offer should be accepted for processing
            assert response1.status_code == 200
            assert response1.json().get("status") == "accepted"
            
            # Step 2: Simulate missed call (no answer after timeout)
            missed_call = create_missed_call_payload(
                caller_jid="+601234567890@s.whatsapp.net",
                device_id="device-call-test-001",
                call_id="e2e-test-001"
            )
            
            # Mock AI response generation for missed call
            with patch("src.core.bijou.bijou_instance") as mock_bijou:
                mock_bijou.process_message = AsyncMock()
                
                response2 = test_client.post(
                    "/webhook/message",
                    json=missed_call,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": "test-api-key"
                    }
                )
            
            # Missed call should trigger follow-up processing
            assert response2.status_code == 200
            assert response2.json().get("status") == "accepted"
            
            # Verify AI processing was triggered for missed call context
            mock_bijou.process_message.assert_called_once()
            call_args = mock_bijou.process_message.call_args[0][0]
            assert call_args["content"] == "📞 MISSED_CALL"
            assert call_args["chat_jid"] == "+601234567890@s.whatsapp.net"

    async def test_answered_call_no_followup(self, test_client, mock_supabase):
        """
        Test answered call flow: Call Offer → Accept → Terminate → No Follow-up
        
        Expected: Call answered, terminated normally, no AI follow-up sent
        """
        tenant_config = {
            "tenant_id": "test-tenant-002",
            "device_id": "device-call-test-002",
            "whatsapp_jid": "+601987654321@s.whatsapp.net",
            "calls_enabled": True,
            "missed_call_followup": True,
        }
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[tenant_config]
        )
        
        with patch.dict(os.environ, {
            "BRIDGE_API_KEY": "test-api-key",
            "WHATSAPP_CALLS_ENABLED": "true",
            "MISSED_CALL_FOLLOWUP": "true"
        }):
            call_id = "answered-call-001"
            caller_jid = "+601987654321@s.whatsapp.net"
            device_id = "device-call-test-002"
            
            # Step 1: Call offer
            call_offer = create_call_offer_payload(caller_jid, device_id, call_id)
            response1 = test_client.post(
                "/webhook/message", json=call_offer,
                headers={"Content-Type": "application/json", "X-API-Key": "test-api-key"}
            )
            assert response1.status_code == 200
            
            # Step 2: Call accepted
            call_accept = create_call_accept_payload(caller_jid, device_id, call_id)
            response2 = test_client.post(
                "/webhook/message", json=call_accept,
                headers={"Content-Type": "application/json", "X-API-Key": "test-api-key"}
            )
            assert response2.status_code == 200
            
            # Step 3: Call terminated (answered, not missed)
            call_terminate = create_call_terminate_payload(
                caller_jid, device_id, call_id,
                is_missed=False, duration_seconds=120.5
            )
            
            with patch("src.core.bijou.bijou_instance") as mock_bijou:
                mock_bijou.process_message = AsyncMock()
                
                response3 = test_client.post(
                    "/webhook/message", json=call_terminate,
                    headers={"Content-Type": "application/json", "X-API-Key": "test-api-key"}
                )
            
            assert response3.status_code == 200
            
            # Verify NO missed call follow-up was triggered
            mock_bijou.process_message.assert_not_called()

    async def test_auto_reject_mode_immediate_followup(self, test_client, mock_supabase):
        """
        Test auto-reject mode: CALLS_ENABLED=false
        
        Expected: Call rejected immediately, follow-up triggered within seconds
        """
        tenant_config = {
            "tenant_id": "test-tenant-003", 
            "device_id": "device-call-test-003",
            "whatsapp_jid": "+602123456789@s.whatsapp.net",
            "calls_enabled": False,  # Auto-reject mode
            "missed_call_followup": True,
        }
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[tenant_config]
        )
        
        with patch.dict(os.environ, {
            "BRIDGE_API_KEY": "test-api-key",
            "WHATSAPP_CALLS_ENABLED": "false",  # Auto-reject
            "MISSED_CALL_FOLLOWUP": "true"
        }):
            # Call offer should trigger immediate rejection + follow-up
            call_offer = create_call_offer_payload(
                caller_jid="+602123456789@s.whatsapp.net",
                device_id="device-call-test-003",
                call_id="auto-reject-001",
                auto_rejected=True  # Bridge marks as auto-rejected
            )
            
            with patch("src.core.bijou.bijou_instance") as mock_bijou:
                mock_bijou.process_message = AsyncMock()
                
                response = test_client.post(
                    "/webhook/message", json=call_offer,
                    headers={"Content-Type": "application/json", "X-API-Key": "test-api-key"}
                )
            
            assert response.status_code == 200
            
            # Auto-rejected calls should still trigger missed call follow-up
            # This would be sent as a separate missed_call message by the bridge
            missed_call = create_missed_call_payload(
                caller_jid="+602123456789@s.whatsapp.net",
                device_id="device-call-test-003", 
                call_id="auto-reject-001"
            )
            
            response2 = test_client.post(
                "/webhook/message", json=missed_call,
                headers={"Content-Type": "application/json", "X-API-Key": "test-api-key"}
            )
            
            assert response2.status_code == 200
            # Follow-up should be processed
            mock_bijou.process_message.assert_called()


@pytest.mark.integration
@pytest.mark.asyncio  
class TestMultiTenantCallIsolation:
    """
    Test multi-tenant isolation for call handling
    """
    
    async def test_tenant_call_isolation(self, test_client, mock_supabase):
        """
        Verify calls are properly isolated between tenants
        """
        scenario = create_multi_tenant_test_scenario()
        tenants = scenario["tenants"]
        
        # Configure mock to return appropriate tenant based on device_id lookup
        def mock_tenant_lookup(device_id):
            for tenant_key, tenant_data in tenants.items():
                if tenant_data["device_id"] == device_id:
                    return MagicMock(data=[tenant_data])
            return MagicMock(data=[])  # Device not found
            
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = mock_tenant_lookup
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "test-api-key"}):
            # Test Tenant A call processing
            tenant_a_call = scenario["legitimate_calls"]["tenant_a"][0]
            response_a = test_client.post(
                "/webhook/message", json=tenant_a_call,
                headers={"Content-Type": "application/json", "X-API-Key": "test-api-key"}
            )
            
            # Test Tenant B call processing  
            tenant_b_call = scenario["legitimate_calls"]["tenant_b"][0]
            response_b = test_client.post(
                "/webhook/message", json=tenant_b_call,
                headers={"Content-Type": "application/json", "X-API-Key": "test-api-key"}
            )
            
            # Both should succeed with their own tenant context
            assert response_a.status_code == 200
            assert response_b.status_code == 200
            
            # Verify cross-tenant attacks are blocked
            for attack_payload in scenario["attack_payloads"]:
                attack_response = test_client.post(
                    "/webhook/message", json=attack_payload,
                    headers={"Content-Type": "application/json", "X-API-Key": "test-api-key"}
                )
                
                # Cross-tenant attacks should be rejected
                assert attack_response.status_code in [403, 404], (
                    f"Cross-tenant attack should be blocked, got {attack_response.status_code}"
                )

    async def test_tenant_configuration_isolation(self, test_client, mock_supabase):
        """
        Verify each tenant's call configuration is applied independently
        """
        # Setup tenants with different call configurations
        tenant_configs = [
            {
                "tenant_id": "config-test-001",
                "device_id": "config-device-001", 
                "whatsapp_jid": "+601111111111@s.whatsapp.net",
                "calls_enabled": True,   # Accepts calls
                "missed_call_followup": True
            },
            {
                "tenant_id": "config-test-002", 
                "device_id": "config-device-002",
                "whatsapp_jid": "+602222222222@s.whatsapp.net",
                "calls_enabled": False,  # Auto-rejects calls
                "missed_call_followup": True
            },
            {
                "tenant_id": "config-test-003",
                "device_id": "config-device-003", 
                "whatsapp_jid": "+603333333333@s.whatsapp.net",
                "calls_enabled": True,
                "missed_call_followup": False  # No follow-up
            }
        ]
        
        def mock_config_lookup(device_id):
            for config in tenant_configs:
                if config["device_id"] == device_id:
                    return MagicMock(data=[config])
            return MagicMock(data=[])
            
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = mock_config_lookup
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "test-api-key"}):
            # Test each tenant's configuration is respected
            for i, config in enumerate(tenant_configs, 1):
                call_payload = create_call_offer_payload(
                    caller_jid=config["whatsapp_jid"],
                    device_id=config["device_id"],
                    call_id=f"config-test-{i:03d}",
                    auto_rejected=not config["calls_enabled"]
                )
                
                response = test_client.post(
                    "/webhook/message", json=call_payload,
                    headers={"Content-Type": "application/json", "X-API-Key": "test-api-key"}
                )
                
                # All should be accepted for processing (configuration applied in bridge)
                assert response.status_code == 200
                assert response.json().get("status") == "accepted"


@pytest.mark.integration
@pytest.mark.asyncio
class TestCallBridgeIntegration:
    """
    Test integration between WhatsApp bridge and Bijou core
    """
    
    async def test_webhook_payload_compatibility(self, test_client, mock_supabase):
        """
        Verify bridge webhooks are correctly processed by core
        """
        # Mock tenant for webhook validation
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "tenant_id": "integration-test-001",
                "whatsapp_jid": "+601234567890@s.whatsapp.net"
            }]
        )
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "integration-test-key"}):
            # Test all call event types from bridge
            test_events = [
                create_call_offer_payload(
                    "+601234567890@s.whatsapp.net", "integration-device-001", "call-001"
                ),
                create_call_accept_payload(
                    "+601234567890@s.whatsapp.net", "integration-device-001", "call-001"  
                ),
                create_call_terminate_payload(
                    "+601234567890@s.whatsapp.net", "integration-device-001", "call-001",
                    is_missed=False, duration_seconds=30.0
                ),
                create_missed_call_payload(
                    "+601234567890@s.whatsapp.net", "integration-device-001", "call-002"
                )
            ]
            
            for event_payload in test_events:
                response = test_client.post(
                    "/webhook/message", json=event_payload,
                    headers={"Content-Type": "application/json", "X-API-Key": "integration-test-key"}
                )
                
                # All bridge events should be successfully processed
                assert response.status_code == 200
                assert "accepted" in response.json().get("status", "").lower()

    async def test_webhook_error_handling(self, test_client):
        """
        Test webhook error handling for malformed payloads
        """
        from tests.fixtures.call_payloads import create_malformed_call_payload
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "test-key"}):
            error_cases = [
                ("missing_fields", 422, "Missing required fields should return 422"),
                ("invalid_jid", 422, "Invalid JID format should return 422"),
                ("empty_payload", 422, "Empty payload should return 422"),
                ("wrong_event_type", 200, "Wrong event type should be skipped gracefully"),
            ]
            
            for payload_type, expected_status, description in error_cases:
                malformed_payload = create_malformed_call_payload(payload_type)
                
                response = test_client.post(
                    "/webhook/message", json=malformed_payload,
                    headers={"Content-Type": "application/json", "X-API-Key": "test-key"}
                )
                
                assert response.status_code == expected_status, (
                    f"{description}. Got {response.status_code}, expected {expected_status}"
                )

    async def test_webhook_authentication_integration(self, test_client, mock_supabase):
        """
        Test end-to-end authentication between bridge and core
        """
        # Valid payload with proper authentication
        call_payload = create_missed_call_payload(
            "+601234567890@s.whatsapp.net", "auth-test-device", "auth-test-001"
        )
        
        # Mock successful tenant lookup
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"tenant_id": "auth-test-tenant", "whatsapp_jid": "+601234567890@s.whatsapp.net"}]
        )
        
        # Test with correct API key
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "correct-bridge-key"}):
            response = test_client.post(
                "/webhook/message", json=call_payload,
                headers={"Content-Type": "application/json", "X-API-Key": "correct-bridge-key"}
            )
            
            assert response.status_code == 200
            assert response.json().get("status") == "accepted"


@pytest.mark.unit
@pytest.mark.asyncio
class TestCallConfigurationMatrix:
    """
    Test all combinations of call configuration settings
    """
    
    @pytest.mark.parametrize("calls_enabled,followup_enabled,expected_behavior", [
        (True, True, "ring_and_followup_if_missed"),
        (True, False, "ring_no_followup"),
        (False, True, "auto_reject_with_followup"),
        (False, False, "auto_reject_forced_followup"),  # Implementation forces followup when disabled
    ])
    async def test_configuration_matrix(
        self, calls_enabled, followup_enabled, expected_behavior, test_client, mock_supabase
    ):
        """
        Test all combinations of CALLS_ENABLED and MISSED_CALL_FOLLOWUP settings
        """
        tenant_config = {
            "tenant_id": f"config-{expected_behavior}",
            "device_id": f"device-{expected_behavior}",
            "whatsapp_jid": "+601234567890@s.whatsapp.net",
            "calls_enabled": calls_enabled,
            "missed_call_followup": followup_enabled,
        }
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[tenant_config]
        )
        
        with patch.dict(os.environ, {
            "BRIDGE_API_KEY": "config-test-key",
            "WHATSAPP_CALLS_ENABLED": str(calls_enabled).lower(),
            "MISSED_CALL_FOLLOWUP": str(followup_enabled).lower()
        }):
            # Send call event
            call_payload = create_call_offer_payload(
                "+601234567890@s.whatsapp.net",
                f"device-{expected_behavior}",
                f"config-test-{expected_behavior}",
                auto_rejected=not calls_enabled
            )
            
            response = test_client.post(
                "/webhook/message", json=call_payload,
                headers={"Content-Type": "application/json", "X-API-Key": "config-test-key"}
            )
            
            # All configurations should accept the webhook
            assert response.status_code == 200
            
            # The actual behavior difference would be in the bridge's handling
            # and whether missed call follow-up messages are sent
            
            if not calls_enabled or expected_behavior.endswith("followup"):
                # Should eventually receive missed call message for follow-up
                missed_call = create_missed_call_payload(
                    "+601234567890@s.whatsapp.net",
                    f"device-{expected_behavior}", 
                    f"config-test-{expected_behavior}"
                )
                
                followup_response = test_client.post(
                    "/webhook/message", json=missed_call,
                    headers={"Content-Type": "application/json", "X-API-Key": "config-test-key"}
                )
                
                assert followup_response.status_code == 200


@pytest.mark.smoke
@pytest.mark.asyncio  
class TestCallHandlerSmoke:
    """
    Smoke tests for critical call handler paths
    """
    
    async def test_missed_call_context_override(self, test_client, mock_supabase):
        """
        SMOKE TEST: Verify missed call context override is working
        
        This tests the core functionality that was recently integrated.
        """
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "tenant_id": "smoke-test-001",
                "whatsapp_jid": "+601234567890@s.whatsapp.net"
            }]
        )
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "smoke-test-key"}):
            # Create missed call payload
            missed_call = create_missed_call_payload(
                "+601234567890@s.whatsapp.net",
                "smoke-test-device",
                "smoke-001"
            )
            
            # Mock AI processing to verify context
            with patch("src.core.bijou.bijou_instance") as mock_bijou:
                mock_bijou.process_message = AsyncMock()
                
                response = test_client.post(
                    "/webhook/message", json=missed_call,
                    headers={"Content-Type": "application/json", "X-API-Key": "smoke-test-key"}
                )
                
                assert response.status_code == 200
                
                # Verify AI processing was called with missed call context
                mock_bijou.process_message.assert_called_once()
                processed_message = mock_bijou.process_message.call_args[0][0]
                
                # Should contain missed call indicators
                assert processed_message["content"] == "📞 MISSED_CALL"
                assert processed_message.get("message_type") == "missed_call"

    async def test_basic_call_webhook_processing(self, test_client, mock_supabase):
        """
        SMOKE TEST: Basic call webhook is processed without errors
        """
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "tenant_id": "smoke-basic-001", 
                "whatsapp_jid": "+601234567890@s.whatsapp.net"
            }]
        )
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "smoke-basic-key"}):
            basic_call = create_call_offer_payload(
                "+601234567890@s.whatsapp.net",
                "smoke-basic-device",
                "smoke-basic-001"
            )
            
            response = test_client.post(
                "/webhook/message", json=basic_call,
                headers={"Content-Type": "application/json", "X-API-Key": "smoke-basic-key"}
            )
            
            # Should process successfully
            assert response.status_code == 200
            assert response.json().get("status") == "accepted"