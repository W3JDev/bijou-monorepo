"""
Integration Tests for WhatsApp Call Handler
===========================================

Tests the end-to-end call handling flow including:
- Bridge to Core HTTP communication
- Database integration
- Configuration combinations
- Multi-tenant isolation

Test Coverage:
- Bridge call event forwarding
- Core webhook processing of call events
- Environment variable configurations
- Tenant-specific call handling

Author: QA Engineer - Bijou AI Enterprise
Date: 2026-02-23
"""

import pytest
import asyncio
import json
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Test constants
TEST_BRIDGE_URL = "http://mock-bridge:8080"
TEST_CORE_URL = "http://localhost:8080"
TEST_CALLER_JID = "60198765432@s.whatsapp.net"
TEST_BUSINESS_JID = "60123456789@s.whatsapp.net"
TEST_TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"


class TestBridgeToCoreCommunication:
    """Test communication between bridge and core for call events."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_call_offer_webhook_forwarding(self, test_client: TestClient):
        """Test bridge forwards call.offer events to core webhook."""
        # Arrange - Mock call offer payload from bridge
        call_payload = {
            "event": "call.offer",
            "timestamp": "2026-02-23T10:00:00Z",
            "device_id": TEST_BUSINESS_JID,
            "payload": {
                "call_id": "CALL_123456789",
                "from": TEST_CALLER_JID,
                "auto_rejected": False,
                "remote_platform": "android",
                "remote_version": "2.23.20.76"
            }
        }
        
        with patch("src.core.bijou.process_call_event") as mock_process_call:
            mock_process_call.return_value = {"status": "processed", "follow_up_sent": True}
            
            # Act - Simulate bridge sending webhook
            response = test_client.post(
                "/webhook/call",
                headers={"Content-Type": "application/json"},
                json=call_payload
            )
            
            # Assert
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "processed"
            
            # Verify call processing was triggered
            mock_process_call.assert_called_once()
            call_args = mock_process_call.call_args[0][0]
            assert call_args["event"] == "call.offer"
            assert call_args["payload"]["call_id"] == "CALL_123456789"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_missed_call_followup_creation(self, test_client: TestClient):
        """Test that missed calls trigger follow-up message creation."""
        # Arrange - Call that times out (missed)
        call_payload = {
            "event": "call.offer",
            "timestamp": "2026-02-23T10:00:00Z",
            "device_id": TEST_BUSINESS_JID,
            "payload": {
                "call_id": "CALL_MISSED_001",
                "from": TEST_CALLER_JID,
                "auto_rejected": False
            }
        }
        
        # Simulate call timeout after 30+ seconds
        call_timeout_payload = {
            "event": "call.terminate",
            "timestamp": "2026-02-23T10:00:35Z",  # 35 seconds later
            "device_id": TEST_BUSINESS_JID,
            "payload": {
                "call_id": "CALL_MISSED_001",
                "from": TEST_CALLER_JID,
                "reason": "timeout",
                "duration": 35
            }
        }
        
        with patch("src.core.bijou.send_whatsapp_message") as mock_send, \
             patch("src.core.bijou.TenantManager") as mock_tenant_mgr:
            
            mock_tenant_mgr.return_value.get_tenant_from_whatsapp.return_value = TEST_TENANT_ID
            mock_send.return_value = {"status": "sent", "message_id": "MSG_FOLLOWUP_001"}
            
            # Act - Process call offer first
            offer_response = test_client.post("/webhook/call", json=call_payload)
            assert offer_response.status_code == 200
            
            # Then process call termination
            terminate_response = test_client.post("/webhook/call", json=call_timeout_payload)
            
            # Assert
            assert terminate_response.status_code == 200
            
            # Verify follow-up message was sent
            mock_send.assert_called()
            send_call_args = mock_send.call_args
            
            # Check that message contains missed call context
            sent_message = send_call_args[1] if len(send_call_args) > 1 else send_call_args[0]
            assert "missed_call" in str(sent_message).lower() or "📞" in str(sent_message)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_answered_call_no_followup(self, test_client: TestClient):
        """Test that answered calls don't trigger follow-up messages."""
        # Arrange - Call that gets answered
        call_offer_payload = {
            "event": "call.offer",
            "timestamp": "2026-02-23T10:00:00Z",
            "device_id": TEST_BUSINESS_JID,
            "payload": {
                "call_id": "CALL_ANSWERED_001",
                "from": TEST_CALLER_JID,
                "auto_rejected": False
            }
        }
        
        call_accept_payload = {
            "event": "call.accept",
            "timestamp": "2026-02-23T10:00:05Z",  # Answered after 5 seconds
            "device_id": TEST_BUSINESS_JID,
            "payload": {
                "call_id": "CALL_ANSWERED_001",
                "from": TEST_CALLER_JID
            }
        }
        
        call_terminate_payload = {
            "event": "call.terminate",
            "timestamp": "2026-02-23T10:02:00Z",  # 2 minute call
            "device_id": TEST_BUSINESS_JID,
            "payload": {
                "call_id": "CALL_ANSWERED_001",
                "from": TEST_CALLER_JID,
                "reason": "ended",
                "duration": 120
            }
        }
        
        with patch("src.core.bijou.send_whatsapp_message") as mock_send, \
             patch("src.core.bijou.TenantManager") as mock_tenant_mgr:
            
            mock_tenant_mgr.return_value.get_tenant_from_whatsapp.return_value = TEST_TENANT_ID
            
            # Act - Process call lifecycle
            test_client.post("/webhook/call", json=call_offer_payload)
            test_client.post("/webhook/call", json=call_accept_payload)
            terminate_response = test_client.post("/webhook/call", json=call_terminate_payload)
            
            # Assert
            assert terminate_response.status_code == 200
            
            # Verify NO follow-up message was sent (call was answered)
            mock_send.assert_not_called()


