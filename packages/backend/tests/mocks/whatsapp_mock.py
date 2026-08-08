"""
WhatsApp Mock Simulator
========================

Mock WhatsApp bridge for testing without real WhatsApp numbers.

Simulates:
- Message sending/receiving
- QR code generation
- Session management
- Media handling
- Message history

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Date: 2026-02-07
"""

import base64
import io
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from unittest.mock import MagicMock


class MockWhatsAppMessage:
    """Simulated WhatsApp message"""

    def __init__(
        self,
        chat_jid: str,
        content: str,
        sender: str = None,
        is_from_me: bool = False,
        media_type: str = None,
        media_url: str = None,
    ):
        self.id = str(uuid.uuid4())
        self.chat_jid = chat_jid
        self.content = content
        self.sender = sender or chat_jid
        self.is_from_me = is_from_me
        self.media_type = media_type
        self.media_url = media_url
        self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict:
        """Convert to dictionary format matching bridge API"""
        return {
            "id": self.id,
            "chat_jid": self.chat_jid,
            "content": self.content,
            "sender": self.sender,
            "is_from_me": self.is_from_me,
            "media_type": self.media_type,
            "media_url": self.media_url,
            "timestamp": self.timestamp,
            "Time": self.timestamp,
        }


class MockWhatsAppSession:
    """Simulated WhatsApp session for a tenant"""

    def __init__(self, session_id: str, tenant_id: str):
        self.session_id = session_id
        self.tenant_id = tenant_id
        self.connected = False
        self.qr_code = None
        self.whatsapp_jid = None
        self.messages: List[MockWhatsAppMessage] = []
        self.sent_messages: List[MockWhatsAppMessage] = []

    def generate_qr(self) -> str:
        """Generate fake QR code (base64 PNG)"""
        # Simulate QR code as base64 encoded "image"
        fake_qr_data = f"QR_CODE_FOR_SESSION_{self.session_id}_{time.time()}"
        qr_base64 = base64.b64encode(fake_qr_data.encode()).decode()
        self.qr_code = f"data:image/png;base64,{qr_base64}"
        return self.qr_code

    def connect(self, phone_number: str = "+60100000000"):
        """Simulate WhatsApp connection"""
        self.connected = True
        self.whatsapp_jid = f"{phone_number.replace('+', '')}@s.whatsapp.net"
        return True

    def disconnect(self):
        """Simulate disconnection"""
        self.connected = False
        self.whatsapp_jid = None

    def receive_message(self, message: MockWhatsAppMessage):
        """Simulate receiving a message"""
        self.messages.append(message)

    def send_message(self, chat_jid: str, content: str) -> MockWhatsAppMessage:
        """Simulate sending a message"""
        msg = MockWhatsAppMessage(
            chat_jid=chat_jid,
            content=content,
            sender=self.whatsapp_jid,
            is_from_me=True,
        )
        self.sent_messages.append(msg)
        return msg


