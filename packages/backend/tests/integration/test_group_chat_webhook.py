"""
Integration tests for group chat webhook handling.

Tests the webhook endpoint's handling of group chat messages
when ENABLE_GROUP_CHAT_SUPPORT is enabled/disabled.
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# Mark as integration test
pytestmark = pytest.mark.integration


@pytest.fixture
def mock_bijou_instance():
    """Create a mock Bijou instance for testing"""
    mock_instance = MagicMock()
    mock_instance.processed_message_ids = set()
    mock_instance.process_message = MagicMock()
    return mock_instance


@pytest.fixture
def test_client(mock_bijou_instance):
    """Create test client with mocked Bijou instance"""
    # Import here to avoid circular imports
    from src.core import bijou
    
    # Replace global instance with mock
    original_instance = bijou.bijou_instance
    bijou.bijou_instance = mock_bijou_instance
    
    # Create test client
    client = TestClient(bijou.app)
    
    yield client
    
    # Restore original instance
    bijou.bijou_instance = original_instance


class TestGroupChatWebhook:
    """Test suite for group chat webhook handling"""

    def test_group_chat_ignored_when_disabled(self, test_client, mock_bijou_instance):
        """Test that group chat messages are ignored when support is disabled"""
        with patch.dict(os.environ, {"ENABLE_GROUP_CHAT_SUPPORT": "false"}):
            response = test_client.post(
                "/webhook/message",
                json={
                    "event": "message",
                    "device_id": "test-device-123",
                    "payload": {
                        "id": "test-msg-001",
                        "chat_id": "120363123456789@g.us",  # Group chat JID
                        "from": "60123456789@s.whatsapp.net",
                        "from_name": "Test User",
                        "body": "Hello group",
                        "timestamp": "2026-02-25T10:00:00Z",
                        "is_from_me": False,
                    },
                },
                headers={"content-type": "application/json"},
            )

            # The webhook ACCEPTS and queues; it does not decide.
            #
            # 2026-09-06 — this test previously asserted that the webhook
            # marked the message processed and never called process_message.
            # Neither could ever hold: the group-chat skip lives INSIDE
            # BijouAI.process_message (src/core/bijou.py, "GROUP CHAT
            # DETECTION"), and `mock_bijou_instance` replaces that method with
            # a MagicMock. The test mocked away the code it was asserting on,
            # so it failed with `assert 'test-msg-001' in set()` — the empty
            # set of a mock that had never run the real logic.
            #
            # Split in two rather than deleted. The webhook's real contract is
            # asserted here; the skip DECISION is asserted directly in
            # tests/unit/test_group_chat_support_flag.py, which is also the
            # first coverage that behaviour has ever had.
            assert response.status_code == 200
            assert response.json()["status"] == "accepted"

            # It reached the queue — filtering is downstream, by design: the
            # decision needs the tenant's config, which the handler has not
            # loaded at this point.
            mock_bijou_instance.process_message.assert_called_once()

    def test_group_chat_processed_when_enabled(self, test_client, mock_bijou_instance):
        """Test that group chat messages are processed when support is enabled"""
        with patch.dict(os.environ, {"ENABLE_GROUP_CHAT_SUPPORT": "true"}):
            response = test_client.post(
                "/webhook/message",
                json={
                    "event": "message",
                    "device_id": "test-device-123",
                    "payload": {
                        "id": "test-msg-002",
                        "chat_id": "120363123456789@g.us",  # Group chat JID
                        "from": "60123456789@s.whatsapp.net",
                        "from_name": "Test User",
                        "body": "Hello group with support enabled",
                        "timestamp": "2026-02-25T10:00:00Z",
                        "is_from_me": False,
                    },
                },
                headers={"content-type": "application/json"},
            )

            # Should return 200 (accepted for processing)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert data["message_id"] == "test-msg-002"

    def test_direct_message_always_processed(self, test_client, mock_bijou_instance):
        """Test that direct messages are always processed regardless of group chat setting"""
        with patch.dict(os.environ, {"ENABLE_GROUP_CHAT_SUPPORT": "false"}):
            response = test_client.post(
                "/webhook/message",
                json={
                    "event": "message",
                    "device_id": "test-device-123",
                    "payload": {
                        "id": "test-msg-003",
                        "chat_id": "60123456789@s.whatsapp.net",  # Direct message JID
                        "from": "60123456789@s.whatsapp.net",
                        "from_name": "Test User",
                        "body": "Hello direct",
                        "timestamp": "2026-02-25T10:00:00Z",
                        "is_from_me": False,
                    },
                },
                headers={"content-type": "application/json"},
            )

            # Should return 200 (accepted for processing)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"

    def test_broadcast_ignored_when_disabled(self, test_client, mock_bijou_instance):
        """Test that broadcast messages are ignored when group chat support is disabled"""
        with patch.dict(os.environ, {"ENABLE_GROUP_CHAT_SUPPORT": "false"}):
            response = test_client.post(
                "/webhook/message",
                json={
                    "event": "message",
                    "device_id": "test-device-123",
                    "payload": {
                        "id": "test-msg-004",
                        "chat_id": "status@broadcast",  # Broadcast JID
                        "from": "60123456789@s.whatsapp.net",
                        "from_name": "Test User",
                        "body": "Broadcast message",
                        "timestamp": "2026-02-25T10:00:00Z",
                        "is_from_me": False,
                    },
                },
                headers={"content-type": "application/json"},
            )

            # Same correction as test_group_chat_ignored_when_disabled: the
            # webhook accepts and queues, and the broadcast skip happens
            # downstream inside process_message, which is mocked here.
            assert response.status_code == 200
            assert response.json()["status"] == "accepted"
            mock_bijou_instance.process_message.assert_called_once()

    def test_lid_jid_always_processed(self, test_client, mock_bijou_instance):
        """Test that linked device (LID) JIDs are processed as direct messages"""
        with patch.dict(os.environ, {"ENABLE_GROUP_CHAT_SUPPORT": "false"}):
            response = test_client.post(
                "/webhook/message",
                json={
                    "event": "message",
                    "device_id": "test-device-123",
                    "payload": {
                        "id": "test-msg-005",
                        "chat_id": "84950644740196@lid",  # LID JID (direct message)
                        "from": "84950644740196@lid",
                        "from_name": "Test User",
                        "body": "Hello from LID",
                        "timestamp": "2026-02-25T10:00:00Z",
                        "is_from_me": False,
                    },
                },
                headers={"content-type": "application/json"},
            )

            # Should return 200 (accepted for processing)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"

    def test_own_messages_skipped(self, test_client, mock_bijou_instance):
        """Test that our own messages are always skipped (infinite loop prevention)"""
        with patch.dict(os.environ, {"ENABLE_GROUP_CHAT_SUPPORT": "true"}):
            response = test_client.post(
                "/webhook/message",
                json={
                    "event": "message",
                    "device_id": "test-device-123",
                    "payload": {
                        "id": "test-msg-006",
                        "chat_id": "120363123456789@g.us",
                        "from": "test-device-123",
                        "from_name": "Bijou AI",
                        "body": "This is my own message",
                        "timestamp": "2026-02-25T10:00:00Z",
                        "is_from_me": True,  # Our own message
                    },
                },
                headers={"content-type": "application/json"},
            )

            # Should return 200 but skip processing
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "skipped"
            assert data["reason"] == "from_me"

    def test_duplicate_message_skipped(self, test_client, mock_bijou_instance):
        """Test that duplicate messages are skipped (idempotency)"""
        # Add message ID to processed set
        mock_bijou_instance.processed_message_ids.add("test-msg-007")

        response = test_client.post(
            "/webhook/message",
            json={
                "event": "message",
                "device_id": "test-device-123",
                "payload": {
                    "id": "test-msg-007",  # Already processed
                    "chat_id": "60123456789@s.whatsapp.net",
                    "from": "60123456789@s.whatsapp.net",
                    "from_name": "Test User",
                    "body": "Duplicate message",
                    "timestamp": "2026-02-25T10:00:00Z",
                    "is_from_me": False,
                },
            },
            headers={"content-type": "application/json"},
        )

        # Should return 200 but skip processing
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["reason"] == "already_processed"


if __name__ == "__main__":
    # Run tests with: pytest tests/integration/test_group_chat_webhook.py -v
    pytest.main([__file__, "-v"])
