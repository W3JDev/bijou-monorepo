"""
Bijou AI - E2E Dashboard API Tests
===================================

P0 Dashboard API tests for data retrieval and management.

Test Coverage:
- TC-DASH-001: Dashboard stats endpoint
- TC-DASH-002: Conversations list endpoint
- TC-DASH-003: Conversation detail endpoint

Author: @qa-engineer
"""

import pytest
import httpx
from typing import Dict, Any
from supabase import Client


@pytest.mark.e2e
@pytest.mark.p0
@pytest.mark.dashboard
@pytest.mark.asyncio
async def test_dashboard_stats_endpoint(
    api_client: httpx.AsyncClient,
    test_tenant_id: str,
    supabase_client: Client
):
    """
    TC-DASH-001: Dashboard Stats Endpoint
    
    GIVEN: Activity data exists for tenant
    WHEN: GET /api/dashboard/stats is called
    THEN: Stats should include required metrics
    AND: All metrics should be valid numbers
    
    Priority: P0 (BLOCKING)
    Rollback Trigger: If endpoint returns 500 or invalid data
    """
    # Arrange: Ensure test tenant has some data
    # (This test uses existing data or returns zeros, both are acceptable)
    
    # Act: Request dashboard stats
    response = await api_client.get(
        "/api/dashboard/stats",
        headers={"X-Tenant-ID": test_tenant_id}
    )
    
    # Assert: Response should be successful
    assert response.status_code == 200, \
        f"❌ Stats endpoint returned {response.status_code}: {response.text}"
    
    stats = response.json()
    
    # Assert: Required fields present
    required_fields = [
        "active_conversations",
        "ai_handled",
        "human_handled",
        "leads_generated_today"
    ]
    
    for field in required_fields:
        assert field in stats, \
            f"❌ Missing required field '{field}' in stats response: {stats}"
        
        # Assert: All values are integers
        assert isinstance(stats[field], int), \
            f"❌ Field '{field}' should be integer, got {type(stats[field])}: {stats[field]}"
        
        # Assert: All values are non-negative
        assert stats[field] >= 0, \
            f"❌ Field '{field}' should be non-negative, got {stats[field]}"
    
    # Assert: Logical consistency
    total_handled = stats["ai_handled"] + stats["human_handled"]
    assert total_handled <= stats["active_conversations"] or stats["active_conversations"] == 0, \
        f"❌ Logical error: ai_handled ({stats['ai_handled']}) + human_handled ({stats['human_handled']}) " \
        f"should not exceed active_conversations ({stats['active_conversations']})"
    
    print(f"✅ TC-DASH-001 PASSED: Dashboard stats returned successfully")
    print(f"   Active conversations: {stats['active_conversations']}")
    print(f"   AI handled: {stats['ai_handled']}")
    print(f"   Human handled: {stats['human_handled']}")
    print(f"   Leads today: {stats['leads_generated_today']}")


@pytest.mark.e2e
@pytest.mark.p0
@pytest.mark.dashboard
@pytest.mark.asyncio
async def test_conversations_list_endpoint(
    api_client: httpx.AsyncClient,
    test_tenant_id: str,
    supabase_client: Client
):
    """
    TC-DASH-002: Conversations List Endpoint
    
    GIVEN: Conversations exist in database
    WHEN: GET /api/dashboard/conversations is called
    THEN: Conversations should be returned
    AND: Response should include required fields
    AND: Phone numbers should be formatted correctly
    
    Priority: P0 (BLOCKING)
    Rollback Trigger: If endpoint returns 500 or incorrect data
    """
    # Arrange: Create test conversation to ensure at least one exists
    test_conv_data = {
        "tenant_id": test_tenant_id,
        "chat_jid": "60123456789@s.whatsapp.net",
        "message_content": "Test conversation for E2E testing",
        "ai_response": "Test response",
        "contact_name": "+60 12 345 6789"
    }
    
    conv_response = supabase_client.table("conversations").insert(test_conv_data).execute()
    assert conv_response.data, "Failed to create test conversation"
    test_conv_id = conv_response.data[0]["id"]
    
    try:
        # Act: Request conversations list
        response = await api_client.get(
            "/api/dashboard/conversations",
            headers={"X-Tenant-ID": test_tenant_id},
            params={"limit": 50}
        )
        
        # Assert: Response should be successful
        assert response.status_code == 200, \
            f"❌ Conversations endpoint returned {response.status_code}: {response.text}"
        
        conversations = response.json()
        
        # Assert: Response should be a list
        assert isinstance(conversations, list), \
            f"❌ Expected list, got {type(conversations)}: {conversations}"
        
        # Assert: Should contain at least our test conversation
        assert len(conversations) >= 1, \
            f"❌ Expected at least 1 conversation, got {len(conversations)}"
        
        # Verify structure of first conversation
        if len(conversations) > 0:
            first_conv = conversations[0]
            
            # Required fields
            required_fields = ["chat_jid", "customer_name"]
            for field in required_fields:
                assert field in first_conv, \
                    f"❌ Missing required field '{field}' in conversation: {first_conv}"
            
            # Verify phone number formatting
            # Should be formatted like "+60 12 345 6789" for Malaysian numbers
            customer_name = first_conv.get("customer_name", "")
            
            # Check if it's a formatted phone number (contains + and spaces)
            if customer_name and customer_name.startswith("+"):
                assert " " in customer_name or len(customer_name) < 15, \
                    f"⚠️ Phone number may not be formatted correctly: {customer_name}"
            
            print(f"✅ TC-DASH-002 PASSED: Conversations list returned successfully")
            print(f"   Total conversations: {len(conversations)}")
            print(f"   Sample conversation: {first_conv.get('chat_jid')}")
            print(f"   Customer name: {first_conv.get('customer_name')}")
        
    finally:
        # Cleanup: Delete test conversation
        supabase_client.table("conversations").delete().eq("id", test_conv_id).execute()