class MockWhatsAppBridge:
    """
    Mock WhatsApp Bridge API

    Simulates the WhatsApp bridge server for testing.
    """

    def __init__(self):
        self.sessions: Dict[str, MockWhatsAppSession] = {}
        self.base_url = "http://mock-whatsapp-bridge:8080"

    # ════════════════════════════════════════════════════════════════
    # SESSION MANAGEMENT
    # ════════════════════════════════════════════════════════════════

    def create_session(self, session_id: str, tenant_id: str = None) -> Dict:
        """Create new WhatsApp session"""
        if session_id in self.sessions:
            return {"success": False, "error": "Session already exists"}

        session = MockWhatsAppSession(session_id, tenant_id or "test-tenant")
        self.sessions[session_id] = session

        return {
            "success": True,
            "session_id": session_id,
            "status": "qr_pending",
            "message": "Session created. Generate QR code to connect.",
        }

    def get_qr_code(self, session_id: str) -> Dict:
        """Get QR code for session"""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        if session.connected:
            return {"success": False, "error": "Already connected"}

        qr_code = session.generate_qr()

        return {"success": True, "qr_code": qr_code, "status": "qr_ready"}

    def get_session_status(self, session_id: str) -> Dict:
        """Get session connection status"""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        if session.connected:
            status = "connected"
        elif session.qr_code:
            status = "qr_ready"
        else:
            status = "pending"

        return {
            "success": True,
            "session_id": session_id,
            "status": status,
            "connected": session.connected,
            "whatsapp_jid": session.whatsapp_jid,
        }

    def connect_session(self, session_id: str, phone_number: str = None) -> Dict:
        """Simulate scanning QR and connecting"""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        phone = phone_number or f"+6010{uuid.uuid4().hex[:8]}"
        session.connect(phone)

        return {
            "success": True,
            "session_id": session_id,
            "status": "connected",
            "whatsapp_jid": session.whatsapp_jid,
        }

    def disconnect_session(self, session_id: str) -> Dict:
        """Disconnect session"""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        session.disconnect()

        return {"success": True, "message": "Session disconnected"}

    def delete_session(self, session_id: str) -> Dict:
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return {"success": True, "message": "Session deleted"}
        return {"success": False, "error": "Session not found"}

    # ════════════════════════════════════════════════════════════════
    # MESSAGE HANDLING
    # ════════════════════════════════════════════════════════════════

    def send_message(self, session_id: str, chat_jid: str, content: str) -> Dict:
        """Send message to chat"""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        if not session.connected:
            return {"success": False, "error": "Session not connected"}

        msg = session.send_message(chat_jid, content)

        return {
            "success": True,
            "message_id": msg.id,
            "chat_jid": chat_jid,
            "content": content,
            "timestamp": msg.timestamp,
        }

    def get_messages(self, session_id: str, limit: int = 100) -> Dict:
        """Get recent messages for session"""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        messages = [msg.to_dict() for msg in session.messages[-limit:]]

        return {"success": True, "messages": messages, "count": len(messages)}

    def simulate_incoming_message(
        self, session_id: str, sender_number: str, content: str
    ) -> MockWhatsAppMessage:
        """
        Simulate receiving a message from a user.

        This is used in tests to simulate user interactions.
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        chat_jid = f"{sender_number.replace('+', '')}@s.whatsapp.net"
        msg = MockWhatsAppMessage(
            chat_jid=chat_jid, content=content, sender=chat_jid, is_from_me=False
        )

        session.receive_message(msg)
        return msg

    # ════════════════════════════════════════════════════════════════
    # HELPER METHODS FOR TESTING
    # ════════════════════════════════════════════════════════════════

    def get_sent_messages(self, session_id: str) -> List[Dict]:
        """Get all sent messages for a session (for test assertions)"""
        session = self.sessions.get(session_id)
        if not session:
            return []

        return [msg.to_dict() for msg in session.sent_messages]

    def get_last_sent_message(self, session_id: str) -> Optional[Dict]:
        """Get last sent message (for test assertions)"""
        messages = self.get_sent_messages(session_id)
        return messages[-1] if messages else None

    def clear_messages(self, session_id: str):
        """Clear message history for session"""
        session = self.sessions.get(session_id)
        if session:
            session.messages.clear()
            session.sent_messages.clear()

    def reset(self):
        """Reset all sessions (for test cleanup)"""
        self.sessions.clear()


# ════════════════════════════════════════════════════════════════
# MOCK HTTP CLIENT FOR BRIDGE API
# ════════════════════════════════════════════════════════════════


class MockBridgeHTTPClient:
    """
    Mock HTTP client that mimics requests to WhatsApp bridge.

    Use this to replace httpx/requests in tests.
    """

    def __init__(self, mock_bridge: MockWhatsAppBridge):
        self.bridge = mock_bridge

    def post(self, url: str, json: Dict = None, **kwargs) -> MagicMock:
        """Mock POST request"""
        response = MagicMock()
        response.status_code = 200

        # Parse endpoint
        if "/api/sessions/create" in url:
            result = self.bridge.create_session(
                json.get("session_id"), json.get("tenant_id")
            )
        elif "/api/sessions/connect" in url:
            result = self.bridge.connect_session(
                json.get("session_id"), json.get("phone_number")
            )
        elif "/api/send" in url:
            result = self.bridge.send_message(
                json.get("session_id"), json.get("chat_jid"), json.get("content")
            )
        else:
            result = {"success": False, "error": "Unknown endpoint"}

        response.json = lambda: result
        return response

    def get(self, url: str, **kwargs) -> MagicMock:
        """Mock GET request"""
        response = MagicMock()
        response.status_code = 200

        # Parse endpoint
        if "/api/qr/" in url:
            session_id = url.split("/api/qr/")[1].split("?")[0]
            result = self.bridge.get_qr_code(session_id)
        elif "/api/sessions/status/" in url:
            session_id = url.split("/api/sessions/status/")[1].split("?")[0]
            result = self.bridge.get_session_status(session_id)
        elif "/api/messages" in url:
            # Extract session_id from query params (simplified)
            session_id = kwargs.get("params", {}).get("session_id", "default")
            result = self.bridge.get_messages(session_id)
        else:
            result = {"success": False, "error": "Unknown endpoint"}

        response.json = lambda: result
        return response

    def delete(self, url: str, **kwargs) -> MagicMock:
        """Mock DELETE request"""
        response = MagicMock()
        response.status_code = 200

        if "/api/sessions/" in url:
            session_id = url.split("/api/sessions/")[1].split("?")[0]
            result = self.bridge.delete_session(session_id)
        else:
            result = {"success": False, "error": "Unknown endpoint"}

        response.json = lambda: result
        return response


# ════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS FOR TESTS
# ════════════════════════════════════════════════════════════════


def create_mock_bridge() -> MockWhatsAppBridge:
    """Create a new mock bridge instance"""
    return MockWhatsAppBridge()


def create_mock_http_client(bridge: MockWhatsAppBridge) -> MockBridgeHTTPClient:
    """Create mock HTTP client for bridge"""
    return MockBridgeHTTPClient(bridge)


def simulate_whatsapp_conversation(
    bridge: MockWhatsAppBridge, session_id: str, sender: str, messages: List[str]
) -> List[MockWhatsAppMessage]:
    """
    Simulate a conversation from a user.

    Args:
        bridge: Mock bridge instance
        session_id: WhatsApp session ID
        sender: Phone number of sender (e.g., "+60123456789")
        messages: List of message contents to send

    Returns:
        List of message objects
    """
    sent_messages = []
    for content in messages:
        msg = bridge.simulate_incoming_message(session_id, sender, content)
        sent_messages.append(msg)
    return sent_messages