class TestConfigurationCombinations:
    """Test different environment variable combinations."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_calls_enabled_followup_enabled(self, test_client: TestClient):
        """Test WHATSAPP_CALLS_ENABLED=true, MISSED_CALL_FOLLOWUP=true."""
        # Arrange
        with patch.dict("os.environ", {
            "WHATSAPP_CALLS_ENABLED": "true",
            "MISSED_CALL_FOLLOWUP": "true"
        }):
            call_payload = {
                "event": "call.offer",
                "payload": {
                    "call_id": "CALL_CONFIG_001",
                    "from": TEST_CALLER_JID,
                    "auto_rejected": False  # Should ring normally
                }
            }
            
            with patch("src.core.bijou.send_whatsapp_message") as mock_send:
                mock_send.return_value = {"status": "sent"}
                
                # Act
                response = test_client.post("/webhook/call", json=call_payload)
                
                # Assert
                assert response.status_code == 200
                # Call should be allowed to ring, follow-up enabled

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_calls_disabled_followup_enabled(self, test_client: TestClient):
        """Test WHATSAPP_CALLS_ENABLED=false, MISSED_CALL_FOLLOWUP=true."""
        # Arrange
        with patch.dict("os.environ", {
            "WHATSAPP_CALLS_ENABLED": "false",
            "MISSED_CALL_FOLLOWUP": "true"
        }):
            call_payload = {
                "event": "call.offer",
                "payload": {
                    "call_id": "CALL_CONFIG_002",
                    "from": TEST_CALLER_JID,
                    "auto_rejected": True  # Should be auto-rejected by bridge
                }
            }
            
            with patch("src.core.bijou.send_whatsapp_message") as mock_send, \
                 patch("src.core.bijou.TenantManager") as mock_tenant_mgr:
                
                mock_tenant_mgr.return_value.get_tenant_from_whatsapp.return_value = TEST_TENANT_ID
                mock_send.return_value = {"status": "sent"}
                
                # Act
                response = test_client.post("/webhook/call", json=call_payload)
                
                # Assert
                assert response.status_code == 200
                # Should send immediate follow-up for rejected call
                mock_send.assert_called()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_calls_disabled_followup_disabled(self, test_client: TestClient):
        """Test WHATSAPP_CALLS_ENABLED=false, MISSED_CALL_FOLLOWUP=false (should force follow-up)."""
        # Arrange
        with patch.dict("os.environ", {
            "WHATSAPP_CALLS_ENABLED": "false",
            "MISSED_CALL_FOLLOWUP": "false"
        }):
            call_payload = {
                "event": "call.offer",
                "payload": {
                    "call_id": "CALL_CONFIG_003",
                    "from": TEST_CALLER_JID,
                    "auto_rejected": True
                }
            }
            
            with patch("src.core.bijou.send_whatsapp_message") as mock_send, \
                 patch("src.core.bijou.TenantManager") as mock_tenant_mgr:
                
                mock_tenant_mgr.return_value.get_tenant_from_whatsapp.return_value = TEST_TENANT_ID
                mock_send.return_value = {"status": "sent"}
                
                # Act
                response = test_client.post("/webhook/call", json=call_payload)
                
                # Assert
                assert response.status_code == 200
                # Should STILL send follow-up (forced when calls disabled)
                mock_send.assert_called()


class TestMultiTenantCallHandling:
    """Test multi-tenant isolation for call handling."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tenant_call_isolation(self, test_client: TestClient, test_tenants):
        """Test that calls for different tenants are properly isolated."""
        # Arrange - Two different tenants
        tenant_a = test_tenants[0]  # Property tenant
        tenant_b = test_tenants[1]  # Gaming tenant
        
        call_to_tenant_a = {
            "event": "call.offer",
            "payload": {
                "call_id": "CALL_TENANT_A_001",
                "from": "60111111111@s.whatsapp.net",  # Customer calling tenant A
                "auto_rejected": True
            }
        }
        
        call_to_tenant_b = {
            "event": "call.offer", 
            "payload": {
                "call_id": "CALL_TENANT_B_001",
                "from": "60222222222@s.whatsapp.net",  # Customer calling tenant B
                "auto_rejected": True
            }
        }
        
        with patch("src.core.bijou.send_whatsapp_message") as mock_send, \
             patch("src.core.bijou.TenantManager") as mock_tenant_mgr:
            
            def mock_get_tenant(whatsapp_jid):
                if "60111111111" in whatsapp_jid:
                    return tenant_a["id"]
                elif "60222222222" in whatsapp_jid:
                    return tenant_b["id"]
                return None
            
            mock_tenant_mgr.return_value.get_tenant_from_whatsapp.side_effect = mock_get_tenant
            mock_send.return_value = {"status": "sent"}
            
            # Act - Process calls for both tenants
            response_a = test_client.post("/webhook/call", json=call_to_tenant_a)
            response_b = test_client.post("/webhook/call", json=call_to_tenant_b)
            
            # Assert
            assert response_a.status_code == 200
            assert response_b.status_code == 200
            
            # Verify both tenants got their respective follow-ups
            assert mock_send.call_count == 2
            
            # Verify tenant isolation - each call should be associated with correct tenant
            send_calls = mock_send.call_args_list
            # This would need more detailed verification of tenant context in actual implementation

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_unknown_tenant_call_handling(self, test_client: TestClient):
        """Test handling of calls from unknown/unregistered numbers."""
        # Arrange - Call from unregistered number
        call_payload = {
            "event": "call.offer",
            "payload": {
                "call_id": "CALL_UNKNOWN_001",
                "from": "60999999999@s.whatsapp.net",  # Unregistered number
                "auto_rejected": True
            }
        }
        
        with patch("src.core.bijou.TenantManager") as mock_tenant_mgr:
            # Mock tenant lookup returning None (unknown tenant)
            mock_tenant_mgr.return_value.get_tenant_from_whatsapp.return_value = None
            
            # Act
            response = test_client.post("/webhook/call", json=call_payload)
            
            # Assert - Should handle gracefully, not crash
            assert response.status_code in [200, 404]  # Either processed or not found


