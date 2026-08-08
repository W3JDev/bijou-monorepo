"""
Test Mocks
==========

Mock implementations for testing without external dependencies.

Mocks:
- whatsapp_mock.py - WhatsApp bridge simulator for testing without real numbers

Usage:
    from tests.mocks.whatsapp_mock import MockWhatsAppBridge, create_mock_bridge

Example:
    bridge = create_mock_bridge()
    bridge.create_session("session-123", "tenant-123")
    bridge.connect_session("session-123", "+60143856929")

    # Simulate incoming message
    msg = bridge.simulate_incoming_message(
        "session-123",
        "+60100000001",
        "Hello, I have a question"
    )

    # Check sent messages
    sent = bridge.get_sent_messages("session-123")

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Date: 2026-02-07
"""

from tests.mocks.whatsapp_mock import (
    MockBridgeHTTPClient,
    MockWhatsAppBridge,
    MockWhatsAppMessage,
    MockWhatsAppSession,
    create_mock_bridge,
    create_mock_http_client,
    simulate_whatsapp_conversation,
)

__all__ = [
    "MockWhatsAppBridge",
    "MockWhatsAppSession",
    "MockWhatsAppMessage",
    "MockBridgeHTTPClient",
    "create_mock_bridge",
    "create_mock_http_client",
    "simulate_whatsapp_conversation",
]