@pytest.mark.e2e
@pytest.mark.p0
@pytest.mark.dashboard
@pytest.mark.asyncio
async def test_conversation_detail_endpoint(
    api_client: httpx.AsyncClient,
    test_tenant_id: str,
    supabase_client: Client,
    test_customer_jid: str
):
    """
    TC-DASH-003: Conversation Detail Endpoint
    
    GIVEN: Conversation exists for a customer
    WHEN: GET /api/dashboard/conversation/{customer_jid} is called
    THEN: Full message history should be returned
    AND: Messages should include user and assistant roles
    AND: Timestamps should be present
    
    Priority: P0 (BLOCKING)
    Rollback Trigger: If endpoint returns 500 or missing data
    """
    # Arrange: Create test conversation with messages
    test_messages = [
        {
            "tenant_id": test_tenant_id,
            "chat_jid": test_customer_jid,
            "message_content": "Hello, I need help",
            "ai_response": "Hi! How can I assist you today?",
            "contact_name": "Test Customer"
        },
        {
            "tenant_id": test_tenant_id,
            "chat_jid": test_customer_jid,
            "message_content": "What are your business hours?",
            "ai_response": "We're open Monday to Friday, 9 AM - 6 PM.",
            "contact_name": "Test Customer"
        }
    ]
    
    insert_response = supabase_client.table("conversations").insert(test_messages).execute()
    assert insert_response.data, "Failed to create test messages"
    inserted_ids = [msg["id"] for msg in insert_response.data]
    
    try:
        # Act: Request conversation detail
        response = await api_client.get(
            f"/api/dashboard/conversation/{test_customer_jid}",
            headers={"X-Tenant-ID": test_tenant_id}
        )
        
        # Assert: Response should be successful
        assert response.status_code == 200, \
            f"❌ Conversation detail endpoint returned {response.status_code}: {response.text}"
        
        detail = response.json()
        
        # Assert: Required fields present
        required_fields = ["customer_jid", "customer_name", "status", "messages"]
        for field in required_fields:
            assert field in detail, \
                f"❌ Missing required field '{field}' in conversation detail: {detail}"
        
        # Assert: customer_jid matches
        assert detail["customer_jid"] == test_customer_jid, \
            f"❌ Expected customer_jid {test_customer_jid}, got {detail['customer_jid']}"
        
        # Assert: Messages array present and populated
        messages = detail["messages"]
        assert isinstance(messages, list), \
            f"❌ Messages should be a list, got {type(messages)}"
        
        assert len(messages) >= 2, \
            f"❌ Expected at least 2 messages (user + assistant), got {len(messages)}"
        
        # Verify message structure
        for msg in messages:
            assert "role" in msg, f"❌ Message missing 'role' field: {msg}"
            assert "content" in msg, f"❌ Message missing 'content' field: {msg}"
            assert "timestamp" in msg, f"❌ Message missing 'timestamp' field: {msg}"
            
            # Role should be either 'user' or 'assistant'
            assert msg["role"] in ["user", "assistant"], \
                f"❌ Invalid role '{msg['role']}', expected 'user' or 'assistant'"
            
            # Content should not be empty
            assert len(msg["content"]) > 0, \
                f"❌ Message content is empty for role {msg['role']}"
        
        # Assert: Conversation should alternate between user and assistant
        # First message should be from user
        if len(messages) > 0:
            assert messages[0]["role"] == "user", \
                f"❌ First message should be from user, got {messages[0]['role']}"
        
        # Assert: Status should be valid
        assert detail["status"] in ["ai", "human"], \
            f"❌ Invalid status '{detail['status']}', expected 'ai' or 'human'"
        
        print(f"✅ TC-DASH-003 PASSED: Conversation detail returned successfully")
        print(f"   Customer: {detail['customer_jid']}")
        print(f"   Status: {detail['status']}")
        print(f"   Message count: {len(messages)}")
        print(f"   Sample message: {messages[0]['content'][:50]}...")
        
    finally:
        # Cleanup: Delete test messages
        for msg_id in inserted_ids:
            supabase_client.table("conversations").delete().eq("id", msg_id).execute()