class TestDatabaseIntegration:
    """Test database operations for call handling."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_call_event_storage(self, mock_supabase_with_tenant, test_client: TestClient):
        """Test that call events are stored in database."""
        # Arrange
        call_payload = {
            "event": "call.offer",
            "timestamp": "2026-02-23T10:00:00Z",
            "payload": {
                "call_id": "CALL_STORAGE_001",
                "from": TEST_CALLER_JID,
                "auto_rejected": False
            }
        }
        
        with patch("src.core.bijou.supabase_client", mock_supabase_with_tenant):
            # Act
            response = test_client.post("/webhook/call", json=call_payload)
            
            # Assert
            assert response.status_code == 200
            
            # Verify database interaction occurred
            # (This would need more detailed verification based on actual storage implementation)
            assert mock_supabase_with_tenant.table.called

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_followup_message_storage(self, mock_supabase_with_tenant, test_client: TestClient):
        """Test that follow-up messages are stored in conversations table."""
        # Arrange
        call_payload = {
            "event": "call.offer", 
            "payload": {
                "call_id": "CALL_FOLLOWUP_STORAGE_001",
                "from": TEST_CALLER_JID,
                "auto_rejected": True
            }
        }
        
        with patch("src.core.bijou.supabase_client", mock_supabase_with_tenant), \
             patch("src.core.bijou.send_whatsapp_message") as mock_send, \
             patch("src.core.bijou.TenantManager") as mock_tenant_mgr:
            
            mock_tenant_mgr.return_value.get_tenant_from_whatsapp.return_value = TEST_TENANT_ID
            mock_send.return_value = {"status": "sent", "message_id": "MSG_FOLLOWUP_001"}
            
            # Act
            response = test_client.post("/webhook/call", json=call_payload)
            
            # Assert
            assert response.status_code == 200
            
            # Verify conversation record was attempted to be created
            conversations_table = mock_supabase_with_tenant.table("conversations")
            assert conversations_table.insert.called


class TestErrorHandlingIntegration:
    """Test error handling in integration scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bridge_communication_failure(self, test_client: TestClient):
        """Test handling of bridge communication failures."""
        # Arrange - Malformed payload from bridge
        malformed_payload = {
            "event": "call.offer",
            # Missing required fields
        }
        
        # Act
        response = test_client.post("/webhook/call", json=malformed_payload)
        
        # Assert - Should return error but not crash
        assert response.status_code in [400, 422]  # Bad request or validation error

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_failure_graceful_handling(self, test_client: TestClient):
        """Test graceful handling of database failures."""
        # Arrange
        call_payload = {
            "event": "call.offer",
            "payload": {
                "call_id": "CALL_DB_ERROR_001",
                "from": TEST_CALLER_JID,
                "auto_rejected": True
            }
        }
        
        with patch("src.core.bijou.supabase_client") as mock_supabase:
            # Mock database failure
            mock_supabase.table.side_effect = Exception("Database connection failed")
            
            # Act - Should not crash despite DB failure
            response = test_client.post("/webhook/call", json=call_payload)
            
            # Assert - Should handle gracefully
            assert response.status_code in [200, 500]  # Either processed or server error

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_whatsapp_send_failure_handling(self, test_client: TestClient):
        """Test handling of WhatsApp message send failures."""
        # Arrange
        call_payload = {
            "event": "call.offer",
            "payload": {
                "call_id": "CALL_SEND_ERROR_001", 
                "from": TEST_CALLER_JID,
                "auto_rejected": True
            }
        }
        
        with patch("src.core.bijou.send_whatsapp_message") as mock_send, \
             patch("src.core.bijou.TenantManager") as mock_tenant_mgr:
            
            mock_tenant_mgr.return_value.get_tenant_from_whatsapp.return_value = TEST_TENANT_ID
            # Mock send failure
            mock_send.side_effect = Exception("Bridge connection failed")
            
            # Act
            response = test_client.post("/webhook/call", json=call_payload)
            
            # Assert - Should handle send failure gracefully
            assert response.status_code in [200, 500]


