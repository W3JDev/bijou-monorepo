"""
Test Fixtures for WhatsApp Call Handler Testing
==============================================

Provides realistic call event payloads for testing different scenarios:
- Normal call events (offer, accept, terminate, missed_call)
- Security attack payloads (cross-tenant injection, malformed data)
- Edge case payloads (invalid JIDs, missing fields)

Author: QA Engineer
Date: 2026-02-23
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


def create_call_offer_payload(
    caller_jid: str,
    device_id: str, 
    call_id: str,
    auto_rejected: bool = False,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a call offer webhook payload matching GOWA bridge format.
    
    Args:
        caller_jid: WhatsApp JID of caller (e.g., "+601234567890@s.whatsapp.net")
        device_id: Bridge device ID receiving the call
        call_id: Unique call identifier
        auto_rejected: Whether call was auto-rejected due to settings
        timestamp: ISO timestamp, defaults to now
    
    Returns:
        Dict representing webhook payload from bridge to Bijou core
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    return {
        "event": "call.offer",
        "timestamp": timestamp,
        "device_id": device_id,
        "payload": {
            "call_id": call_id,
            "from": caller_jid,
            "auto_rejected": auto_rejected,
            "remote_platform": "android", 
            "remote_version": "2.23.24.0",
            "group_jid": None  # Not a group call
        }
    }


def create_call_accept_payload(
    caller_jid: str,
    device_id: str,
    call_id: str,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """Create a call acceptance webhook payload."""
    if timestamp is None:
        timestamp = datetime.now().isoformat()
        
    return {
        "event": "call.accept",
        "timestamp": timestamp, 
        "device_id": device_id,
        "payload": {
            "call_id": call_id,
            "from": caller_jid
        }
    }


def create_call_terminate_payload(
    caller_jid: str,
    device_id: str,
    call_id: str,
    is_missed: bool,
    duration_seconds: float,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """Create a call termination webhook payload."""
    if timestamp is None:
        timestamp = datetime.now().isoformat()
        
    return {
        "event": "call.terminate",
        "timestamp": timestamp,
        "device_id": device_id,
        "payload": {
            "call_id": call_id,
            "from": caller_jid,
            "is_missed": is_missed,
            "duration_seconds": duration_seconds
        }
    }


def create_missed_call_payload(
    caller_jid: str,
    device_id: str,
    call_id: str,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a missed call synthetic message payload.
    
    This represents the payload sent by the bridge when triggering
    a missed call follow-up message to Bijou core.
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    return {
        "event": "message",
        "timestamp": timestamp,
        "device_id": device_id,
        "payload": {
            "id": f"missed-call-{call_id}",
            "chat_id": caller_jid,
            "from_": caller_jid,
            "from_name": "Customer",
            "body": "📞 MISSED_CALL",
            "timestamp": timestamp,
            "is_from_me": False,
            "message_type": "missed_call",
            # Media fields (all None for missed call)
            "image": None,
            "video": None,
            "audio": None,
            "document": None,
            "sticker": None
        }
    }


def create_cross_tenant_attack_payload(
    caller_jid: str,
    device_id: str,
    call_id: str,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a malicious cross-tenant injection attack payload.
    
    This simulates an attacker trying to inject a call event
    with mismatched caller JID and device ID to leak data
    between tenants.
    
    Args:
        caller_jid: Legitimate caller's JID (belongs to Tenant A)
        device_id: Wrong device ID (belongs to Tenant B)  
        call_id: Attack call ID
        
    Returns:
        Malicious payload attempting cross-tenant injection
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()
        
    # This payload tries to trick the system by using:
    # - A legitimate caller JID (Tenant A's customer)
    # - A different tenant's device_id (Tenant B's device)
    # The security fix should detect this mismatch and reject it
    
    return {
        "event": "message", 
        "timestamp": timestamp,
        "device_id": device_id,  # INJECTION: Wrong tenant's device
        "payload": {
            "id": f"attack-{call_id}",
            "chat_id": caller_jid,  # Legitimate caller but wrong tenant
            "from_": caller_jid,
            "from_name": "Attacker",
            "body": "📞 MISSED_CALL",
            "timestamp": timestamp,
            "is_from_me": False,
            "message_type": "missed_call",
            "image": None,
            "video": None,
            "audio": None,
            "document": None,
            "sticker": None
        }
    }


def create_malformed_call_payload(
    payload_type: str = "missing_fields"
) -> Dict[str, Any]:
    """
    Create malformed call payloads to test input validation.
    
    Args:
        payload_type: Type of malformation:
            - "missing_fields": Missing required fields
            - "invalid_jid": Invalid JID format
            - "invalid_device": Invalid device ID format
            - "empty_payload": Empty payload object
            - "wrong_event_type": Wrong event type
            - "sql_injection": SQL injection attempt in fields
    """
    base_timestamp = datetime.now().isoformat()
    
    if payload_type == "missing_fields":
        return {
            "event": "message",
            "timestamp": base_timestamp,
            # Missing device_id field
            "payload": {
                "id": "malformed-001",
                "chat_id": "+601234567890@s.whatsapp.net",
                # Missing from_ field
                "body": "📞 MISSED_CALL",
                "timestamp": base_timestamp,
                "is_from_me": False
            }
        }
    
    elif payload_type == "invalid_jid":
        return {
            "event": "message",
            "timestamp": base_timestamp, 
            "device_id": "valid-device-123",
            "payload": {
                "id": "malformed-002",
                "chat_id": "invalid-jid-format",  # Invalid JID
                "from_": "another-invalid-jid",
                "from_name": "Test",
                "body": "📞 MISSED_CALL",
                "timestamp": base_timestamp,
                "is_from_me": False,
                "message_type": "missed_call"
            }
        }
    
    elif payload_type == "invalid_device":
        return {
            "event": "message",
            "timestamp": base_timestamp,
            "device_id": "",  # Empty device ID
            "payload": {
                "id": "malformed-003",
                "chat_id": "+601234567890@s.whatsapp.net",
                "from_": "+601234567890@s.whatsapp.net",
                "from_name": "Test",
                "body": "📞 MISSED_CALL", 
                "timestamp": base_timestamp,
                "is_from_me": False,
                "message_type": "missed_call"
            }
        }
    
    elif payload_type == "empty_payload":
        return {
            "event": "message",
            "timestamp": base_timestamp,
            "device_id": "valid-device-123",
            "payload": {}  # Empty payload
        }
    
    elif payload_type == "wrong_event_type":
        return {
            "event": "unknown_event",  # Wrong event type
            "timestamp": base_timestamp,
            "device_id": "valid-device-123",
            "payload": {
                "id": "malformed-005",
                "chat_id": "+601234567890@s.whatsapp.net",
                "from_": "+601234567890@s.whatsapp.net",
                "body": "📞 MISSED_CALL",
                "timestamp": base_timestamp,
                "is_from_me": False
            }
        }
    
    elif payload_type == "sql_injection":
        return {
            "event": "message",
            "timestamp": base_timestamp,
            "device_id": "'; DROP TABLE tenants; --",  # SQL injection attempt
            "payload": {
                "id": "'; DELETE FROM conversations; --", 
                "chat_id": "+601234567890@s.whatsapp.net",
                "from_": "+601234567890@s.whatsapp.net",
                "from_name": "'; DROP DATABASE; --",
                "body": "📞 MISSED_CALL",
                "timestamp": base_timestamp,
                "is_from_me": False,
                "message_type": "missed_call"
            }
        }
    
    else:
        raise ValueError(f"Unknown payload_type: {payload_type}")


def create_load_test_payloads(count: int = 100) -> list[Dict[str, Any]]:
    """
    Create multiple call payloads for load testing.
    
    Args:
        count: Number of payloads to generate
        
    Returns:
        List of call payloads with unique IDs and caller JIDs
    """
    payloads = []
    
    for i in range(count):
        payload = create_missed_call_payload(
            caller_jid=f"+6012345{i:05d}@s.whatsapp.net",
            device_id=f"load-test-device-{i:03d}",
            call_id=f"load-test-{i:05d}",
            timestamp=(datetime.now() + timedelta(seconds=i)).isoformat()
        )
        payloads.append(payload)
    
    return payloads


def create_multi_tenant_test_scenario() -> Dict[str, Any]:
    """
    Create a comprehensive multi-tenant test scenario with:
    - 3 tenants with different configurations
    - Multiple call events per tenant
    - Cross-tenant attack attempts
    
    Returns:
        Dict containing tenant configs and call events
    """
    tenants = {
        "tenant_a": {
            "tenant_id": "aaaa-1111-bbbb-2222",
            "device_id": "tenant-a-device-001", 
            "whatsapp_jid": "+601111111111@s.whatsapp.net",
            "plan_tier": "pro",
            "settings": {
                "calls_enabled": True,
                "missed_call_followup": True
            }
        },
        "tenant_b": {
            "tenant_id": "cccc-3333-dddd-4444",
            "device_id": "tenant-b-device-002",
            "whatsapp_jid": "+602222222222@s.whatsapp.net", 
            "plan_tier": "free",
            "settings": {
                "calls_enabled": False,  # Auto-reject calls
                "missed_call_followup": True
            }
        },
        "tenant_c": {
            "tenant_id": "eeee-5555-ffff-6666", 
            "device_id": "tenant-c-device-003",
            "whatsapp_jid": "+603333333333@s.whatsapp.net",
            "plan_tier": "enterprise",
            "settings": {
                "calls_enabled": True,
                "missed_call_followup": False  # No follow-up
            }
        }
    }
    
    # Legitimate call events per tenant
    call_events = {
        "tenant_a": [
            create_call_offer_payload(
                caller_jid="+601111111111@s.whatsapp.net",
                device_id="tenant-a-device-001",
                call_id="tenant-a-call-001"
            ),
            create_missed_call_payload(
                caller_jid="+601111111111@s.whatsapp.net",
                device_id="tenant-a-device-001", 
                call_id="tenant-a-call-002"
            )
        ],
        "tenant_b": [
            create_call_offer_payload(
                caller_jid="+602222222222@s.whatsapp.net",
                device_id="tenant-b-device-002",
                call_id="tenant-b-call-001",
                auto_rejected=True  # Calls disabled
            )
        ],
        "tenant_c": [
            create_call_offer_payload(
                caller_jid="+603333333333@s.whatsapp.net", 
                device_id="tenant-c-device-003",
                call_id="tenant-c-call-001"
            ),
            create_call_accept_payload(
                caller_jid="+603333333333@s.whatsapp.net",
                device_id="tenant-c-device-003",
                call_id="tenant-c-call-001"
            ),
            create_call_terminate_payload(
                caller_jid="+603333333333@s.whatsapp.net",
                device_id="tenant-c-device-003", 
                call_id="tenant-c-call-001",
                is_missed=False,
                duration_seconds=45.2
            )
        ]
    }
    
    # Attack payloads attempting cross-tenant access
    attack_payloads = [
        # Attempt to use Tenant A's caller with Tenant B's device
        create_cross_tenant_attack_payload(
            caller_jid="+601111111111@s.whatsapp.net",  # Tenant A caller
            device_id="tenant-b-device-002",           # Tenant B device
            call_id="attack-cross-tenant-001"
        ),
        
        # Attempt to use Tenant C's caller with Tenant A's device  
        create_cross_tenant_attack_payload(
            caller_jid="+603333333333@s.whatsapp.net",  # Tenant C caller
            device_id="tenant-a-device-001",           # Tenant A device
            call_id="attack-cross-tenant-002" 
        )
    ]
    
    return {
        "tenants": tenants,
        "legitimate_calls": call_events,
        "attack_payloads": attack_payloads
    }


# Export test data creation functions
__all__ = [
    "create_call_offer_payload",
    "create_call_accept_payload", 
    "create_call_terminate_payload",
    "create_missed_call_payload",
    "create_cross_tenant_attack_payload",
    "create_malformed_call_payload",
    "create_load_test_payloads",
    "create_multi_tenant_test_scenario"
]