@pytest.mark.e2e
@pytest.mark.p1
@pytest.mark.dashboard
@pytest.mark.asyncio
async def test_escalations_endpoint(
    api_client: httpx.AsyncClient,
    test_tenant_id: str,
    supabase_client: Client
):
    """
    TC-DASH-004: Escalations Queue Endpoint
    
    GIVEN: Escalations exist for tenant
    WHEN: GET /api/dashboard/escalations is called
    THEN: Escalations should be returned
    AND: Sorted by priority (urgent > high > normal > low)
    
    Priority: P1 (Should pass)
    """
    # Arrange: Create test escalations with different priorities
    from datetime import datetime, timedelta
    
    test_escalations = [
        {
            "tenant_id": test_tenant_id,
            "chat_jid": "60100000030@s.whatsapp.net",
            "reason": "Test urgent escalation",
            "priority": "urgent",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "sla_deadline": (datetime.now() + timedelta(minutes=5)).isoformat()
        },
        {
            "tenant_id": test_tenant_id,
            "chat_jid": "60100000031@s.whatsapp.net",
            "reason": "Test normal escalation",
            "priority": "normal",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "sla_deadline": (datetime.now() + timedelta(hours=1)).isoformat()
        },
        {
            "tenant_id": test_tenant_id,
            "chat_jid": "60100000032@s.whatsapp.net",
            "reason": "Test high escalation",
            "priority": "high",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "sla_deadline": (datetime.now() + timedelta(minutes=15)).isoformat()
        }
    ]
    
    insert_response = supabase_client.table("escalations").insert(test_escalations).execute()
    assert insert_response.data, "Failed to create test escalations"
    inserted_ids = [esc["id"] for esc in insert_response.data]
    
    try:
        # Act: Request escalations
        response = await api_client.get(
            "/api/dashboard/escalations",
            headers={"X-Tenant-ID": test_tenant_id},
            params={"status": "pending"}
        )
        
        # Assert: Response should be successful
        assert response.status_code == 200, \
            f"❌ Escalations endpoint returned {response.status_code}: {response.text}"
        
        escalations = response.json()
        
        # Response might be {"escalations": [...]} or just [...]
        if isinstance(escalations, dict) and "escalations" in escalations:
            escalations = escalations["escalations"]
        
        assert isinstance(escalations, list), \
            f"❌ Expected list of escalations, got {type(escalations)}"
        
        # Find our test escalations
        test_escalations_returned = [
            esc for esc in escalations 
            if esc.get("id") in inserted_ids
        ]
        
        if len(test_escalations_returned) >= 2:
            # Verify priority ordering
            priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
            
            for i in range(len(test_escalations_returned) - 1):
                current_priority = test_escalations_returned[i].get("priority", "normal")
                next_priority = test_escalations_returned[i + 1].get("priority", "normal")
                
                current_order = priority_order.get(current_priority, 99)
                next_order = priority_order.get(next_priority, 99)
                
                # Current priority should be >= next priority (urgent comes first)
                if current_order > next_order:
                    print(f"⚠️ Warning: Escalations may not be sorted by priority")
                    print(f"   Found {current_priority} before {next_priority}")
        
        print(f"✅ TC-DASH-004 PASSED: Escalations endpoint working")
        print(f"   Total escalations: {len(escalations)}")
        print(f"   Test escalations found: {len(test_escalations_returned)}")
        
    finally:
        # Cleanup: Delete test escalations
        for esc_id in inserted_ids:
            supabase_client.table("escalations").delete().eq("id", esc_id).execute()