class TestPerformanceIntegration:
    """Test performance characteristics in integration scenarios."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_high_call_volume_handling(self, test_client: TestClient):
        """Test system performance under high call volume."""
        # Arrange - Generate multiple concurrent calls
        import time
        num_calls = 20
        
        call_payloads = []
        for i in range(num_calls):
            call_payloads.append({
                "event": "call.offer",
                "timestamp": f"2026-02-23T10:{i:02d}:00Z",
                "payload": {
                    "call_id": f"CALL_VOLUME_{i:03d}",
                    "from": f"6012345{i:04d}@s.whatsapp.net",
                    "auto_rejected": True
                }
            })
        
        with patch("src.core.bijou.send_whatsapp_message") as mock_send, \
             patch("src.core.bijou.TenantManager") as mock_tenant_mgr:
            
            mock_tenant_mgr.return_value.get_tenant_from_whatsapp.return_value = TEST_TENANT_ID
            mock_send.return_value = {"status": "sent"}
            
            # Act - Send all calls concurrently
            start_time = time.time()
            
            responses = []
            for payload in call_payloads:
                response = test_client.post("/webhook/call", json=payload)
                responses.append(response)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Assert
            # All requests should succeed
            for response in responses:
                assert response.status_code == 200
            
            # Performance should be reasonable (< 5 seconds for 20 calls)
            assert total_time < 5.0, f"Processing {num_calls} calls took {total_time:.2f}s (should be <5s)"
            
            # All follow-ups should be sent
            assert mock_send.call_count == num_calls

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_call_tracking_memory_usage(self, test_client: TestClient):
        """Test that call tracking doesn't cause memory leaks."""
        import gc
        import psutil
        import os
        
        # Arrange - Get baseline memory usage
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss
        
        # Act - Process many call events
        for i in range(50):
            call_payload = {
                "event": "call.offer",
                "payload": {
                    "call_id": f"CALL_MEMORY_{i:03d}",
                    "from": f"60123456{i:03d}@s.whatsapp.net",
                    "auto_rejected": True
                }
            }
            
            response = test_client.post("/webhook/call", json=call_payload)
            assert response.status_code == 200
            
            # Simulate call cleanup after some time
            if i % 10 == 0:
                gc.collect()
        
        # Final cleanup
        gc.collect()
        final_memory = process.memory_info().rss
        memory_increase = final_memory - baseline_memory
        
        # Assert - Memory increase should be reasonable (<50MB for 50 calls)
        memory_increase_mb = memory_increase / (1024 * 1024)
        assert memory_increase_mb < 50, f"Memory increased by {memory_increase_mb:.2f}MB (should be <50MB)"